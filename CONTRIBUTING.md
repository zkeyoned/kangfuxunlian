# 协作流程

人和 AI（Codex、Claude 等）都照这份流程走，每一步给出可以直接照抄的命令。

## 0. 准备环境

```bash
# 装 git（Mac 一般自带，没有就装 Xcode 命令行工具）
xcode-select --install

# 装 gh（GitHub 官方命令行工具），用来开 PR
brew install gh
gh auth login
```

## 1. 克隆仓库

```bash
git clone <仓库地址>
cd kangfuxunlian
```

## 2. 每次开工前先同步

```bash
git checkout main
git pull --rebase origin main
```

不管做什么改动，开工第一件事都是这条命令，避免自己的分支落后太多产生冲突。

## 3. 建分支

分支名格式：`<角色英文>/<主题>`，角色英文对应五个目录：

- `materials/` 用 `materials`
- `frontend/` 用 `frontend`
- `database/` 用 `database`
- `backend/` 或 `algorithm/` 用 `backend`
- `medical/` 用 `medical`
- `deploy/` 用 `deploy`
- `docs/` 用 `docs`

```bash
git checkout -b database/add-reps-table
```

## 4. 改代码，提交

提交信息格式：`[角色] 一句话`，角色用中文，例如：

```bash
git add database/schema.sql
git commit -m "[数据库] 增加 reps 表校验"
```

不要用 `git add -A` 或 `git add .` 一把梭，容易把 `data/`、视频文件、`.venv/` 这些不该进仓库的东西一起加进来。改完先 `git status` 看清楚改了哪些文件，再一个一个 `git add`。

## 5. push 并开 PR

```bash
git push -u origin database/add-reps-table
gh pr create --fill
```

PR 描述按 `.github/PULL_REQUEST_TEMPLATE.md` 的模板填：改了哪个目录、有没有动接口契约、有没有跑测试、需要谁审。

## 6. 谁审谁合

- 只改了自己负责的目录：自己审、自己合（`gh pr merge --squash`）。
- 改了别人的目录，或改了 `docs/03-接口契约.md`（前端、后端、数据库三方共有）：必须请对应目录的负责人审过再合，接口契约的改动还要在 `docs/decisions/` 补一条决定记录。

## 7. 遇到冲突怎么办

```bash
git checkout main
git pull --rebase origin main
git checkout database/add-reps-table
git rebase main
# 按提示打开冲突文件，手动改好，然后：
git add <改好的文件>
git rebase --continue
# 确认没问题后强推自己的分支（只能推自己的分支，绝不能推 main）
git push --force-with-lease
```

## 8. 每周同步一次 PROGRESS.md

每周把自己目录的交付物打勾、更新状态和日期，提交到自己的分支跟着当周的 PR 一起合并，不用单开分支。

## 给 AI（Codex / Claude 等）操作 git 的注意事项

- 提交前必须先 `git status` 看清楚改了哪些文件，不许没看就提交。
- 不许用 `git add -A` 或 `git add .`，只能按需要一个一个加文件，防止把 `data/`、`*.sqlite3`、视频文件、`__pycache__/` 这些误加进去。
- 不许 `git push --force` 到 `main`，只能对自己的功能分支用 `--force-with-lease`。
- 不许跳过 `git pull --rebase origin main` 直接开始改代码。
- 不许在提交信息、代码注释、文档里写真实姓名、域名、服务器 IP、密钥密码，占位符写法（`<你的域名>`、`<服务器IP>`）见 `AGENTS.md`「提交规则」第 6 条。
