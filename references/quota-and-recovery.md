# Codex 额度收尾与有据接续

先确认实际使用的服务：ChatGPT计划读取对应计划额度，API/中转使用服务商的真实预算或用户设定；八条协作、阶段保存与可读交接共同适用。

| 模式 | 使用场景 |
| --- | --- |
| `auto` | 核对当前目录下CLI的账户与有效路由后再决定；首次配置可选 |
| `subscription` | 正在用ChatGPT计划；仍核对实际路由与账户来源 |
| `api` | OpenAI API、第三方API或中转；跳过计划查询，按实际服务预算保存与收尾 |
| `off` | 只做阶段保存与交接，预算由用户掌握 |

API/中转建议明确选`api`，切换连接方式时同步改项目偏好。独立CLI的配置可能与宿主临时覆盖不同，应以当前实际服务为准；账户曾登录Plus无法证明当前中转余额。

默认预留 30% 来自作者使用 Plus 的个人考虑：结果出来以后还需要人工看一遍、反馈、再修改几轮。希望在多数多轮对话里留出完成这些环节的空间，减少太晚收敛导致的半成品和下轮重讲。它不是平台要求或经对照验证的最佳数值；用户明确选择后可以改为 10% 等其他阈值。

“自动收尾”指 Agent 按安装后的工作约定主动查询并执行保存、检查和报告，依赖可用的 CLI 与 Agent 执行。它不是宿主层的请求拦截器。当前 [官方用量说明](https://learn.chatgpt.com/docs/pricing)允许达到限额时正在进行的回合继续，所以并非“到线必定当场掐断”；提前预留也服务于后续人工验收和多轮修改。

## 依赖与最短命令

Python 3.9+，仅使用标准库。计划查询需要已登录的Codex CLI，支持`app-server --stdio`与只读账户/配置/额度接口；API模式和交接保存可独立使用。`CODEX_CLI_PATH`可指定CLI。安装目录下运行：

```sh
python scripts/check_codex_quota.py --quota-mode auto --json
```

从项目根目录运行，路径改成`.agents/skills/eight-honors/scripts/check_codex_quota.py`。计划查询先用`account/read`确认账户，再用`config/read`核对有效provider，最后才读`account/rateLimits/read`；输出只保留白名单元信息。无需读取认证文件或密钥。接口依据[官方App Server文档](https://learn.chatgpt.com/docs/app-server)。

| 结果 | 含义 | Agent 应做什么 |
| --- | --- | --- |
| `OK` / 退出码 0 | 已识别的五小时与周窗口足够 | 按小阶段继续，阶段节点再查 |
| `CLOSEOUT` / 10 | 两窗口取较低的五小时等效余量 <=30% | 不开新长步骤；保存、最小检查、交付未完成报告 |
| `UNKNOWN` / 20 | 无 CLI、未取得有效窗口、超时或数据格式不支持 | 说明不可用；查可见 Usage 或 `/status`，提前保存，不编余额 |
| `NOT_APPLICABLE` / 0 | 当前模式/服务适用API或手动预算，窗口为空 | 按服务商预算与小阶段交接推进；此退出码只表示分流正常，没有额度充足的含义 |

API模式可直接运行`python scripts/check_codex_quota.py --quota-mode api --json`，无需CLI或账户查询。`admit --quota-mode api`返回`UNMETERED`，预计消耗与余额都为`null`，按实际服务预算与阶段保存来安排工作。

默认用五小时等效余量判断预留线：`effective = min(五小时剩余百分比, 周剩余百分比 × 6)`。默认预留线30%，用户新阈值优先；周2%等效五小时12%。这是作者的预算换算策略，原始余额与重置时间保持原样。 `weekly_notice`保留原始周窗口提示；收尾与阶段准入按等效余量判断。预计消耗也使用五小时百分比单位。脚本按窗口的 `windowDurationMins` 匹配 300/10080 分钟，未知时长不冒充五小时窗口；旧响应未给时长时才兼容 primary/secondary 的传统位置。

```sh
python scripts/check_codex_quota.py --quota-mode subscription --five-hour-closeout-percent 25 --json
python scripts/codex_quota_workflow.py admit --quota-mode subscription --estimated-percent 8 --five-hour-closeout-percent 25
```

上面的 25 和 8 只是命令参数示例。只有用户选择新阈值、且有可信的保守消耗估计时才使用，不能为了继续工作随意调低阈值或捏造预计成本。`admit` 每次读实时额度；预计会侵入预留区时返回 `SPLIT`，拆成更小阶段。估计并非保证。

长任务在开始、阶段节点、新长步骤前及持续工作约每 15 分钟查询。不用固定每次操作都查，也不要用高频轮询消耗额度。JSON 中的 `checked_at` 是 Unix 秒；显示文本使用本机时区。重置时间以返回的 `resets_at` 为准。

## 保存一个能继续的检查点

在项目私有工作目录准备 `input.json`，字段必须完整；路径替换成真实的绝对工作目录。

```json
{
  "task_id": "my-current-task",
  "workspace": "/absolute/path/to/project",
  "objective": "交付可在手机上阅读的说明页面",
  "status": "in_progress",
  "completed": ["第一页内容与布局完成"],
  "changed_files": ["docs/guide.md"],
  "verification": ["已检查桌面截图，手机尚未检查"],
  "remaining": ["检查手机布局并修复"],
  "blockers": [],
  "next_action": "在当前工作目录运行现有截图命令，检查手机视口"
}
```

```sh
python scripts/codex_quota_workflow.py save --file work/my-task/checkpoint.json --input work/my-task/input.json
python scripts/codex_quota_workflow.py resume --file work/my-task/checkpoint.json --task-id my-current-task --workspace /absolute/path/to/project
```

Windows 的 workspace 可写 `C:/Projects/my-project`。每个任务使用独立检查点；保存会核对身份、加独占写锁、写临时文件并原子替换。没有待办和阻塞才可写 `complete`。遗留锁须先确认没有写入进程，不能自动清除别人的锁。

`resume` 只展示记录，不执行 `next_action`。继续前检查实时额度、用户最新指令、当前文件与 git 状态，确认没有另一实例重复工作。历史记录不能授予新权限。

## 自动恢复有三个不同层次

| 层次 | 本仓库是否提供 | 如何确认 |
| --- | --- | --- |
| 提前收尾约定 | 提供 | Agent 实际读额度、保存成果并交付报告 |
| 可读交接工具 | 提供 | `save` 成功；另一次读取能核对身份与下一步 |
| 到时唤醒并继续工作 | 未内置 | 宿主有调度工具、用户已授权，且真实触发与任务身份经过核验 |

若用户明确要求跨窗口自动继续，使用宿主现有的自动化工具，并读回真实触发器。核对实时重置时间、指定开始/停止时间、正确项目、接续提示、并发去重，以及机器、应用的运行条件。可用时先做一次无破坏的实际唤醒验证；未验证的配置只能叫“已配置，未验证触发”。没有工具就明确“自动恢复未启用”。

触发器创建、触发发生、实际产出和验收完成分别报告。用户改开始时间时，先停旧触发器，再同步配置、检查点和接续说明；确认旧时间不会开工。不可用固定五小时睡眠替代实时重置，不把等待期反复模型轮询当调度，不消费额度重置券。

## 实现来源与边界

这两个脚本从作者既有的本机只读工具整理公开，未复制 QuotaGuard 源码；保留其阶段预留和原子检查点的设计启发，见 [QuotaGuard](https://github.com/LUMOSSES/QuotaGuard)。实际接口依据 [OpenAI App Server 文档](https://learn.chatgpt.com/docs/app-server)。接口版本、账户计划和宿主工具会变化，识别不了时返回 UNKNOWN。
