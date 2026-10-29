# Codex 额度收尾与有据接续

这里提供的是 Agent 主动查询并提前收尾的工具与约定。脚本不会拦截所有模型请求，不能保证网络中断或平台直接拒绝前一定发出最后一条消息，也没有内置调度器。

默认预留 30% 来自作者使用 Plus 的个人考虑：结果出来以后还需要人工看一遍、反馈、再修改几轮。希望在多数多轮对话里留出完成这些环节的空间，减少太晚收敛导致的半成品和下轮重讲。它不是平台要求或经对照验证的最佳数值；用户明确选择后可以改为 10% 等其他阈值。

## 依赖与最短命令

Python 3.9+、已安装并登录的 Codex CLI；仅使用 Python 标准库。CLI 需支持 `app-server --stdio` 和只读 `account/rateLimits/read`。`CODEX_CLI_PATH` 可指定实际可执行文件。先在安装目录运行：

```sh
python scripts/check_codex_quota.py --json
```

从项目根目录运行，路径改成 `.agents/skills/eight-honors/scripts/check_codex_quota.py`。不要安装或登录不存在的账户来假装验证成功；API key 等登录方式可能不返回订阅额度，此时是 UNKNOWN。

| 结果 | 含义 | Agent 应做什么 |
| --- | --- | --- |
| `OK` / 退出码 0 | 已识别的五小时与周窗口足够 | 按小阶段继续，阶段节点再查 |
| `CLOSEOUT` / 10 | 五小时剩余 <=30%，或周额度耗尽 | 不开新长步骤；保存、最小检查、交付未完成报告 |
| `UNKNOWN` / 20 | 无 CLI、未取得有效窗口、超时或数据格式不支持 | 说明不可用；查可见 Usage 或 `/status`，提前保存，不编余额 |

周剩余 <=30% 是 `weekly_notice=LOW`，五小时足够时继续工作。只要实际周耗尽就收尾。脚本按窗口的 `windowDurationMins` 匹配 300/10080 分钟，未知时长不冒充五小时窗口；旧响应未给时长时才兼容 primary/secondary 的传统位置。

```sh
python scripts/check_codex_quota.py --five-hour-closeout-percent 25 --json
python scripts/codex_quota_workflow.py admit --estimated-percent 8 --five-hour-closeout-percent 25
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
