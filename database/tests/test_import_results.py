"""database/import_results.py 的冒烟测试。

用原型（algorithm/rehab-pose-demo）自带的合成样例 examples/synthetic_summary.json +
examples/synthetic_frames.jsonl 跑一遍导入到临时 sqlite，断言行数和关键字段。

不把样例复制进本仓库：直接引用 algorithm/rehab-pose-demo/examples/ 下的路径。PR #1
（backend/import-pose-demo-v0.6）已经合并进 main，这个目录现在就在仓库里，下面的
skipUnless 只是防呆（万一有人删了样例），正常情况下**跳过数应该是 0**。

样例是原型很早期的 schema_version 1.0 格式，字段比现在的 rehab_pose 代码少很多（没有
measurement_metrics、没有 calibrations、没有 created_utc/status/effective_parameters 等），
import_results.py 对这些缺失字段都做了退化处理，所以这里的断言只覆盖"样例里确实有的"
关键字段（peak_angle_max、reps_done/valid、幂等），不覆盖需要完整字段才能算的
measurement_angle_json / calibration_json 这类可选增强信息。

运行：
    python3 database/tests/test_import_results.py
    # 或
    python3 -m unittest database/tests/test_import_results.py
"""
import json
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "database"))
import import_results as ir  # noqa: E402

EXAMPLES_DIR = ROOT / "algorithm" / "rehab-pose-demo" / "examples"
SYNTHETIC_SUMMARY = EXAMPLES_DIR / "synthetic_summary.json"
SYNTHETIC_FRAMES = EXAMPLES_DIR / "synthetic_frames.jsonl"


def _fixture_db(db_path: Path):
    """最小演示数据：一家机构、一个患者账号、一条 SEATED_KNEE_EXTENSION 动作定义。
    不经过 backend/db.py（database/ 不碰 backend/ 代码），也不依赖 seed.json 是否已灌库。
    """
    con = ir.open_db(db_path)
    con.execute("INSERT INTO institutions(name) VALUES('测试机构')")
    con.execute(
        "INSERT INTO users(institution_id,role,username,password_hash,display_name) "
        "VALUES(1,'patient','test.patient','x','测试患者')"
    )
    con.execute("INSERT INTO patients(user_id,institution_id) VALUES(1,1)")
    con.execute(
        "INSERT INTO exercises(code,name,joint,metric,direction,camera_side,description) "
        "VALUES('SEATED_KNEE_EXTENSION','坐姿伸膝','膝','knee_angle','up','side','test fixture')"
    )
    con.commit()
    con.close()


