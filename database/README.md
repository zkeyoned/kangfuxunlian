# database（数据库负责人：数据库（得））

## 这一层是什么

这里是康迹 RehabTrack 的数据层定义，不是运行时数据。包含三样东西：

- `schema.sql`：建表语句，SQLite 起步，字段设计尽量兼容 PostgreSQL，换库时只改 `backend/db.py` 的连接部分。
- `seed/seed.json`：演示数据，登录账号和病人信息全部虚构，仅供本机演示和联调用。
- 数据字段的文字说明在 `docs/02-数据字典.md`，改表必须同步那份文档。

真正跑起来产生的数据库文件在仓库根目录的 `data/` 下（`data/rehabtrack.sqlite3`），这个目录已被 `.gitignore` 排除，不进仓库。

## 14 张表，分四组

**账号与机构**
- `institutions` 机构，逻辑隔离的最小单位
- `users` 账号，患者/康复师/管理员三种角色
- `tokens` 登录令牌，一行一个有效会话
- `patients` 患者档案，挂在 `users` 下

**训练内容与规则**
- `exercises` 动作库（候选方案，待康复师确认）
- `rule_versions` 每个动作的规则参数版本，可激活/停用，改参数走开新版本而不是覆盖旧版本
- `plans` 训练计划
- `plan_items` 计划里的每一项（哪个动作、几组几次、目标角度）

**训练记录**
- `sessions` 一次训练会话
- `session_items` 一组动作的结果（前端上传的核心数据，见 `docs/03-接口契约.md` B 节）
- `reps` 单次动作的明细（峰值角度、时长、是否有效、代偿标记）

**运营**
- `alerts` 异常提醒（疼痛过高、代偿过多、拍摄质量低、角度退步、连续未训练等触发）
- `consents` 知情同意记录
- `audit_logs` 操作审计日志

## 怎么重置演示数据

```bash
./start.sh --reset
```

会清空 `data/` 下的数据库文件，下次启动服务时用 `seed/seed.json` 重新灌一遍演示账号和示例数据。不要手动删 `data/` 目录里的文件再直接起服务，`--reset` 会做该做的清理。

## 改表的流程

1. 改 `database/schema.sql`。
2. 同步改 `docs/02-数据字典.md`，字段含义、约束、取值范围写清楚。
3. 如果新字段需要演示数据，改 `database/seed/seed.json`。
4. 如果改动影响到接口返回或请求字段，同步 `docs/03-接口契约.md`，并在 `docs/decisions/` 新增一条决策记录，知会前端（景）和后端（常）。
5. 跑 `python3 tests/test_api.py`，必须全过才能合并。

## 与后端的读写约定

后端只通过 `backend/db.py` 里的函数读写数据库（`connect()`、`init_db()`、`load_seed()` 等），`backend/main.py` 不直接拼裸 SQL 语句操作核心表以外的逻辑。新增查询优先在 `db.py` 里加辅助函数，保持数据库访问集中在一处，方便以后换 PostgreSQL 时只改一个文件。
