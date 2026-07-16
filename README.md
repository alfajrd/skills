# skills

A collection of [Claude Code](https://claude.com/claude-code) / Claude Agent SDK skills authored by [@alfajrd](https://github.com/alfajrd).

## Skills

- [`academic-translation-workflow`](./skills/academic-translation-workflow) — Manages an Indonesian → English academic-article translation job end to end: segments a source .docx into a reviewable table, tracks a per-client glossary/style profile across jobs, and rebuilds the final document by editing the original file in place so formatting matches exactly.
- [`verdict-quality-critic`](./skills/verdict-quality-critic) — Two-gate validate-and-critique pipeline for LLM outputs that produce structured judgments (scored reviews, multi-axis evaluations, verdicts).

## Related

- [**shipyard**](https://github.com/alfajrd/shipyard) — a 4-agent dev team for Claude Code: `/ship` runs a feature through planner → coder → tester → reviewer. Lives in its own repo (subagents + a slash command, not a skill).

## Usage

Each skill folder is self-contained. To install a skill into your Claude Code or Claude Agent SDK setup, copy the folder into your skills directory (e.g., `~/.claude/skills/<name>/`).