@unittest.skipUnless(
    SYNTHETIC_SUMMARY.exists() and SYNTHETIC_FRAMES.exists(),
    "algorithm/rehab-pose-demo/examples/ 还没合并进 main（见 PR backend/import-pose-demo-v0.6），先跳过",
)
class TestImportResults(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.run_dir = self.tmp / "results_run"
        self.run_dir.mkdir()
        shutil.copy(SYNTHETIC_SUMMARY, self.run_dir / "summary.json")
        shutil.copy(SYNTHETIC_FRAMES, self.run_dir / "frames.jsonl")
        self.db_path = self.tmp / "test.sqlite3"
        _fixture_db(self.db_path)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _connect(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def test_resolve_exercise_from_old_format_sample(self):
        summary, rows, _ = ir.load_run(self.run_dir)
        name, code = ir.resolve_exercise(summary, rows)
        self.assertEqual(name, "SEATED_KNEE_EXTENSION")
        self.assertEqual(code, "SEATED_KNEE_EXTENSION")

    def test_dry_run_writes_nothing(self):
        result = ir.import_run(
            self.run_dir, patient_id=1, plan_id=None, plan_item_id=None,
            db_path=self.db_path, dry_run=True,
        )
        self.assertIsNone(result)
        con = self._connect()
        self.assertEqual(con.execute("SELECT COUNT(*) c FROM sessions").fetchone()["c"], 0)
        con.close()

    def test_import_creates_session_item_and_rep(self):
        session_id = ir.import_run(
            self.run_dir, patient_id=1, plan_id=None, plan_item_id=None,
            db_path=self.db_path, dry_run=False,
        )
        self.assertIsNotNone(session_id)
        con = self._connect()

        session = con.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        self.assertEqual(session["patient_id"], 1)
        self.assertIn(session["status"], ("finished", "aborted"))
        self.assertIsNotNone(session["import_source_key"])
        self.assertIsNotNone(session["started_at_source"])

        items = con.execute("SELECT * FROM session_items WHERE session_id=?", (session_id,)).fetchall()
        self.assertEqual(len(items), 1, "样例只有一个 training_set，应该聚合成一条 session_items")
        item = items[0]
        self.assertEqual(item["exercise_code"], "SEATED_KNEE_EXTENSION")
        self.assertEqual(item["reps_done"], 1)
        self.assertEqual(item["reps_valid"], 1, "样例唯一一次动作 amplitude_met=true 且没有 too_fast 事件")
        self.assertAlmostEqual(item["peak_angle_max"], 170.0)

        # 20260919 常的要求：默认（--score-mode 不传）quality_score 留 NULL，
        # 不能拿提示事件条数反推一个分数出来。
        self.assertIsNone(item["quality_score"])
        breakdown = json.loads(item["score_breakdown_json"])
        self.assertTrue(breakdown["provisional"])
        self.assertIn("reason", breakdown)
        self.assertEqual(breakdown["reps_valid"], 1)
        self.assertEqual(breakdown["reps_target"], 1)
        self.assertIn("compensation_event_count", breakdown)
        self.assertIn("too_fast_event_count", breakdown)

        reps = con.execute(
            "SELECT * FROM reps WHERE session_item_id=?", (item["id"],)
        ).fetchall()
        self.assertEqual(len(reps), 1)
        self.assertEqual(reps[0]["valid"], 1)
        self.assertAlmostEqual(reps[0]["peak_angle"], 170.0)
        self.assertEqual(reps[0]["duration_ms"], 3700)  # (4.4-0.7)s 的样例数据

        # 样例（老格式）summary.json 没有 feedback_events，session_events 应该是空的，
        # 但表本身要能查（新表跟着 schema.sql 自动建）。
        events = con.execute(
            "SELECT * FROM session_events WHERE session_item_id=?", (item["id"],)
        ).fetchall()
        self.assertEqual(len(events), 0)

        con.close()

    def test_score_mode_contract_d_computes_quality_score(self):
        session_id = ir.import_run(
            self.run_dir, patient_id=1, plan_id=None, plan_item_id=None,
            db_path=self.db_path, dry_run=False, score_mode="contract-d",
        )
        con = self._connect()
        item = con.execute(
            "SELECT * FROM session_items WHERE session_id=?", (session_id,)
        ).fetchone()
        self.assertIsNotNone(item["quality_score"])
        self.assertGreaterEqual(item["quality_score"], 0)
        self.assertLessEqual(item["quality_score"], 100)
        breakdown = json.loads(item["score_breakdown_json"])
        self.assertEqual(breakdown["score_mode"], "contract-d")
        self.assertNotIn("provisional", breakdown)
        points = sum(v for k, v in breakdown.items() if k != "score_mode")
        self.assertAlmostEqual(points, item["quality_score"], places=2)
        con.close()

    def test_reimport_is_idempotent(self):
        first = ir.import_run(
            self.run_dir, patient_id=1, plan_id=None, plan_item_id=None,
            db_path=self.db_path, dry_run=False,
        )
        second = ir.import_run(
            self.run_dir, patient_id=1, plan_id=None, plan_item_id=None,
            db_path=self.db_path, dry_run=False,
        )
        self.assertEqual(first, second)
        con = self._connect()
        self.assertEqual(con.execute("SELECT COUNT(*) c FROM sessions").fetchone()["c"], 1)
        self.assertEqual(con.execute("SELECT COUNT(*) c FROM session_items").fetchone()["c"], 1)
        self.assertEqual(con.execute("SELECT COUNT(*) c FROM reps").fetchone()["c"], 1)
        con.close()

    def test_unknown_patient_raises(self):
        with self.assertRaises(ir.ImportError_):
            ir.import_run(
                self.run_dir, patient_id=999, plan_id=None, plan_item_id=None,
                db_path=self.db_path, dry_run=False,
            )


class TestSessionEvents(unittest.TestCase):
    """assign_events_to_groups / build_session_events 的单元测试，不依赖原型样例文件，
    main 分支上也能跑（不像上面那组测试要等 PR #1 合并）。"""

    def test_events_assigned_to_matching_group_and_rep(self):
        groups = {
            1: [{"index": 1, "start_s": 1.0, "end_s": 4.0, "rep_in_set": 1}],
            2: [{"index": 2, "start_s": 10.0, "end_s": 13.0, "rep_in_set": 1}],
        }
        events = [
            {"code": "KNEE_TOO_FAST", "message": "太快", "timestamp_s": 3.0, "level": "notice"},
            {"code": "TRUNK_FORWARD", "message": "前倾", "timestamp_s": 11.5, "level": "notice"},
            {"code": "SOMETHING", "message": "组间休息期间的提示", "timestamp_s": 6.0, "level": "notice"},
        ]
        assigned = ir.assign_events_to_groups(events, groups)
        self.assertEqual(len(assigned[1]), 2, "第一条落在组1窗内；第三条（t=6）离组1右边界更近，也归组1")
        self.assertEqual(len(assigned[2]), 1)

        rows_g1 = ir.build_session_events(assigned[1], groups[1])
        by_code = {r["code"]: r for r in rows_g1}
        self.assertEqual(by_code["KNEE_TOO_FAST"]["rep_index"], 1)
        self.assertIsNone(by_code["SOMETHING"]["rep_index"], "t=6 不落在任何 rep 窗口内，rep_index 应为空")
        self.assertEqual(json.loads(by_code["KNEE_TOO_FAST"]["raw_json"])["message"], "太快")

    def test_event_own_rep_index_wins_over_time_window(self):
        """原型的 AMPLITUDE_BELOW_TARGET / HOLD_TOO_SHORT / RETURN_TOO_FAST 是在这一次动作判定
        完成的那一帧才发出的，时间戳一定晚于该次 rep 的 end_s（end_s 取回到静息位的时刻）。
        所以必须优先认事件自带的 rep_index（原型全局序号），并换算成落库用的组内序号。"""
        groups = {
            1: [{"index": 1, "start_s": 1.0, "end_s": 4.0, "rep_in_set": 1}],
            2: [{"index": 2, "start_s": 10.0, "end_s": 13.0, "rep_in_set": 1}],
        }
        # t=13.6 落在所有 rep 窗口之外，但事件自带 rep_index=2（原型全局第 2 次动作，属于第 2 组）
        events = [{"code": "HOLD_TOO_SHORT", "message": "保持不足", "timestamp_s": 13.6,
                   "level": "notice", "rep_index": 2}]
        assigned = ir.assign_events_to_groups(events, groups)
        self.assertEqual(len(assigned[2]), 1, "自带 rep_index=2 的事件应归第 2 组，不看时间戳")
        self.assertEqual(assigned[1], [])
        rows = ir.build_session_events(assigned[2], groups[2])
        self.assertEqual(rows[0]["rep_index"], 1, "全局第 2 次动作在第 2 组里是组内第 1 次")

    def test_event_rep_index_not_in_this_group_falls_back_to_time(self):
        """事件自带的序号在本组 reps 里找不到时（不该发生，兜底），退回按时间窗判。"""
        reps = [{"index": 7, "start_s": 1.0, "end_s": 4.0, "rep_in_set": 3}]
        rows = ir.build_session_events(
            [{"code": "TRUNK_FORWARD", "timestamp_s": 2.0, "level": "notice", "rep_index": 99}], reps
        )
        self.assertEqual(rows[0]["rep_index"], 3)

    def test_no_groups_means_no_events_assigned(self):
        self.assertEqual(ir.assign_events_to_groups([{"timestamp_s": 1.0, "code": "X"}], {}), {})


def _frames(start_s, end_s, step_s=0.1, visible=True):
    """造一段帧：timestamp_s 从 start_s 到 end_s，可见性由 visible 控制。"""
    rows = []
    t = start_s
    while t <= end_s + 1e-9:
        rows.append({
            "exercise": "SEATED_KNEE_EXTENSION", "timestamp_s": round(t, 3),
            "visible": bool(visible), "confidence": 1 if visible else 0,
            "smoothed_included_deg": 150 if visible else None,
            "measurement_metrics": {"knee_included_deg": 150} if visible else {},
        })
        t += step_s
    return rows


def _write_run(directory: Path, summary: dict, rows: list, assessment: dict | None = None):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "summary.json").write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
    with (directory / "frames.jsonl").open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    if assessment is not None:
        (directory / "assessment.json").write_text(
            json.dumps(assessment, ensure_ascii=False), encoding="utf-8")
    return directory


def _base_summary(**overrides):
    summary = {
        "schema_version": "1.3", "algorithm_version": "0.6.0", "backend": "mediapipe",
        "created_utc": "2026-09-19T10:00:00+00:00", "timing_source": "monotonic_clock",
        "exercise": "SEATED_KNEE_EXTENSION", "status": "completed",
        "effective_parameters": {"rest_max_deg": 105, "target_deg": 160,
                                  "min_hold_s": 2, "min_return_s": 1, "max_gap_s": 0.3},
        "calibrations": [{"captured_at_s": 0.5, "baseline": {"thigh_deg": 3.2}}],
        "feedback_events": [],
        "repetitions": [],
        "interrupted_attempts": [],
    }
    summary.update(overrides)
    return summary


class TestReviewFixes(unittest.TestCase):
    """按队友（后端与视觉算法）20260919 审查意见新增的四组测试：
    代偿计数去重口径、零完成动作也落库、capture_quality 分母、未知 status 的处理。
    用现造的合成 summary/frames，不依赖原型样例文件。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.db_path = self.tmp / "test.sqlite3"
        _fixture_db(self.db_path)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _connect(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def _import(self, summary, rows, assessment=None, **kwargs):
        run_dir = _write_run(self.tmp / f"run_{len(list(self.tmp.iterdir()))}", summary, rows, assessment)
        params = dict(patient_id=1, plan_id=None, plan_item_id=None,
                      db_path=self.db_path, dry_run=False)
        params.update(kwargs)
        return ir.import_run(run_dir, **params)

    # --- 1. compensation_count 口径：同一提示出现两次只计一次 --------------------
    def test_same_prompt_twice_in_one_rep_counts_once(self):
        """口径：每次动作内、非速度类、按提示代号去重的类型数，再按组求和。
        同一次动作里前倾提示两次，session_events 两条，compensation_count 只记 1。"""
        events = [
            {"code": "TRUNK_FORWARD", "message": "身体前倾", "timestamp_s": 10.5, "level": "notice"},
            {"code": "TRUNK_FORWARD", "message": "身体前倾", "timestamp_s": 11.5, "level": "notice"},
            {"code": "THIGH_MOVEMENT", "message": "大腿移动", "timestamp_s": 12.0, "level": "notice"},
            {"code": "KNEE_TOO_FAST", "message": "太快", "timestamp_s": 12.5, "level": "notice"},
        ]
        self.assertEqual(ir.rep_compensation_codes(events), ["TRUNK_FORWARD", "THIGH_MOVEMENT"],
                          "按代号去重，too_fast 类不算进来")

        summary = _base_summary(
            feedback_events=events,
            repetitions=[{"index": 1, "start_s": 10.0, "end_s": 13.0, "max_included_deg": 150,
                          "target_comparison": {"amplitude_met": True}}],
        )
        session_id = self._import(summary, _frames(0.0, 14.0))
        con = self._connect()
        item = con.execute("SELECT * FROM session_items WHERE session_id=?", (session_id,)).fetchone()
        self.assertEqual(item["compensation_count"], 2,
                          "前倾两次只算一个类型，加上大腿移动共 2，too_fast 不计入")
        events_rows = con.execute(
            "SELECT * FROM session_events WHERE session_item_id=?", (item["id"],)).fetchall()
        self.assertEqual(len(events_rows), 4, "逐条事件一条不少，去重只发生在计数口径上")
        con.close()

    # --- 2. 一次动作都没完成时也要落库 -------------------------------------------
    def test_zero_completed_reps_still_creates_session_item(self):
        events = [
            {"code": "AMPLITUDE_BELOW_TARGET", "message": "幅度不够", "timestamp_s": 3.0, "level": "notice"},
            {"code": "TRUNK_FORWARD", "message": "身体前倾", "timestamp_s": 4.0, "level": "notice"},
            {"code": "SLR_KNEE_BENT", "message": "膝没伸直", "timestamp_s": 7.0, "level": "notice"},
        ]
        summary = _base_summary(
            status="stopped_by_user",
            feedback_events=events,
            repetitions=[],
            interrupted_attempts=[{"start_s": 2.0, "end_s": 6.0, "reason": "excursion_too_small"},
                                   {"start_s": 7.0, "end_s": 9.0, "reason": "tracking_lost"}],
        )
        assessment = {
            "attempts": [
                {"attempt": 1, "completed_rep_index": None, "start_s": 2.0, "end_s": 6.0,
                 "completed": False, "interruption_reason": "excursion_too_small",
                 "status": "unable_to_assess",
                 "checks": [{"metric": "amplitude", "status": "unable_to_assess"}]},
                {"attempt": 2, "completed_rep_index": None, "start_s": 7.0, "end_s": 9.0,
                 "completed": False, "interruption_reason": "tracking_lost",
                 "status": "unable_to_assess",
                 "checks": [{"metric": "amplitude", "status": "unable_to_assess"}]},
            ],
        }
        session_id = self._import(summary, _frames(0.0, 10.0), assessment)
        self.assertIsNotNone(session_id)
        con = self._connect()

        session = con.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        self.assertEqual(session["status"], "aborted")

        items = con.execute("SELECT * FROM session_items WHERE session_id=?", (session_id,)).fetchall()
        self.assertEqual(len(items), 1, "一次都没完成也要有一条 session_item")
        item = items[0]
        self.assertEqual(item["reps_done"], 0)
        self.assertEqual(item["reps_valid"], 0)
        self.assertEqual(item["low_confidence"], 1)
        self.assertEqual(item["needs_review"], 1)
        self.assertIsNone(item["quality_score"])
        self.assertIsNotNone(item["calibration_json"], "标定快照照存")
        checks = json.loads(item["checks_json"])
        self.assertEqual(len(checks["interrupted_attempts"]), 2, "中断的尝试照存")
        breakdown = json.loads(item["score_breakdown_json"])
        self.assertTrue(breakdown["zero_completed_reps"])

        self.assertEqual(
            con.execute("SELECT COUNT(*) c FROM reps WHERE session_item_id=?",
                        (item["id"],)).fetchone()["c"], 0)
        event_rows = con.execute(
            "SELECT * FROM session_events WHERE session_item_id=?", (item["id"],)).fetchall()
        self.assertEqual(len(event_rows), 3, "逐条提示事件全部入库，挂在这条 item 下面")
        self.assertTrue(all(r["rep_index"] is None for r in event_rows), "没有 rep 可挂，rep_index 为空")
        con.close()

    def test_zero_completed_reps_not_scored_even_in_contract_d(self):
        summary = _base_summary(status="stopped_by_user", repetitions=[],
                                 interrupted_attempts=[{"start_s": 2.0, "end_s": 6.0,
                                                        "reason": "excursion_too_small"}])
        session_id = self._import(summary, _frames(0.0, 10.0), score_mode="contract-d")
        con = self._connect()
        item = con.execute("SELECT * FROM session_items WHERE session_id=?", (session_id,)).fetchone()
        self.assertIsNone(item["quality_score"], "零完成组不给分，contract-d 也不给")
        con.close()

    # --- 3. capture_quality 分母取整组时间跨度 ------------------------------------
    def test_capture_quality_uses_whole_group_span(self):
        """前半段（标定、中断的尝试）拍不到人，后半段完成动作时拍得很好：
        新口径（整组跨度做分母）必须明显低于旧口径（只算已完成动作窗内）。"""
        rows = _frames(0.0, 9.9, visible=False) + _frames(10.0, 13.0, visible=True)
        summary = _base_summary(
            repetitions=[{"index": 1, "start_s": 10.0, "end_s": 13.0, "max_included_deg": 150,
                          "target_comparison": {"amplitude_met": True}}],
            interrupted_attempts=[{"start_s": 2.0, "end_s": 6.0, "reason": "excursion_too_small"}],
        )
        session_id = self._import(summary, rows)
        con = self._connect()
        item = con.execute("SELECT * FROM session_items WHERE session_id=?", (session_id,)).fetchone()
        new_ratio = item["capture_quality"]
        old_ratio = json.loads(item["measurement_angle_json"])["capture_quality_completed_reps"]
        self.assertAlmostEqual(old_ratio, 1.0, places=6, msg="旧口径只看完成动作窗内，是满分")
        self.assertLess(new_ratio, 0.4, "新口径把标定和中断的尝试算进分母，明显更低")
        self.assertLess(new_ratio, old_ratio)
        self.assertEqual(item["low_confidence"], 1, "新口径低于 0.6，应标 low_confidence")
        con.close()

    def test_group_span_covers_calibration_and_interrupted_attempts(self):
        groups = {1: [{"index": 1, "start_s": 10.0, "end_s": 13.0, "rep_in_set": 1}]}
        summary = _base_summary(
            calibrations=[{"captured_at_s": 0.5}],
            interrupted_attempts=[{"start_s": 2.0, "end_s": 15.0, "reason": "tracking_lost"}],
        )
        spans = ir.compute_group_spans(groups, summary, _frames(0.0, 16.0))
        self.assertEqual(spans[1], (0.5, 15.0))

    # --- 4. 未知 summary.status ---------------------------------------------------
    def test_unknown_status_defaults_to_aborted_and_needs_review(self):
        summary = _base_summary(
            status="some_new_state_from_prototype",
            repetitions=[{"index": 1, "start_s": 10.0, "end_s": 13.0, "max_included_deg": 150,
                          "target_comparison": {"amplitude_met": True}}],
        )
        session_id = self._import(summary, _frames(0.0, 14.0))
        con = self._connect()
        session = con.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        self.assertEqual(session["status"], "aborted", "未知状态不再乐观地按 finished 处理")
        item = con.execute("SELECT * FROM session_items WHERE session_id=?", (session_id,)).fetchone()
        self.assertEqual(item["needs_review"], 1)
        con.close()

    def test_unknown_status_with_strict_refuses_import(self):
        summary = _base_summary(
            status="some_new_state_from_prototype",
            repetitions=[{"index": 1, "start_s": 10.0, "end_s": 13.0, "max_included_deg": 150,
                          "target_comparison": {"amplitude_met": True}}],
        )
        run_dir = _write_run(self.tmp / "run_strict", summary, _frames(0.0, 14.0))
        with self.assertRaises(ir.ImportError_):
            ir.import_run(run_dir, patient_id=1, plan_id=None, plan_item_id=None,
                          db_path=self.db_path, dry_run=False, strict=True)
        con = self._connect()
        self.assertEqual(con.execute("SELECT COUNT(*) c FROM sessions").fetchone()["c"], 0,
                          "--strict 下一条都不许落库")
        con.close()
        # CLI 层：--strict 遇到未知状态应该非零退出
        exit_code = ir.main([str(run_dir), "--patient-id", "1", "--db", str(self.db_path), "--strict"])
        self.assertEqual(exit_code, 1)

    def test_known_status_still_maps_as_before(self):
        summary = _base_summary(
            status="plan_completed",
            repetitions=[{"index": 1, "start_s": 10.0, "end_s": 13.0, "max_included_deg": 150,
                          "target_comparison": {"amplitude_met": True}}],
        )
        session_id = self._import(summary, _frames(0.0, 14.0))
        con = self._connect()
        session = con.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        self.assertEqual(session["status"], "finished")
        item = con.execute("SELECT * FROM session_items WHERE session_id=?", (session_id,)).fetchone()
        self.assertEqual(item["needs_review"], 0, "状态已知、没有补帧，不该平白标复核")
        con.close()


if __name__ == "__main__":
    unittest.main()
