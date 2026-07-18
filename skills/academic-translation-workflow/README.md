# academic-translation-workflow

A Claude Code / Claude Agent SDK skill for running an Indonesian → English
academic-article translation job end to end: source `.docx` in, a
segmented review table out, a reviewed table back in, a final `.docx` out
that matches the source's formatting exactly.

`SKILL.md` is the actual instruction file Claude reads - this README is for
humans browsing the repo. See `SKILL.md` for the full step-by-step workflow.

## What it does

1. Segments a source document into a reviewable table (one row per
   sentence/heading/table cell/footnote/bibliography entry), preserving
   stable row IDs back to the original document structure.
2. Drafts an English translation for each row, plus a topic-overview
   briefing, a terminology list, and open questions for the translator -
   all in a single Word document.
3. Reads the translator's filled-in review table back (`default` to accept,
   or a written override) and any answered questions.
4. Rebuilds the final document by editing the *original* source file in
   place - so margins, fonts, colors, styles, images, and table layout come
   out identical to what the client submitted, not regenerated from
   scratch.

Also handles: real Word footnotes, in-text citations inserted by reference
managers (Zotero/Mendeley/EndNote - preserved as live fields, not flattened
to dead text), and a lightweight `*italic*` / `{{highlight}}` markup
convention for foreign-word italics and editorial flags.

## Requirements

```
pip install -r requirements.txt   # python-docx, lxml
```

## Client data lives elsewhere, on purpose

This skill's code is public. Per-client glossaries and style profiles
(`glossary.json` / `style_profile.json`) hold real, often confidential
client terminology, so they're **not** stored anywhere in this repo -
`SKILL.md` expects them in a separate, private `translation-glossary` repo
that you check out locally and point the skill at. See that repo's README
for the schema.

## Layout

```
SKILL.md              - the actual skill instructions (read this first)
scripts/               - segment_docx.py, build_review_doc.py,
                          read_reviewed_doc.py, rebuild_final_docx.py,
                          docx_utils.py (shared helpers)
references/             - known-limitations.md (edge cases worth knowing about)
evals/                  - test fixtures and eval cases for skill-creator
```

## Installing

Copy this folder into your Claude Code / Claude Agent SDK skills directory,
e.g. `~/.claude/skills/academic-translation-workflow/`.
