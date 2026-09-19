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
  note               TEXT
);

-- 一组动作的结果（前端每做完一组上传一条）。这就是前端（景）→ 后端与视觉算法（常）的核心契约，字段见 docs/03-接口契约.md B 节。
CREATE TABLE IF NOT EXISTS session_items (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id          INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  plan_item_id        INTEGER REFERENCES plan_items(id),
  exercise_code       TEXT NOT NULL REFERENCES exercises(code),
  set_index           INTEGER NOT NULL,
  reps_target         INTEGER NOT NULL,
  reps_done           INTEGER NOT NULL,        -- 状态机数出来的次数
  reps_valid          INTEGER NOT NULL,        -- 达到有效幅度的次数
  peak_angle_max      REAL,
  peak_angle_mean     REAL,
  duration_ms         INTEGER,
  quality_score       REAL,                    -- 0-100，按规则计算（含 5 个维度）
  score_breakdown_json TEXT,                   -- {"completion":30,"amplitude":22,...}
  compensation_count  INTEGER NOT NULL DEFAULT 0,
  capture_quality     REAL,                    -- 0-1，关键点可用帧率
  low_confidence      INTEGER NOT NULL DEFAULT 0,  -- 1=这组测不准，不给强提示
  angle_trace_json    TEXT,                    -- 可选：降采样角度序列（每 100ms 一个点）
  created_at          TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 每一次动作（可选明细，默认存）。
CREATE TABLE IF NOT EXISTS reps (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  session_item_id  INTEGER NOT NULL REFERENCES session_items(id) ON DELETE CASCADE,
  rep_index        INTEGER NOT NULL,
  peak_angle       REAL,
  duration_ms      INTEGER,
  valid            INTEGER NOT NULL DEFAULT 1,
  flags_json       TEXT                        -- ["amplitude_low","too_fast","trunk_lean"]
);

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

-- =========================================================================
-- 迁移 20260919：训练记录离线导入（origin: database/import_results.py）
-- 只追加列，不改动、不重排已有列。原因见 docs/02-数据字典.md 对应小节
-- 和 知识库/10_卡片/项目/康迹-原型输出落库映射-20260918.md。
-- =========================================================================

-- sessions：离线导入的幂等去重键，以及 started_at 的可信度标记。
-- 原型录制模式为 timing_source=video_presentation_timestamps（回放视频文件）时，
-- 帧时间戳是视频内部呈现时间戳，和真实墙钟时间无关，started_at 只能退化成
-- "结果文件写入时刻"，必须打标记，不能假装是真实训练开始时刻。
ALTER TABLE sessions ADD COLUMN import_source_key TEXT;   -- 通常是 summary.json 的 created_utc；没有 created_utc 时退化成结果目录名
ALTER TABLE sessions ADD COLUMN started_at_source TEXT;   -- observed_wallclock_estimate / file_write_time_video_replay / unknown_timing_source；非导入产生的 session 为空
CREATE UNIQUE INDEX IF NOT EXISTS idx_sessions_import_source_key
  ON sessions(import_source_key) WHERE import_source_key IS NOT NULL;

-- session_items：原型没有 0-100 打分，只有逐项 met/not_met/unable_to_assess 判定（assessment.json），
-- 现有 score_breakdown_json 是 5 维度打分，装不下这种结构，需要单独一列；
-- 另外原型的动作 2（SLR）/6（SQUAT）主指标是"相对初始方向的变化量"（已扣掉 90 度人工偏移，按原样存进
-- peak_angle_max/peak_angle_mean，不是解剖角），不能和动作 1（SEATED_KNEE_EXTENSION）/8（STS）的真实
-- 髋-膝-踝夹角混用同一含义，所以另存一列真实二维测量角度（measurement_metrics 里的 knee_included_deg 等，
-- 仅取可信观测帧）供核对；标定基线（calibration.baseline）原样保留一列。
ALTER TABLE session_items ADD COLUMN checks_json TEXT;            -- 例如 {"3":[{"metric":"amplitude","status":"met",...}]}，key 是原型 repetitions[].index（全局序号）
ALTER TABLE session_items ADD COLUMN measurement_angle_json TEXT; -- 二维测量角度参考值，如 {"observed_knee_min_deg":.., "observed_knee_max_deg":.., "observed_frame_count":..}；不与 peak_angle_max 的口径混用
ALTER TABLE session_items ADD COLUMN calibration_json TEXT;       -- 标定基线快照（measures.baseline，含 captured_at_s），原样保留
ALTER TABLE session_items ADD COLUMN needs_review INTEGER NOT NULL DEFAULT 0;  -- 组内是否存在 needs_review=1 的 rep（预测补帧导致的不确定组）

-- reps：原型每次动作还有保持时长、返回用时、预测补帧次数、是否需复核，
-- 比塞进 flags_json 字符串更适合单独列，方便以后做"保持时间退步"这类趋势提醒。
ALTER TABLE reps ADD COLUMN hold_s REAL;
ALTER TABLE reps ADD COLUMN return_s REAL;
ALTER TABLE reps ADD COLUMN bridged_gaps INTEGER NOT NULL DEFAULT 0;
ALTER TABLE reps ADD COLUMN needs_review INTEGER NOT NULL DEFAULT 0;
