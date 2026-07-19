# academic-translation-workflow

A Claude Code / Claude Agent SDK skill for running an Indonesian → English
academic-article translation job end to end: source `.docx` in, a
segmented review table out, a reviewed table back in, a final `.docx` out
that matches the source's formatting exactly.

`SKILL.md` is the actual instruction file Claude reads - this README is for
humans browsing the repo. See `SKILL.md` for the full step-by-step workflow.

## The process (Step 1–6)

The job runs as a six-step pipeline. Each step has a small standalone script
under `scripts/`; the translation and judgment happen in between, done by
Claude and reviewed by a human. The data flows like this:

```
source.docx --(2)--> segments.json --(3)--> annotated.json --(4)--> v1_proposed.docx
   --(translator reviews & resends)--> v2_reviewed.docx --(5)--> reviewed.json
   --(6)--> v3_final.docx  +  catatan_penyuntingan.docx
```

**1. Intake.** Note the client's name and what the article is about. The
skill slugifies the client name and looks up that client's glossary and style
profile (kept in a separate private repo — see below), so terminology and
tone stay consistent with any previous jobs for the same client. Working
files are named by stage: `<client>_<topic>_v1_proposed.docx`,
`…_v3_final.docx`.

**2. Segment the source** (`segment_docx.py`). Walks the document in true
reading order — body text, table cells, and real footnotes — and produces
`segments.json`: one row per sentence for running prose, one row per unit for
headings, captions, list items, table cells, and bibliography entries. Every
row gets a stable ID (e.g. `p12.s0`, `tbl0_r1_c2_p0.s0`) that ties it back to
the exact spot in the original file. In-text citations from a reference
manager (Zotero/Mendeley/EndNote) are detected and flagged here.

**3. Translate and annotate.** Claude drafts an English translation for each
row, reusing the client glossary, italicizing foreign terms (with a
first-occurrence gloss), passing bibliography/citation text through
untouched, and highlighting any editorial intervention — a missing or
predicted citation, a sentence rewritten or split for clarity — with a note
recorded for the author. The result is `annotated.json` plus a topic
overview, terminology list, and open questions for the translator.

**4. Build the review document** (`build_review_doc.py`). Produces
`v1_proposed.docx`: a briefing (overview, terminology, questions) followed by
a segmented table — `ID | Type | Source | Proposed (EN) | Final (EN)` — with
the Final column left empty. This goes to the translator.

**5. Receive the reviewed document** (`read_reviewed_doc.py`). The translator
fills the Final column — `default` to accept each proposal, or their own
replacement — and answers the questions, then resends the file (`v2`). The
script reads it back into `reviewed.json`, resolving each row's final text. A
row left blank is flagged as unresolved rather than silently accepted.

**6. Rebuild the final document + catatan** (`rebuild_final_docx.py`,
`build_catatan.py`). Rebuilds `v3_final.docx` by editing the *original*
source file in place, so margins, fonts, colors, styles, images, and table
layout come out identical to what the client submitted — never regenerated
from scratch. Alongside it, `build_catatan.py` produces the *catatan
penyuntingan* (editing-notes document) explaining every highlighted passage
for the author. **The deliverable is both files together.**

Also handles along the way: real Word footnotes; reference-manager citations
preserved as live fields (not flattened to dead text); and a lightweight
`*italic*` / `{{highlight}}` markup convention for foreign-word italics and
editorial flags.

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
                          build_catatan.py, docx_utils.py (shared helpers)
references/             - known-limitations.md (edge cases worth knowing about)
evals/                  - test fixtures and eval cases for skill-creator
```

## Installing

Copy this folder into your Claude Code / Claude Agent SDK skills directory,
e.g. `~/.claude/skills/academic-translation-workflow/`.
