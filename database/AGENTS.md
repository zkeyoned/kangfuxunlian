# database/ 规则（数据库负责人：数据库（得））

## 归属

本目录归数据库（得）负责，deploy/ 暂由数据库（得）兼管。

## 交付物清单

- database/schema.sql：数据库建表脚本
- docs/02-数据字典.md：字段说明（与 schema.sql 必须一致）
- database/seed/seed.json：测试数据（全部虚构人物）

## 可以做什么

- 设计与调整表结构、索引、约束。
- 维护 seed 数据，保证本机演示可跑通。
- 为其他角色解释数据字段含义。

## 不可以做什么

- 不写真实病人数据，seed 里的人物必须虚构。
- 不提交 data/ 目录下的运行时数据库文件（已在 .gitignore）。
- 不擅自改 backend/、algorithm/、frontend/ 目录下的代码；需要改动时提 PR 请后端（常）或前端（景）审。
- 不在没有通知前端（景）、后端（常）的情况下改动 docs/03-接口契约.md 里涉及的字段命名。

## 开工前读什么

1. PROGRESS.md
2. docs/02-数据字典.md
3. docs/03-接口契约.md（看清哪些字段被前端、后端引用）

## 完工标准

- 改表结构必须同时改 docs/02-数据字典.md 和 database/seed/seed.json，保证三者字段一致。
- schema.sql 只能写 `CREATE TABLE/INDEX IF NOT EXISTS`，不能写 `ALTER TABLE`：backend/db.py 的 init_db() 每次启动都会对已有库重跑一遍 schema.sql，ALTER TABLE ADD COLUMN 在已经跑过一次的库上会因为列已存在报错。给已有表加列，直接写进对应 CREATE TABLE 语句末尾；已有旧库要补列，在 database/migrations/ 下新增一个手工执行的 .sql 文件，见 database/README.md 对应小节。
- 跑 `python3 tests/test_api.py` 全部通过。
- backend/db.py 里 SCHEMA 常量指向 `ROOT/"database"/"schema.sql"`，SEED 常量指向 `ROOT/"database"/"seed"/"seed.json"`，改表结构后确认这两个路径仍然有效；backend/db.py 本身属于 backend/，路径若需变动，提 PR 请后端（常）审。
- 更新 PROGRESS.md 里数据库这一行的状态与日期。
