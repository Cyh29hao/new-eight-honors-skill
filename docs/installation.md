# 安装、规则合并、更新与卸载

## 一条命令启用当前项目

在已有项目根目录运行，需要 Python 3.9+；不需要 Git 或额外 Python 包：

```sh
python -c "import urllib.request as u;exec(u.urlopen('https://raw.githubusercontent.com/Cyh29hao/new-eight-honors-skill/main/scripts/install.py',timeout=20).read(262144))"
```

macOS/Linux 如只有 `python3`，将开头的 `python` 换成 `python3`。命令下载并执行仓库中可阅读的 [scripts/install.py](../scripts/install.py)。远端下载失败时停止，不会假装安装成功。

它会完成：

1. 下载仓库包后，只将需要的运行文件安装到项目 `.agents/skills/eight-honors`，不会把宣传图片和测试装进去。
2. 已有 `AGENTS.md` 要修改时，先备份原始字节到项目 `.eight-honors-backups/` 下的独立时间目录。该目录在 Windows 隐藏，且内部有 Git 忽略规则。
3. 在 `AGENTS.md` 添加或替换 `EIGHT-HONORS:START/END` 标记块，保留块外内容、UTF-8 BOM 与原有换行方式。
4. 读回规则与运行文件，核对是否确实写入。输出实际位置及备份路径。

安装完成后开新会话，调用 `$eight-honors`；也可以让 Agent 列出实际读取的规则和 skill。文件写入与客户端实际加载是两个检查。

## 预览、指定项目与 Claude Code

在同一条命令最后追加参数即可：

- `--dry-run`：预览变化，零文件写入，不创建目录、锁或备份。
- `--project "C:/Projects/my-project"`：选择另一个已存在的项目。
- `--agent claude`：使用项目 `.claude/skills/eight-honors` 和 `CLAUDE.md`。

Claude Code 中调用 `/eight-honors`。安装器的路径和文件合并行为有测试；实际 Claude 会话加载未实机验收。额度工具仍针对 Codex。

已克隆仓库时，也能离线运行：

```sh
python path/to/eight-honors-skill/scripts/install.py --source path/to/eight-honors-skill --project path/to/project
```

## 保护已有内容的方式

重复安装相同版本不会追加第二份规则。由安装器管理、且没有手工修改的旧版本可以更新；已修改的 skill 文件、未知额外文件会被保留并使安装停止。两个额度模块正常产生的 CPython 缓存被识别为可再生文件，不会妨碍重复安装或更新。

规则标记损坏、出现多份标记、目标为符号链接/Windows junction，或存在会覆盖 `AGENTS.md` 的同层 `AGENTS.override.md` 时，安装器明确停止。它不会擅自改写覆盖规则。

脚本只能识别自己的标记块。如果已经手工写过未标记的八条，请先让 Agent 阅读并合并重复含义，不要机械追加。备份含原始私人内容，应按项目资料保护，不要上传。

写入使用锁、临时文件和替换；捕获到写入或核对失败时恢复先前规则和 skill。突然断电等仍可能留下锁或恢复目录，先检查是否存在运行实例和已输出的恢复路径，不要删除另一实例的锁。

## 只安装 skill，不改项目规则

仍可手动克隆：

```sh
git clone https://github.com/Cyh29hao/new-eight-honors-skill .agents/skills/eight-honors
```

这种方式只安装目录，需另行合并 [AGENTS.fragment.md](../references/AGENTS.fragment.md)。手动克隆没有安装器的所有权清单，命令安装器不会直接覆盖它；保留旧目录、核对修改后再选择迁移方式。

## 全局偏好

命令安装器只改所选项目。全局使用时，Codex 用户级 skill 目录是 `~/.agents/skills`；全局规则在 `$CODEX_HOME/AGENTS.md`，未设置时是 `~/.codex/AGENTS.md`。先备份，再手动或由 Agent 合并规则，避免项目与全局重复。

Codex 默认发现 `AGENTS.md`，有 S；同层 `AGENTS.override.md` 优先，项目层级也影响结果。规则默认合并体积有上限，详见 [官方说明](https://learn.chatgpt.com/docs/agent-configuration/agents-md)。

## 更新与卸载

命令安装的版本：重复运行安装命令即可核对并更新；手工修改会使它停止，不会覆盖。Git 克隆的版本：检查 `git status` 后使用 `git pull --ff-only`，规则片段需另行比较合并。

卸载前核对准确目录，只移除本 skill 和它的标记块，保留其他规则。交接记录和备份属于项目资料，不跟着 skill 自动删除。
