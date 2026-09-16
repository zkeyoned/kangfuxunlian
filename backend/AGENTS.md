# backend/ 规则（后端负责人：后端（常））

## 归属

本目录与 algorithm/ 一起归后端（常）负责。

## 交付物清单

- 视觉分析模块（algorithm/）
- 后端接口（backend/main.py、backend/db.py、backend/scoring.py）
- 完整联调演示（前端页面调用后端接口跑通闭环）

## 可以做什么

- 现有 backend/main.py、db.py、scoring.py 是参考实现，可以整体重写或大改。
- 调整内部实现、性能优化、加日志。
- 提出 docs/03-接口契约.md 的修改建议（需按流程改）。

## 不可以做什么

- 无论怎么重写，对外接口路径与返回字段必须符合 docs/03-接口契约.md；要改契约必须先改 docs/03、通知前端（景）与数据库（得）、在 docs/decisions/ 记一条，再改代码。
- 不直接改 database/schema.sql、database/seed/seed.json；需要改字段时请数据库（得）配合。
- 不在 backend/main.py 里假设 frontend/ 一定有 html 文件。frontend/ 目录在仓库里可能只有 AGENTS.md 和 README.md（前端页面由前端负责人本地维护，不进本仓库），main.py 必须在 frontend/ 没有 html 文件时也能正常启动，只提供 API 和 /docs。
- 不写死真实域名、真实服务器 IP、真实密钥；示例配置用 `<你的域名>`、`<服务器IP>` 占位。

## 开工前读什么

1. PROGRESS.md
2. backend/README.md
3. docs/03-接口契约.md（尤其 A 节：算法结果上报字段；B 节：前端调用字段）
4. docs/02-数据字典.md

## 完工标准

- `python3 tests/test_api.py` 全部通过。
- 接口路径、字段与 docs/03-接口契约.md 完全一致。
- 改了字段先同步 docs/03，并在 docs/decisions/ 新增一条。
- 更新 PROGRESS.md 里后端这一行的状态与日期。
