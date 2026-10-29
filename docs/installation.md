# 安装、加载与卸载

## 项目级：先试用

从目标项目目录执行：

```sh
git clone https://github.com/Cyh29hao/eight-honors-skill .agents/skills/eight-honors
```

Windows PowerShell、macOS 和 Linux 都可用这条 Git 命令。额度工具另需 Python 3.9+ 和已登录的 Codex CLI；八条本身不依赖 Python。根目录 `SKILL.md` 的调用名为 `eight-honors`。

在项目新会话中用 `$eight-honors`；没有出现在列表时重新打开项目。默认保持自动发现，宿主可按任务匹配是否加载；显式调用最易核对。安装目录里文件存在，只证明下载完成，不证明这次对话已经读取。

## 全局安装

Codex 官方用户级发现目录是 `~/.agents/skills`。PowerShell 示例：

```powershell
git clone https://github.com/Cyh29hao/eight-honors-skill "$env:USERPROFILE/.agents/skills/eight-honors"
```

macOS / Linux：

```sh
git clone https://github.com/Cyh29hao/eight-honors-skill "$HOME/.agents/skills/eight-honors"
```

用户级 Skills 目录与全局 `AGENTS.md` 目录不同：后者在 `CODEX_HOME`，未设置时是 `~/.codex`。不要仅因设置了 `CODEX_HOME` 就把 Skills 目录也照搬。旧客户端的路径支持可能不同，以当前官方文档和实际列表为准。

项目级与全局同名 skill 可能同时出现；先选择一种范围，避免重复安装。已有同名目录时停止并核对内容，不覆盖用户修改。

## 把偏好长期写入 AGENTS.md

1. 读现有项目或全局 `AGENTS.md`；先复制一份备份。
2. 从 [AGENTS.fragment.md](../references/AGENTS.fragment.md) 取 `EIGHT-HONORS:START/END` 整块，合并到已有文件。保留其他规则、OMX 标记、运行时和团队内容。
3. 已存在同一标记块时只更新该块；已有本机八条时先比较并消除重复，不要把本仓库精简版叠在全文后面。
4. 核对 `AGENTS.override.md`：同层覆盖文件会优先于普通 `AGENTS.md`，写入后者可能不会生效。
5. 启动新会话，让 Agent 列出本次实际读取的规则、skill 路径和报告约定，然后做一个小任务检查行为。

可直接给 Agent 这样的任务：

```text
将已安装 eight-honors 的 references/AGENTS.fragment.md 合并到当前项目 AGENTS.md。
先备份，保留已有内容；若已有同一套八条就先合并冲突，别重复追加。
读回修改后的文件，告诉我下次会话怎么验证加载。
```

Codex 默认发现名为 `AGENTS.md`，不是 `Agent.md`。全局和项目规则有层级，默认合并体积限制为 32 KiB，过长可能截断；不要直接复制作者整份本机全局文件。设置及覆盖机制见 [官方 AGENTS.md 文档](https://learn.chatgpt.com/docs/agent-configuration/agents-md)。

## Claude Code 与其他宿主

Claude Code 可克隆到 `.claude/skills/eight-honors` 并用 `/eight-honors` 调用；持久偏好合并到 `CLAUDE.md`。其他支持 Agent Skills 的宿主按各自路径加载 `SKILL.md`。这里没有声称做过这些宿主的实际会话验证；Codex 额度工具仅适用于支持对应接口的 Codex CLI。

只用普通网页聊天时，可粘贴八条或附上 `SKILL.md` 作为本次约定；不能因此宣称文件工具、额度监测或持久加载已经存在。

## 更新与卸载

更新前检查安装目录 `git status`。保留自己的改动；干净时可 `git pull --ff-only`。项目 `AGENTS.md` 中复制的标记块不会随 Git 自动更新，需要另行比较合并。

卸载时，先核对准确安装路径，只移除这一个 skill 目录；如果合并了长期规则，再只删除对应标记块，保留其他配置。交接文件属于任务成果，按项目自身规则保留，不随 skill 删除。
