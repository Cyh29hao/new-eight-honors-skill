# 来源、借鉴与这次改写

## 概念已有历史

常见的 AI 编程八荣八耻包括“以瞎猜接口为耻，以认真查询为荣”等表达，可见 [LangBot 的 AGENTS.md](https://github.com/langbot-app/LangBot/blob/master/AGENTS.md)。[2025-08-29 的 LINUX DO 帖子](https://linux.do/t/topic/917534)也已收录类似版本；它能证明当时已传播，不能据此确认最早作者。

[wangcangxing/ai-eight-honors-eight-shames](https://github.com/wangcangxing/ai-eight-honors-eight-shames)已经把相同概念打包为 skill，并提供 AGENTS.md 接入和报告留痕。所以本仓库不主张“首创八荣八耻”“首次 skill 化”“首次让 Agent 汇报”。原有项目、商标与文字权利归各自作者。

## 作者这版的具体内容

本机规则逐步形成，参考文档中保留了 2026-10-21 修订标记；本仓库于 2026-10-29 将当前偏好整理公开。它把八条改写为目标、证据、方案、决策权、产物、接续、成本和沟通八个职责，覆盖研究、创作、工程与桌面工作。

可辨认的组合是：区分用户目的与候选方法；授权内由 Agent 判断；真实产物验收；正常报告后附八条具体说明；提前保留额度收尾；检查点、调度和实际恢复分开验证；小任务不增加庞大流程。这是作者的工作偏好与实现组合，不是对社区全部实践的独有性声明。

公开包没有照搬整份本机 AGENTS.md，也不包含账户数据、私人路径、课程与第三方项目资料。原本的全局规则保持独立。

## 实际采用哪些成熟方案

| 参考 | 实际采用 | 没有照搬的部分与原因 |
| --- | --- | --- |
| [水仙.skill](https://github.com/Cyh29hao/shuixian-skill) | 一句话定位、首屏视觉、自然语言安装入口、具体体验示例、深入说明拆到文档 | 人格设定和已有社区收录属于水仙，不能当作本项目背书 |
| [obra/superpowers](https://github.com/obra/superpowers) | 解释可见工作过程、模块化入口、明确验证与安装说明 | 不复制强制审批/TDD/代理链；这里按任务规模决定流程 |
| [anthropics/skills](https://github.com/anthropics/skills) | `SKILL.md` 与按需参考资料的目录形式 | 格式兼容不能证明跨宿主效果，未借用官方认可说法 |
| [Codex Skills](https://learn.chatgpt.com/docs/build-skills) 与 [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md) | 按需技能与长期规则分工，项目/用户范围与层级 | 本仓库不改客户端的加载机制，不保证每轮自动匹配 |
| [Codex App Server](https://learn.chatgpt.com/docs/app-server) | 只读额度查询接口与实际窗口元数据 | 不消费重置券，不固定假定所有账户都有同样窗口 |
| [QuotaGuard](https://github.com/LUMOSSES/QuotaGuard) | 阶段预留、原子交接的设计启发；复用作者已实现的两个本机工具 | 未复制上游源码，未引入其依赖或把交接读取当作调度 |
| OpenAI 本机 `skill-installer` | 检查了 ZIP 下载、路径验证和现有目录保护的成熟做法 | 它不负责本项目的规则备份和标记块合并，因此独立补上项目安装、重复更新和失败恢复；没有复制上游源码 |
| [Anthropic: Building effective agents](https://www.anthropic.com/research/building-effective-agents) | 从简单方法开始、使用环境反馈、设置停止条件的设计参考 | 这篇文章不能为本 skill 的实际成功率背书 |

自行制作的是这版八条的职责与裁决方式、报告和接入说明、公开包装及视觉素材。额度工具来自作者已有实现，公开前通用化并测试；无需新增 Python 依赖。

当前首页使用 2026-10-29 同一实际项目的消息节选，完整八条标题已与本版规则核对。图片是原文排版，原始私人日志未发布；并非原生界面截图。设计来由另据 2026-10-21 原始讨论整理，用户原话与助手解释分开，见[设计脉络](design-origin.md)。

## 能主张与不能主张的效果

可以检查文件是否完整、脚本是否正确处理额度、交接能否读取，以及具体任务的报告和行为。不能从单次运行推出普遍成功率、节省额度百分比、所有型号兼容或“永不中断”。[验证记录](validation.md)按层次列出证据与缺口。
