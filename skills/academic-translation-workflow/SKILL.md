---
name: academic-translation-workflow
description: Use whenever the user hands over an Indonesian-language academic article, paper, thesis chapter, or journal manuscript (.docx) and wants an English translation delivered to a client - or when they mention a "translation brief", a "segmented translation table", "proposed/final columns", or resend a previously-generated review document to be finalized. Also trigger when the user asks to rebuild or reformat a reviewed translation into a final Word document that matches the original document's formatting exactly. Don't wait for the user to name this skill - any request to translate an Indonesian academic .docx into English for a client, or to turn a filled-in review doc into a final deliverable, should use this workflow rather than an ad hoc translation.
---

# Academic Translation Workflow

Manages a full Indonesian -> English academic-article translation job for a
freelance translator's clients, from intake through final delivery. The
process exists to solve two things a one-shot translation can't: it gives
the translator a structured way to *review and correct* every sentence
before anything is final, and it guarantees the delivered document is
formatted identically to what the client submitted.

**Confidentiality**: these are client documents, often unpublished academic
work. Everything happens locally via the scripts in `scripts/` - never send
document content to any third-party service or API as part of this workflow.

## The pipeline at a glance

```
source.docx --segment_docx.py--> segments.json --(you translate)--> annotated.json
   --build_review_doc.py--> v1_proposed.docx --(translator reviews, resends)--> v2_reviewed.docx
   --read_reviewed_doc.py--> reviewed.json --rebuild_final_docx.py(+ source.docx)--> v3_final.docx
```

All scripts are in `scripts/` and run standalone, e.g.
`python scripts/segment_docx.py source.docx segments.json --client acme`.
They require `python-docx` (`pip install python-docx`) and `lxml` (installed
as its dependency). Run `python scripts/generate_fixtures... ` - no, that one's
eval-only; ignore it for real jobs.

## Step 1 - Intake

Ask (if not already given): the client's name, and roughly what the article
is about. Slugify the client name (lowercase, hyphenated) and check for
`data/<client-slug>/`. If it doesn't exist yet, create it with an empty
`glossary.json` (`[]`) and `style_profile.json` (`{"observations": []}`) -
see `references/data-schema.md` for what goes in these and why they matter
(consistent terminology and tone across every future document for this
client, not just this one).

Name the working files as you go:
`<client-slug>_<short-topic-slug>_v1_proposed.docx` for what you send the
translator, and `..._v3_final.docx` for the finished deliverable. (v2 is
whatever the translator sends back - don't insist on a name for that one,
it's their file at that point.)

## Step 2 - Segment the source

```
python scripts/segment_docx.py <source.docx> segments.json --client <client-slug>
```

This walks the document in true reading order (including table cells, and
real footnotes if the document has them) and produces one row per sentence
for running prose, and one row per paragraph for headings/captions/list
items/table cells/bibliography entries (splitting *those* into sentences
usually does more harm than good on rebuild). Each row gets a stable id like
`p12.s0` or `tbl0_r1_c2_p0.s0` - keep these ids intact through the whole
pipeline, they're what lets the final step find its way back to the exact
right paragraph in the original file.

**Read `segments.json` before moving on.** The sentence splitter is a
heuristic (see `references/known-limitations.md`) and occasionally
mis-splits around abbreviations or unusual punctuation. Fix any rows that
look wrong now - merging two rows that should be one sentence, for
instance - since every later step just trusts what's here.

## Step 3 - Translate and annotate

For each row, write a `proposed` English translation. This is the heart of
the job, so:

- **Check `data/<client-slug>/glossary.json` first.** If a term in this
  document already has a confirmed rendering from a previous job, reuse it
  rather than re-deriving your own - that consistency is the entire reason
  the glossary exists. Add any *new* recurring terms you introduce here too
  (status `"proposed"` until the translator has accepted/corrected a row
  using it at least once).
- **Check `data/<client-slug>/style_profile.json`** for accumulated
  preferences (formality, active vs. passive voice, citation style) and
  lean into them.
- **Italicize every foreign-language word or phrase** (Indonesian or
  otherwise) in the English text using `*term*` markup - e.g. `*gotong
  royong*`. The **first occurrence in the whole document** gets a plain-
  language gloss in parentheses right after it: `*gotong royong* (communal
  work)`. Every later occurrence of that same term stays italic but does
  **not** repeat the gloss. This markup is a lightweight convention the
  scripts parse into real italic runs in the Word output - don't use actual
  Word formatting yourself at this stage, since you're producing JSON.
- Note any foreign word that has a clean, direct English equivalent as such
  in the Key Terminology section instead of treating it as a loanword.

Alongside the rows, write:
- `topic_overview`: a few short paragraphs that would let the translator
  pick this article up cold - what it's about, why it matters, anything a
  non-specialist would need to follow the terminology.
- `terminology`: the list of notable terms and what to know about each
  (loanword vs. direct-equivalent, why you chose the rendering you did).
- `questions`: anything genuinely ambiguous - a word with two plausible
  readings, a sentence whose intended meaning depends on context you don't
  have, a citation format you're unsure about. Don't guess past comfort;
  surface it here instead. Reference specific row ids so the translator
  knows exactly what you mean.

Save all of this as `annotated.json` - same shape as `segments.json`'s rows,
plus `title`, `topic_overview`, `terminology`, and `questions`. (See
`scripts/build_review_doc.py`'s docstring for the exact schema.)

## Step 4 - Build the review document

```
python scripts/build_review_doc.py annotated.json <client-slug>_<topic>_v1_proposed.docx
```

Produces the front-matter briefing (topic overview, terminology table,
open questions with an empty answer column) followed by the segmented
table: ID | Type | Source (ID) | Proposed (EN) | Final (EN), Final left
empty. Send this to the translator.

## Step 5 - Receive the reviewed document

The translator fills in the Final column directly (writing `default` to
accept your proposal, or their own replacement text - using Word's italic
formatting directly if they want something italicized) and answers the
open questions in the same table, then resends the file.

```
python scripts/read_reviewed_doc.py <returned.docx> reviewed.json
```

This extracts every row's resolved text: `default` (or synonyms a human
might reasonably type there - but when in doubt, only exact "default"
counts) falls back to your proposed translation, anything else becomes the
override, and **a row left blank is flagged `unresolved` rather than
silently treated as accepted** - a blank could just as easily mean "I
haven't gotten to this one" as "no changes." If the script warns about
unresolved rows, check with the translator before finalizing rather than
guessing.

While you're here: update `data/<client-slug>/glossary.json` (bump
`status` to confirmed for terms the translator accepted or explicitly
corrected) and `data/<client-slug>/style_profile.json` (only add an
observation once you've actually seen a pattern, not from one data point).

## Step 6 - Rebuild the final document

```
python scripts/rebuild_final_docx.py <ORIGINAL source.docx> reviewed.json <client-slug>_<topic>_v3_final.docx
```

This is the step that guarantees formatting fidelity: it opens the
*original* source file (not a new document) and replaces only the text runs
of translated paragraphs/cells/footnotes, leaving every paragraph's style,
alignment, spacing, numbering, and every image/header/footer completely
untouched. That's why it needs the original file, not the reviewed one -
the reviewed docx's table has none of the source's page layout to preserve.

Deliver the resulting file to the client-side workflow (i.e. give it to the
user).

## When something looks off

Read `references/known-limitations.md` first - most surprises (a nested
table's cells missing, a footnote that didn't translate, a heading that
stayed in Indonesian) trace back to a documented edge case there, and it'll
tell you where to look instead of guessing.
