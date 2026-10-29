<div align="center">

# Eight Honors.skill

### Working agreements for an agent you want to keep working with.

Clear outcomes · Grounded claims · Real artifacts · Recoverable progress

[中文首页](README.md) · [Skill instructions](SKILL.md) · [Installation](docs/installation.md) · [Validation](docs/validation.md)

</div>

![Eight Honors: finish the work and explain it clearly](assets/hero.png)

This is my personal collaboration style, packaged as an Agent Skill: understand the intended outcome, make routine decisions within authorization, inspect the actual result, and keep the user informed. Small tasks stay small.

The Chinese “eight honors and eight shames” framing already existed in AI coding communities, including [earlier skills](https://github.com/wangcangxing/ai-eight-honors-eight-shames). This project presents my revised agreements and practical Codex integration. It makes no originality or measured productivity claims.

| # | Agreement |
| --- | --- |
| 1 | Clarify intended outcomes instead of solving the wrong problem. |
| 2 | Verify consequential claims and distinguish facts, inference, and unknowns. |
| 3 | Find and evaluate mature solutions before building nontrivial replacements. |
| 4 | Exercise judgment within authorization; distinguish goals from suggested methods. |
| 5 | Inspect actual artifacts against their intended use. |
| 6 | Save progress and deliver a readable handoff before a foreseeable interruption. |
| 7 | Stop ineffective routes and converge after relevant checks pass. |
| 8 | Proactively explain progress, decisions, evidence, and limitations. |

## Install in a Codex project

```sh
git clone https://github.com/Cyh29hao/eight-honors-skill .agents/skills/eight-honors
```

Invoke `$eight-honors` in that project. For persistent preferences, merge the marked block in [AGENTS.fragment.md](references/AGENTS.fragment.md) into your existing project `AGENTS.md`, preserving other rules. Codex's default filename is `AGENTS.md`, with an S. Installation alone does not prove a skill was loaded in a particular conversation.

The skill instructions and detailed guides are primarily Chinese. By default, work reports start with the actual outcome, evidence, limitations, and next action, followed by eight short explanations using the full Chinese principle titles. Pure Q&A does not need this appendix. You can override the reporting frequency in your project agreements.

## Optional Codex quota tools

Requires Python 3.9+ and a signed-in Codex CLI supporting App Server. No third-party Python packages are needed.

```sh
python .agents/skills/eight-honors/scripts/check_codex_quota.py --json
```

Five-hour allowance at or below 30% triggers closeout. Weekly allowance at or below 30% is a notice; weekly exhaustion requires closeout. Unavailable or unrecognized data returns `UNKNOWN`.

`codex_quota_workflow.py` offers live stage advice, atomic checkpoint saves, and historical readback. **`resume` never runs commands. No automatic wakeup scheduler is bundled.** Actual continuation needs user authorization and a verified host mechanism. These helpers advise the agent; they do not intercept every model request or guarantee delivery after a sudden failure.

Choose a model that reliably follows instructions and uses your tools. Files, shell, visual inspection, quota access, and scheduling are separate host capabilities. Other Agent Skills hosts can reuse the instructions, but cross-host behavior has not been certified. See [validation](docs/validation.md), [customization](docs/customization.md), and [sources](docs/provenance.md).

By [Cyh29hao](https://github.com/Cyh29hao), also the author of [Shuixian.skill](https://github.com/Cyh29hao/shuixian-skill). MIT License.
