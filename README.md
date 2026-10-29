<div align="center">

# 新八荣八耻.skill

### 给你的 Agent 装上新八荣八耻。

**主动汇报 · 逐条验收 · 额度收尾**

把做事标准写进 `AGENTS.md`，让 Agent 少走弯路，干活有交代。

[看实际记录](#干活有交代长这样) · [一分钟看懂](#一分钟看懂) · **[直接启用](#直接启用)** · [设计思路](#为什么是新八条)

</div>

**这些情况，你可能也见过：**

- **干得很认真，方向却偏了。** 你随口举个例子，它就当成硬要求一路执行；做了不少，最后不是你想解决的问题。
- **说得头头是道，依据却没找。** 关键事实没有核对，现成方案也没比较，就先造出一套自己的做法。
- **看起来一直在忙，成品却没来。** 命令通过、文件导出，就被当成验收完成；同一路线失败，还要反复试几遍。
- **聊天一停，工作就断了。** 过程靠你追问，暂停没有交接。比如 Plus 下还想验收、反馈和修改，额度却先见底，下一轮又要重新解释。

你可能见过旧版 AI 编程八荣八耻，比如“以瞎猜接口为耻，以认真查询为荣”。它在[社区讨论](https://linux.do/t/topic/952503/27)和[开源项目](https://github.com/langbot-app/LangBot/blob/master/AGENTS.md)里流传，重点是查询、确认、复用、测试等编码纪律。**新八荣八耻沿用这套好记的形式，把规则扩展到一次完整的 Agent 协作。**

八条各有独立职责：**目标、证据、复用、判断、验收、接续、成本、沟通**。各管一个痛点，合起来约束整个过程。

<p align="center">
  <picture>
    <source media="(max-width: 600px)" srcset="assets/principles-mobile.png" />
    <img src="assets/principles-desktop.png" alt="新八荣八耻全文与逐条痛点解读" width="960" />
  </picture>
</p>

<details>
<summary>展开八条文字版，方便复制</summary>

1. 以误认目标为耻，以明确成效为荣。
2. 以无据断言为耻，以查证求实为荣。
3. 以闭门造轮为耻，以择优复用为荣。
4. 以照单全收为耻，以独立判断为荣。
5. 以表面达标为耻，以实物验收为荣。
6. 以无声中断为耻，以有据续作为荣。
7. 以无效消耗为耻，以及时收敛为荣。
8. 以黑箱推进为耻，以主动汇报为荣。

</details>

## 干活有交代，长这样

以下来自本人 2026-10-29 的实际项目聊天，按原文排版，只遮本机路径。

### 结果按八条交代

先报告成果，再说明这次怎样理解、查证、选择和验收，哪里还没做到也写清楚。

<picture>
  <source media="(max-width: 600px)" srcset="assets/records/eight_principles-mobile.png" />
  <img src="assets/records/eight_principles-desktop.png" alt="实际工作报告中的完整八条说明" width="920" />
</picture>

### 额度耗尽前，自动收尾

**安装本 skill，让 Codex 在额度耗尽前主动交接。** 在已登录 Codex CLI 的环境中，它会主动查实时余额，到你设定的预留线就保存成果、说明未完成项和下一步。下面这次实际记录，在还剩 **27%** 时就交代了进度。

<picture>
  <source media="(max-width: 600px)" srcset="assets/records/quota_closeout-mobile.png" />
  <img src="assets/records/quota_closeout-desktop.png" alt="真实额度收尾：余额27%，记录中重置时间21:26，仅本机路径遮蔽" width="920" />
</picture>

默认预留 30%，是给 Plus 用户人工验收、反馈和多轮修改留空间，减少过晚收敛的浪费；你可以改成 10% 等其他值。[阈值与接续机制 →](references/quota-and-recovery.md)

<details>
<summary>再看一段：进度主动汇报</summary>

做了什么、遇到什么、下一步查什么，不用一直追问。

<picture>
  <source media="(max-width: 600px)" srcset="assets/records/progress-mobile.png" />
  <img src="assets/records/progress-desktop.png" alt="实际项目中的主动进度汇报" width="920" />
</picture>

</details>

[查看可复制原文与记录说明 →](docs/examples/real-work.md)

## 一分钟看懂

| 你想知道的 | 直接说 |
| --- | --- |
| **这是什么？** | 一套覆盖目标、做法、验收和交接的 Agent 工作规矩。 |
| **会改哪里？** | 安装项目 skill，先备份，再合并 `AGENTS.md` 的专属规则块。 |
| **如何调整？** | 项目规则里改报告频率、工作要求和额度预留线。 |
| **适合谁？** | 能读写文件、调用工具的 Codex / Claude Code 等 Agent。[能力与型号](docs/compatibility.md) |

## 直接启用

**复制给 Agent：**

```text
在当前项目安装并启用 https://github.com/Cyh29hao/new-eight-honors-skill 。
先读 README，使用 scripts/install.py 安装并备份、合并项目规则。
保留其他规则和自定义修改，报告实际改动，并确认新会话能读取。
```

**或者，在项目根目录运行这条命令（Python 3.9+）：**

```sh
python -c "import urllib.request as u;exec(u.urlopen('https://raw.githubusercontent.com/Cyh29hao/new-eight-honors-skill/main/scripts/install.py',timeout=20).read(262144))"
```

安装后开新会话，调用 `$eight-honors`。名字升级，现有调用名和规则标记保留；已有安装继续兼容。Claude Code 加 `--agent claude`，调用 `/eight-honors`。[安装、备份与更新](docs/installation.md)

## 为什么是新八条

Agent 接手的工作越完整，规则越需要管到目标、判断、成品和接续。新八条把这八个职责分开，也把“自己会判断”和“向人交代清楚”一起写进约定。小任务直接做，复杂任务有据可查、有物可验、有路可续。

[设计来由](docs/design-origin.md) · [来源与借鉴](docs/provenance.md) · [验证记录](docs/validation.md) · [分享素材](docs/sharing.md) · [English](README_EN.md)

By [Cyh29hao](https://github.com/Cyh29hao) · [水仙.skill](https://github.com/Cyh29hao/shuixian-skill) · MIT License
