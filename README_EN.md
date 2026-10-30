<div align="center">

# New Eight Honors.skill

### Give your agent a few working principles.

**Proactive updates · Eight-point reviews · Quota closeout**

Built first for **Codex users**. Put your working standards in `AGENTS.md`.

[Install](#install) · [Real work records](#what-the-work-looks-like) · [The eight principles](#the-eight-principles) · [中文首页](README.md)

</div>

<picture>
  <source media="(max-width: 600px)" srcset="assets/principles-mobile.png" />
  <img src="assets/principles-desktop.png" alt="New Eight Honors: the complete eight principles, shown as an agent's working agreements" width="960" />
</picture>

## What the work looks like

The [Chinese homepage](README.md#实际工作会变成什么样) shows complete messages from the author's actual project on **October 29, 2026**. The task was to check announcements, assignments, and class requirements across nine courses. These local working agreements were later packaged as this skill.

- **A complete report:** results, six concrete findings, coverage gaps, allowance, and next steps come first. The eight-point explanation follows in the same reply. Both parts are displayed together.
- **Closeout with context:** the report showed 33% remaining; subsequent live checks returned 31%, then 27% after checking 36 course modules. At the then-configured 30% reserve, the agent saved its progress and delivered a complete closeout report, including its eight-point explanation.

The original wording, historical **27%**, **21:26** reset time, unfinished work, and continuation status remain. Only local filesystem paths are redacted. The records reproduce the local Codex chat layout; tool rows summarize the recorded tool results, and assistant messages retain their original wording. [Read and copy the complete original records](docs/examples/real-work.md).

**Have Codex close out before its allowance runs out.** During long tasks, the skill directs it to check live allowance, save results at the reserve line, and explain unfinished work and the exact next step. Live quota queries require a working, signed-in Codex CLI.

The default **30%** five-hour reserve comes from the author's Plus workflow: leave room to inspect the result, give feedback, and revise over further turns. Set it to **10%** or another value that suits your work. Automatic wakeup needs a host scheduler; the recorded project explicitly says it had not been configured. [Quota and continuation](references/quota-and-recovery.md).

## The eight principles

The earlier AI coding “eight honors and eight shames” emphasized looking things up, confirming requirements, reusing code, and testing. This version keeps the memorable form and extends it to goals, judgment, real product use, and handoffs. [Background and sources](docs/provenance.md).

**Each principle has its own job:** goals, evidence, reuse, judgment, acceptance, continuity, cost, and communication. They guide the work together.

### 1. Understand the outcome

The agent ticks every word in the request, works for hours, and still leaves the original problem untouched. It confuses actions performed with something useful accomplished for you.

Establish who will use the result, what they need to accomplish, and the time and resource constraints. Choose the approach and judge completion against that outcome.

### 2. Verify before claiming

It draws a conclusion before opening the source, or declares a fix before running the command. A guess arrives dressed as a fact, and your next decision inherits the mistake.

Check primary sources, live state, or real execution results for consequential claims. Make observed facts, informed judgments, and open questions easy to tell apart.

### 3. Find a better solution before rebuilding

It blindly grinds through your suggested implementation without asking whether a higher-level or ready-made solution would solve the problem better. You get a pile of new code and an underwhelming result.

Compare changing a setting, using an existing tool, adapting a mature workflow, and building something new. Inspect the candidates and explain the choice. Small edits stay small.

### 4. Exercise judgment

Your casual suggestion becomes a sacred instruction, even when the approach is failing. Then a routine decision produces another “Should I continue?”, leaving you to do the agent's product thinking.

Separate the intended outcome, proposed methods, and explicit constraints. Own ordinary choices within the authorization. Explain and adjust an approach that works against the goal; use a small experiment when there is a real uncertainty. Ask when the decision changes the goal or crosses an authority boundary.

### 5. Try the actual product

The product is finished and every test supposedly passes. Then you use it, and the experience is awful. You become the tester, finding problems the agent should have caught before handing it over.

Walk through the user's actual task from entry to result. Inspect the page and interactions, read the rendered document, and check an automation's real output. Fix the problems you find, and distinguish technical checks, the observed experience, and decisions still needing the user.

### 6. Leave a usable handoff

Work stops halfway with no readable account of what happened. After allowance resets, you dig through chat, find the files, explain the background again, and guess what the agent intended to do next.

Save results, decisions, verification gaps, and the next action at meaningful stages. Close out near the reserve line and send the handoff in the conversation. On resumption, check the latest instructions and current files before continuing from the existing work.

### 7. Stop wasting effort

The same failure gets another slightly different retry. Plans, checks, and “working on it” updates accumulate while your allowance falls and the problem stays put.

Test the critical route with a small real result. Reassess the conditions and evidence after failure, change route when needed, and finish once the outcome and necessary checks are satisfied.

### 8. Keep the user informed

Tools fill the screen, yet you keep asking what is done, why the direction changed, and whether anything works. A bare file or eight empty slogans still leaves you guessing.

Give brief written updates at discoveries, decisions, blockers, and stage endings. Report results and gaps in normal prose first, then explain the actual work under the eight principles at the end.

## Install

**Codex is the recommended home for this skill.** The agreements grew out of the author's native GPT/Codex workflow: define the goal, let the agent choose methods and use tools, then inspect the result and explain the work. Project rules, quota queries, and handoff helpers are supplied for Codex first.

Give your agent this prompt:

```text
Install and enable https://github.com/Cyh29hao/new-eight-honors-skill in this project.
Read the repository instructions and use scripts/install.py. Back up existing rules,
preserve custom content, report the actual changes, and confirm a new session can read them.
```

Or run in the project directory with Python 3.9+:

```sh
python -c "import urllib.request as u;exec(u.urlopen('https://raw.githubusercontent.com/Cyh29hao/new-eight-honors-skill/main/scripts/install.py',timeout=20).read(262144))"
```

| What you need to know | What happens |
| --- | --- |
| Files changed | The runtime goes in `.agents/skills/eight-honors`. Existing rules are backed up before one managed block is merged into `AGENTS.md`; content outside it is preserved. |
| Where to customize | Change reporting preferences and the quota reserve in the project's `AGENTS.md`, using the same threshold for quota checks. |
| How to start | Open a new Codex session and invoke `$eight-honors`. The invocation name remains compatible with existing installations. |
| Other agents | File- and tool-capable agents can use the principles. Add `--agent claude` for Claude Code installation and invoke `/eight-honors`; the supplied quota queries target Codex. |

[Installation, updates, and backups](docs/installation.md) · [Capabilities and models](docs/compatibility.md)

**Setting principles for an agent is also choosing how we work together.**

Align on the goal, leave room for judgment, judge the result through actual use, and make the work easy to continue. New Eight Honors expresses both the agent's working agreements and my own preferences for work and management.

[Design origin](docs/design-origin.md) · [Sources](docs/provenance.md) · MIT License

By [Cyh29hao](https://github.com/Cyh29hao), also the author of [Shuixian.skill](https://github.com/Cyh29hao/shuixian-skill). MIT License.
