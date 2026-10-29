<div align="center">

# New Eight Honors.skill

### Give your agent a few working principles.

**Proactive updates · Eight-point reviews · Quota closeout**

[中文首页](README.md) · [Real project records](docs/examples/real-work.md) · [Install](#install) · [Design](docs/design-origin.md)

</div>

![The complete eight principles](assets/principles-desktop.png)

An Agent Skill that brings your working agreements into a project's `AGENTS.md`: understand the goal, verify claims, reuse mature solutions, make decisions within authority, inspect real results, preserve progress, stop wasted effort, and explain the work.

## What it looks like in practice

The Chinese homepage shows original excerpts from an actual project on **October 29, 2026**: the complete current eight-principle appendix, quota closeout, and a foldout progress update. Only local filesystem paths are redacted; the historical 27% allowance and 21:26 reset time remain. The images are typeset original messages, not native app screenshots.

[Read the original records](docs/examples/real-work.md). They preserve unfinished work and unverified parts; they are not a controlled model comparison.

## At a glance

| Question | Answer |
| --- | --- |
| What is it? | A reusable skill, persistent project agreements, and Codex quota/handoff helpers. |
| What does it address? | Wrong goals, unsupported claims, unnecessary rebuilding, superficial acceptance, and missing handoffs. |
| What changes? | Visible progress, decisions backed by evidence, an eight-point explanation after work reports, and early closeout. |
| What files change? | Project skill files and one managed block in `AGENTS.md`, with prior rules backed up. |
| What do I need? | Python 3.9+ for the installer; a tool-capable agent for actual file work. |

## Install

Run in your project directory:

```sh
python -c "import urllib.request as u;exec(u.urlopen('https://raw.githubusercontent.com/Cyh29hao/new-eight-honors-skill/main/scripts/install.py',timeout=20).read(262144))"
```

The command downloads and executes the readable [installer](scripts/install.py). It installs the runtime in `.agents/skills/eight-honors`, backs up existing rules, and merges one marked block. Repeating it does not append duplicate rules. Custom edits are protected. Add `--dry-run` for a zero-write preview, `--project PATH` to choose a project, or `--agent claude` for project Claude paths.

Open a new Codex session and invoke `$eight-honors`. For Claude Code use `/eight-honors`; actual Claude session loading has not been certified. [Installation details](docs/installation.md).

The repository and display name are now New Eight Honors. The invocation name, installation directory, managed markers and ownership format remain compatible with existing installations.

You can also give a file-capable agent the repository URL and ask it to read the README, install the runtime, back up and merge project rules, preserve custom content, and report which files changed.

## Your preferences, your rules

By default, work reports give results, evidence and limitations first, then explain the work under the eight full Chinese principle titles. Pure Q&A skips the appendix; small tasks stay small. Change reporting frequency in your project rules.

The default 30% five-hour reserve reflects the author's Plus workflow: leave room to inspect results, give feedback and revise over further turns. It is adjustable. Weekly low allowance is informational; actual exhaustion requires closeout. The quota helpers use Codex's read-only App Server interface. `resume` reads historical handoffs; actual wakeup needs a host scheduler.

The earlier coding “eight honors and eight shames” concept already existed. This version separates goals, evidence, reuse, judgment, acceptance, continuity, cost and communication for broader agent work. [Design origin](docs/design-origin.md) · [Sources](docs/provenance.md) · [Capabilities and models](docs/compatibility.md) · [Validation](docs/validation.md)

By [Cyh29hao](https://github.com/Cyh29hao), also the author of [Shuixian.skill](https://github.com/Cyh29hao/shuixian-skill). MIT License.
