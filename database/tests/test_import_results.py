"""database/import_results.py 的冒烟测试。

用原型（algorithm/rehab-pose-demo）自带的合成样例 examples/synthetic_summary.json +
examples/synthetic_frames.jsonl 跑一遍导入到临时 sqlite，断言行数和关键字段。

不把样例复制进本仓库：直接引用 algorithm/rehab-pose-demo/examples/ 下的路径。这个目录现在
还在未合并的 PR（backend/import-pose-demo-v0.6）里，main 上没有，所以这里对缺文件做 skip，
等那个 PR 合并后这些测试才会真的跑起来。

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


if __name__ == "__main__":
    unittest.main()
