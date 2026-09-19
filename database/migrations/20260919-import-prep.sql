-- 迁移 20260919：训练记录离线导入（origin: database/import_results.py）
--
-- 只给「已经有一个旧的 data/rehabtrack.sqlite3、不想 --reset 重建」的人手工执行一次：
--
--     sqlite3 data/rehabtrack.sqlite3 < database/migrations/20260919-import-prep.sql
--
-- 新建库不需要跑这个文件：database/schema.sql 里对应的列已经直接写进了各自的
-- CREATE TABLE 语句（sessions / session_items / reps），新建库跟着 schema.sql 走
-- 一遍就有这些列了。
--
-- 为什么单独拆出来：backend/db.py 的 init_db() 每次启动都会对已有库重跑一遍
-- schema.sql（`fresh` 只控制要不要灌 seed，不控制要不要跑 schema），如果这几列
-- 也写成 schema.sql 里的 ALTER TABLE ADD COLUMN，已经跑过一次迁移的库下次启动会
-- 因为列已存在而报 `duplicate column name` 崩掉。ALTER TABLE ADD COLUMN 不像
-- CREATE TABLE/INDEX 那样天然支持 IF NOT EXISTS，所以不能留在 schema.sql 里。
--
-- 只追加列，不改动、不重排已有列。含义说明见 docs/02-数据字典.md
-- 「训练记录离线导入」一节和 知识库/10_卡片/项目/康迹-原型输出落库映射-20260918.md。

ALTER TABLE sessions ADD COLUMN import_source_key TEXT;   -- 通常是 summary.json 的 created_utc；没有 created_utc 时退化成结果目录名
ALTER TABLE sessions ADD COLUMN started_at_source TEXT;   -- observed_wallclock_estimate / file_write_time_video_replay / unknown_timing_source；非导入产生的 session 为空

ALTER TABLE session_items ADD COLUMN checks_json TEXT;            -- 例如 {"3":[{"metric":"amplitude","status":"met",...}]}，key 是原型 repetitions[].index（全局序号）
ALTER TABLE session_items ADD COLUMN measurement_angle_json TEXT; -- 二维测量角度参考值，不与 peak_angle_max 的口径混用
ALTER TABLE session_items ADD COLUMN calibration_json TEXT;       -- 标定基线快照（measures.baseline，含 captured_at_s），原样保留
ALTER TABLE session_items ADD COLUMN needs_review INTEGER NOT NULL DEFAULT 0;  -- 组内是否存在 needs_review=1 的 rep

ALTER TABLE reps ADD COLUMN hold_s REAL;
ALTER TABLE reps ADD COLUMN return_s REAL;
ALTER TABLE reps ADD COLUMN bridged_gaps INTEGER NOT NULL DEFAULT 0;
ALTER TABLE reps ADD COLUMN needs_review INTEGER NOT NULL DEFAULT 0;

-- 幂等索引，跑几次都没事（也已经在 schema.sql 里，新建库会自动有）。
CREATE UNIQUE INDEX IF NOT EXISTS idx_sessions_import_source_key
  ON sessions(import_source_key) WHERE import_source_key IS NOT NULL;
