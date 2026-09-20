-- 康迹 RehabTrack · 数据字典（SQLite 起步，字段与 PostgreSQL 兼容）
-- 原则：只存关键点推导出的指标，不存视频、不存原始关键点（默认）。
PRAGMA foreign_keys = ON;

-- 机构：逻辑隔离的最小单位。所有患者/康复师都挂在一个机构下。
CREATE TABLE IF NOT EXISTS institutions (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  name          TEXT NOT NULL,
  created_at    TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 账号：三种角色。患者也是一个账号（手机登录用）。
CREATE TABLE IF NOT EXISTS users (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  institution_id  INTEGER NOT NULL REFERENCES institutions(id),
  role            TEXT NOT NULL CHECK (role IN ('admin','therapist','patient')),
  username        TEXT NOT NULL UNIQUE,
  password_hash   TEXT NOT NULL,          -- pbkdf2_sha256$iterations$salt$hash
  display_name    TEXT NOT NULL,
  is_active       INTEGER NOT NULL DEFAULT 1,
  created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 登录令牌：一行一个有效会话，退出即删。
CREATE TABLE IF NOT EXISTS tokens (
  token       TEXT PRIMARY KEY,
  user_id     INTEGER NOT NULL REFERENCES users(id),
  expires_at  TEXT NOT NULL,
  created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 患者档案：一个患者账号对应一条档案。
CREATE TABLE IF NOT EXISTS patients (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id         INTEGER NOT NULL UNIQUE REFERENCES users(id),
  institution_id  INTEGER NOT NULL REFERENCES institutions(id),
  therapist_id    INTEGER REFERENCES users(id),      -- 主责康复师
  surgery_type    TEXT,                              -- 如 ACL重建 / 全膝置换 / 半月板
  surgery_date    TEXT,                              -- YYYY-MM-DD
  affected_side   TEXT CHECK (affected_side IN ('L','R','both')),
  phase           TEXT,                              -- 术后阶段（自由文本，由康复师填）
  baseline_json   TEXT,                              -- 基线：{"knee_flex_max":85,"knee_ext_deficit":5,...}
  notes           TEXT,
  created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 动作字典：候选动作。code 是全系统统一的动作标识（接口契约里用它）。
-- SEATED_KNEE_EXTENSION 是 20260919 新增：对应姿态识别原型 v0.6 的动作 1（坐姿伸膝），
-- 和 KNEE_FLEX（屈膝训练）是同一关节的两个相反训练方向，不能划等号，方向上 KNEE_FLEX 是
-- "角度变小=更屈"，SEATED_KNEE_EXTENSION 是"角度变大=伸直"，两者都保留，各自独立。
CREATE TABLE IF NOT EXISTS exercises (
  code         TEXT PRIMARY KEY,      -- SLR / KNEE_FLEX / SQUAT / STS / SEATED_KNEE_EXTENSION
  name         TEXT NOT NULL,
  joint        TEXT NOT NULL,         -- 主要关节
  metric       TEXT NOT NULL,         -- 主指标名：hip_angle / knee_angle / knee_hip_angle / knee_angle
  direction    TEXT NOT NULL CHECK (direction IN ('up','down')),  -- 峰值是角度变大还是变小
  camera_side  TEXT NOT NULL,         -- 推荐机位：side / front
  description  TEXT
);

-- 动作规则（版本化）：阈值不写死在代码里，改一次留一版。内容由康复需求与医学沟通（陈）+ 后端与视觉算法（常）定，数据库（得）只负责存和分发。
CREATE TABLE IF NOT EXISTS rule_versions (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  exercise_code  TEXT NOT NULL REFERENCES exercises(code),
  version        TEXT NOT NULL,                -- 如 v0.1
  params_json    TEXT NOT NULL,                -- 阈值/窗口/扣分规则，见 docs/03-接口契约.md
  rationale      TEXT,                         -- 阈值来源（文献/康复师意见/试验）
  author         TEXT,
  reviewer       TEXT,                         -- 双人审核：作者之外的复核人
  is_active      INTEGER NOT NULL DEFAULT 0,   -- 同一动作同一时间只有一个激活版本
  created_at     TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  UNIQUE (exercise_code, version)
);

-- 训练计划：康复师给患者开的"处方"。
CREATE TABLE IF NOT EXISTS plans (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  patient_id    INTEGER NOT NULL REFERENCES patients(id),
  therapist_id  INTEGER NOT NULL REFERENCES users(id),
  title         TEXT NOT NULL,
  start_date    TEXT NOT NULL,
  end_date      TEXT,
  days_per_week INTEGER NOT NULL DEFAULT 5,
  status        TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','paused','ended')),
  goal_text     TEXT,                          -- 如"本周膝屈曲达到 100°"
  created_at    TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS plan_items (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  plan_id          INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
  exercise_code    TEXT NOT NULL REFERENCES exercises(code),
  sets             INTEGER NOT NULL DEFAULT 3,
  reps             INTEGER NOT NULL DEFAULT 10,
  target_angle     REAL,                       -- 个体化目标峰值角度
  min_valid_angle  REAL,                       -- 低于这个不算一次有效
  rest_sec         INTEGER NOT NULL DEFAULT 60,
  rule_version_id  INTEGER REFERENCES rule_versions(id),
  sort_order       INTEGER NOT NULL DEFAULT 0,
  notes            TEXT
);

-- 一次训练（打开训练页到结束）。
CREATE TABLE IF NOT EXISTS sessions (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  patient_id         INTEGER NOT NULL REFERENCES patients(id),
  plan_id            INTEGER REFERENCES plans(id),
  started_at         TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  ended_at           TEXT,
  status             TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running','finished','aborted')),
  device             TEXT,                     -- UA 摘要
  camera_side        TEXT,                     -- side / front
  rule_versions_json TEXT,                     -- 本次用到的规则版本快照 {"SQUAT":"v0.1",...}
  client_version     TEXT,
  pain_score         INTEGER,                  -- 训练后自报 0-10（可空）
  note               TEXT,
  import_source_key  TEXT,                     -- 离线导入幂等去重键（通常是 summary.json 的 created_utc）；非导入产生的 session 为空
  started_at_source  TEXT                      -- started_at 可信度标记：observed_wallclock_estimate / file_write_time_video_replay / unknown_timing_source；非导入产生的 session 为空
);

-- 一组动作的结果（前端每做完一组上传一条）。这就是前端（景）→ 后端与视觉算法（常）的核心契约，字段见 docs/03-接口契约.md B 节。
CREATE TABLE IF NOT EXISTS session_items (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id          INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  plan_item_id        INTEGER REFERENCES plan_items(id),
  exercise_code       TEXT NOT NULL REFERENCES exercises(code),
  set_index           INTEGER NOT NULL,
  reps_target         INTEGER NOT NULL,
  reps_done           INTEGER NOT NULL,        -- 状态机数出来的次数。离线导入允许为 0：患者尝试了但一次没完成（识别中断/幅度不足/遮挡）时照样落一条，配 low_confidence=1、needs_review=1、quality_score=NULL
  reps_valid          INTEGER NOT NULL,        -- 达到有效幅度的次数
  peak_angle_max      REAL,
  peak_angle_mean     REAL,
  duration_ms         INTEGER,
  quality_score       REAL,                    -- 0-100，按规则计算（含 5 个维度）。离线导入（database/import_results.py）默认不写这一列（NULL），只有显式传 --score-mode contract-d 才按契约 D 节现算，原因见 docs/02-数据字典.md
  score_breakdown_json TEXT,                   -- {"completion":30,"amplitude":22,...}。离线导入默认存的是各维度原始输入（非加权得分）并标 provisional，见 docs/02
  compensation_count  INTEGER NOT NULL DEFAULT 0,  -- 口径（20260919 统一）：每次动作内、非速度类、按提示代号去重的类型数，再按组求和；同一次动作里同一个提示出现两次只算一次。不是"确诊代偿次数"，提示有冷却时间，条数不等于问题严重程度，离线导入时不用它反推评分
  capture_quality     REAL,                    -- 0-1，关键点可用帧率。离线导入口径（20260919 修正）：分母是这一组的整个时间跨度（从首次尝试或标定开始到该组结束，含标定失败与中断的尝试），不是只算已完成动作的时间窗；旧口径的值另存在 measurement_angle_json 的 capture_quality_completed_reps
  low_confidence      INTEGER NOT NULL DEFAULT 0,  -- 1=这组测不准，不给强提示；离线导入时一次动作都没完成的组一律为 1
  angle_trace_json    TEXT,                    -- 可选：降采样角度序列（每 100ms 一个点）
  created_at          TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  checks_json           TEXT,                  -- 离线导入：原型 assessment.json 的逐项 met/not_met/unable_to_assess 判定，按 repetitions[].index 建 key；这一组一次动作都没完成时，改存 interrupted_attempts（中断的尝试，带 interruption_reason）
  measurement_angle_json TEXT,                  -- 离线导入：二维测量角度参考值，不与 peak_angle_max 的口径混用；另含 capture_quality_completed_reps（旧口径拍摄质量，只算已完成动作窗内的帧），见 docs/02-数据字典.md
  calibration_json      TEXT,                   -- 离线导入：原型标定基线快照（measures.baseline，含 captured_at_s），原样保留
  needs_review           INTEGER NOT NULL DEFAULT 0  -- 离线导入：组内存在 needs_review=1 的 rep（预测补帧）、这一组一次动作都没完成、或 summary.status 未知，三种情况都为 1
);

-- 每一次动作（可选明细，默认存）。
CREATE TABLE IF NOT EXISTS reps (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  session_item_id  INTEGER NOT NULL REFERENCES session_items(id) ON DELETE CASCADE,
  rep_index        INTEGER NOT NULL,
  peak_angle       REAL,
  duration_ms      INTEGER,
  valid            INTEGER NOT NULL DEFAULT 1,
  flags_json       TEXT,                       -- ["amplitude_low","too_fast","trunk_lean"]
  hold_s           REAL,                       -- 离线导入：原型 target_hold_s 原样存
  return_s         REAL,                       -- 离线导入：原型 return_s 原样存
  bridged_gaps     INTEGER NOT NULL DEFAULT 0,  -- 离线导入：这次动作用了几次短暂预测补帧
  needs_review     INTEGER NOT NULL DEFAULT 0   -- 离线导入：bridged_gaps>0 时为 1，提示这条数据不完全是直接观测
);

-- 逐条提示事件（20260919 新增）。这是原型的 feedback_events 逐时刻纠错记录，不能用下面的
-- alerts 表代替：alerts 是给康复师看的汇总提醒（一条 session 一类问题一条），这里是每一次
-- "身体前倾""速度过快"这类实时提示原样落库，一条事件一行，供以后做回放、按事件类型统计用。
-- 离线导入：database/import_results.py 把 summary.feedback_events 逐条写进来，rep_index
-- 优先用事件自带的序号换算成组内序号，事件没带才按时间戳落在哪个 rep 的 [start_s,end_s]
-- 窗口内回填，两样都对不上时为空。
CREATE TABLE IF NOT EXISTS session_events (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  session_item_id  INTEGER NOT NULL REFERENCES session_items(id) ON DELETE CASCADE,
  rep_index        INTEGER,                    -- 这条提示属于哪一次动作（对齐 reps.rep_index，即组内序号），判不出时为空
  timestamp_s      REAL,                       -- 原型的相对时间戳（run.py 里的 t），不是墙钟时间
  code             TEXT,                       -- 原型事件代号，如 TRUNK_FORWARD / KNEE_TOO_FAST，原样存，不翻译成契约 flags 枚举
  message          TEXT,                       -- 原型给用户看的提示文案，原样存
  severity         TEXT,                       -- 原型 level 字段原样存（目前原型只有 'notice'），不是 alerts.severity 那个三态枚举
  raw_json         TEXT                        -- 整条原始事件 JSON，字段有出入时兜底
);
CREATE INDEX IF NOT EXISTS idx_session_events_item ON session_events(session_item_id);

-- 异常提醒：给康复师看的队列。
CREATE TABLE IF NOT EXISTS alerts (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  patient_id       INTEGER NOT NULL REFERENCES patients(id),
  session_id       INTEGER REFERENCES sessions(id),
  type             TEXT NOT NULL,     -- inactive_3d / compensation_high / angle_drop / pain_high / low_capture
  severity         TEXT NOT NULL CHECK (severity IN ('info','warn','high')),
  message          TEXT NOT NULL,
  created_at       TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  acknowledged_by  INTEGER REFERENCES users(id),
  acknowledged_at  TEXT
);

-- 知情同意：版本化，撤回不删历史。
CREATE TABLE IF NOT EXISTS consents (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  patient_id   INTEGER NOT NULL REFERENCES patients(id),
  version      TEXT NOT NULL,
  text_sha256  TEXT NOT NULL,
  agreed_at    TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  withdrawn_at TEXT
);

-- 审计日志：谁在什么时候动了什么。敏感操作必写。
CREATE TABLE IF NOT EXISTS audit_logs (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id     INTEGER REFERENCES users(id),
  action      TEXT NOT NULL,        -- login / plan.create / rule.activate / export / patient.view ...
  target      TEXT,                 -- 如 patient:3
  detail_json TEXT,
  ip          TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_sessions_patient ON sessions(patient_id, started_at);
CREATE INDEX IF NOT EXISTS idx_items_session ON session_items(session_id);
CREATE INDEX IF NOT EXISTS idx_alerts_patient ON alerts(patient_id, acknowledged_at);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id, created_at);

-- 20260919 训练记录离线导入（database/import_results.py）用到的幂等去重键。
-- CREATE UNIQUE INDEX ... IF NOT EXISTS 本身是幂等的，可以放在这里跟着 executescript 每次都跑；
-- 对应的列直接写进了上面 sessions 表的 CREATE TABLE 里，不用 ALTER TABLE
-- （backend/db.py 的 init_db 每次启动都会对已有库重跑一遍 schema.sql，ALTER TABLE ADD COLUMN
-- 在已经加过列的库上会报 duplicate column name；已有旧库需要手工跑一次
-- database/migrations/20260919-import-prep.sql，见该文件说明）。
CREATE UNIQUE INDEX IF NOT EXISTS idx_sessions_import_source_key
  ON sessions(import_source_key) WHERE import_source_key IS NOT NULL;
