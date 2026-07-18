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
                                            --build_catatan.py(+ editorial_notes.json)--> catatan_penyuntingan.docx
```

The final deliverable is **two** files: `v3_final.docx` and its
`catatan_penyuntingan.docx` (editing notes). Don't hand over one without the
other - see Step 6.

All scripts are in `scripts/` and run standalone, e.g.
`python scripts/segment_docx.py source.docx segments.json --client acme`.
They require `python-docx` (`pip install python-docx`) and `lxml` (installed
as its dependency). Run `python scripts/generate_fixtures... ` - no, that one's
eval-only; ignore it for real jobs.

## Step 1 - Intake

Ask (if not already given): the client's name, and roughly what the article
is about. Slugify the client name (lowercase, hyphenated).

Per-client glossaries live in a **separate, private `translation-glossary`
repo** - deliberately not inside this skill folder, since this skill's own
code is public and glossaries hold real (often confidential) client
terminology. It's cloned locally at **`~/translation-glossary`** (fall back
to asking only if that path doesn't exist). Look for
`~/translation-glossary/<client-slug>/`. If it doesn't exist yet, create it
with an empty `glossary.json` (`[]`) and `style_profile.json`
(`{"observations": []}`) - see that repo's own README for the schema and why
these matter (consistent terminology and tone across every future document
for this client, not just this one). After a job, commit and push the
glossary/style-profile changes so the next session (or machine) has them.

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

**Watch for `citation_fields` on a row.** If the source document's in-text
citations were inserted by a reference manager (Zotero, Mendeley, EndNote's
"Insert Citation"), they're not plain text - they're a live field linked to
the client's reference library. `segment_docx.py` detects these and lists
each field's exact visible text (e.g. `"(Bhambra, 2021)"`) on the row. The
rebuild step re-links each field by finding that exact substring in the
translated sentence, so when you translate such a row, **reproduce that
citation text byte-for-byte** - don't touch capitalization, spacing, or
"dkk." vs "et al." style choices within it, even if the rest of the sentence
changes completely around it. Getting this wrong doesn't break anything
loudly; it just quietly turns that one citation into dead, unlinked text in
the final document.

## Step 3 - Translate and annotate

For each row, write a `proposed` English translation. This is the heart of
the job, so:

- **Check `~/translation-glossary/<client-slug>/glossary.json` first.**
  If a term in this document already has a confirmed rendering from a
  previous job, reuse it rather than re-deriving your own - that consistency
  is the entire reason the glossary exists. Add any *new* recurring terms
  you introduce here too (status `"proposed"` until the translator has
  accepted/corrected a row using it at least once).
- **Check `~/translation-glossary/<client-slug>/style_profile.json`**
  for accumulated preferences (formality, active vs. passive voice, citation
  style) and lean into them.
- **Italicize every foreign-language word or phrase** (Indonesian or
  otherwise) in the English text using `*term*` markup - e.g. `*gotong
  royong*`. The **first occurrence in the whole document** gets a plain-
  language gloss in parentheses right after it: `*gotong royong* (communal
  work)`. Every later occurrence of that same term stays italic but does
  **not** repeat the gloss. This markup is a lightweight convention the
  scripts parse into real italic runs in the Word output - don't use actual
  Word formatting yourself at this stage, since you're producing JSON.
  Word order doesn't change this: if you translate a phrase into English
  first and cite the original term afterward for precision - "the community
  (*umat*)", "a civilized human being (*insan beradab*)" - that parenthetical
  term is still a foreign word and stays italicized, exactly as it would if
  it came first. It's tempting to drop the italics here since the gloss
  already did its job, but italics mark "this is a foreign word," not "this
  is unfamiliar," so the position of the word doesn't matter. Treat dropping
  it as a specific client's style preference to confirm and record in
  `style_profile.json`, not a default to apply on your own judgment.
- Note any foreign word that has a clean, direct English equivalent as such
  in the Key Terminology section instead of treating it as a loanword.
- **Bibliography entries, and citation-style content embedded inside table
  cells** (author/year/title/publisher lists - common in tables that survey
  course reading lists or literature), **default to pass-through** (English
  proposed = original source text, untouched) rather than translation. This
  isn't laziness - retranslating a cited work's actual title misrepresents
  it. On a large document this can be the majority of the row count, so
  don't burn translation effort on it: check whether a row's `type` is
  `bibliography`, or whether its content is obviously a citation (author
  name, year, publisher), and leave `proposed` equal to `source` for those.
  Flag the default itself once in `questions` so the translator can override
  specific entries if they want a bracketed English gloss instead.
- **Watch for a stray lone period followed by a lowercase verb** (e.g. "...
  setiap hari. . menunjukkan bahwa...") - this is a common sign that the
  author's own citation got accidentally deleted while editing the draft,
  not a punctuation quirk to normalize silently. Before guessing, check
  whether a distinctive term right after the gap (a coined phrase like
  "cognitive empire") matches an entry in the References list - if it does,
  that's almost certainly the missing citation, and you can insert it in
  brackets and ask the translator to confirm rather than leaving the gap
  unexplained or silently smoothing the sentence over.
- **Check every table has a caption.** Real drafts are inconsistent about
  this - a document can caption Table 2 and Table 3 properly while leaving
  Table 1 with no "Table N. Title" paragraph at all. If a table lacks one,
  don't just leave it uncaptioned in the final document: propose a caption
  based on the section heading immediately above the table and the table's
  own content (the same way the document's *other* captions echo their
  section's argument), and add it to `questions` for confirmation before
  treating it as final.

### Highlighting editorial interventions (feeds the catatan penyuntingan)

Whenever your translation of a row does something the author would want to
know about and check - anything beyond a faithful sentence-for-sentence
rendering - **wrap the affected span in `{{...}}` markup** so it renders as a
yellow highlight in every document, and **record a matching entry in
`editorial_notes.json`** explaining why. The two always travel together: a
highlight with no note becomes an unexplained yellow blob in the deliverable,
and a note with no highlight has nothing to point at. Typical cases:

- a missing citation you're flagging: `{{[butuh sitasi]}}`
- a predicted/inferred citation the author must verify:
  `{{(Prediksi: Ndlovu-Gatsheni, 2020)}}`
- a sentence you rewrote because the source was confusing, or split into
  several because it carried more than one main idea (or merged)
- a genuinely ambiguous passage where you had to pick a reading

`editorial_notes.json` is a list you maintain as you translate, one entry per
highlight, that you keep locally through the whole job (the translator's Word
review only round-trips the table, not this file):

```json
[
  {"id": "p24.s2", "category": "predicted-citation",
   "highlighted": "(Prediksi: Ndlovu-Gatsheni, 2020)",
   "note": "Sumber punya celah sitasi; 'cognitive empire' cocok dengan entri daftar pustaka. Mohon verifikasi."}
]
```

`id` is the row id; `highlighted` is the exact inner text of the `{{...}}`
span (only needed to disambiguate a row with more than one highlight);
`category` is one of `needs-citation`, `predicted-citation`, `rewritten`,
`split`, `merged`, `ambiguity`, `other`; `note` is written **for the
Indonesian author** (Indonesian, or bilingual) since they're the audience for
the catatan. Don't over-highlight - a clean, faithful sentence needs no
highlight and no note. Reserve it for interventions the author should sign
off on.

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

While you're here: update `~/translation-glossary/<client-slug>/glossary.json`
(bump `status` to confirmed for terms the translator accepted or explicitly
corrected) and `~/translation-glossary/<client-slug>/style_profile.json`
(only add an observation once you've actually seen a pattern, not from one
data point).

## Step 6 - Rebuild the final document (and its catatan penyuntingan)

```
python scripts/rebuild_final_docx.py <ORIGINAL source.docx> reviewed.json <client-slug>_<topic>_v3_final.docx
python scripts/build_catatan.py reviewed.json editorial_notes.json <client-slug>_<topic>_catatan_penyuntingan.docx
```

The first command guarantees formatting fidelity: it opens the *original*
source file (not a new document) and replaces only the text runs of
translated paragraphs/cells/footnotes, leaving every paragraph's style,
alignment, spacing, numbering, and every image/header/footer completely
untouched. That's why it needs the original file, not the reviewed one -
the reviewed docx's table has none of the source's page layout to preserve.
It also renders every `{{...}}` span as a yellow highlight.

The second command produces the **catatan penyuntingan** - the editing-notes
document that must ship *alongside* the final file. It reconciles your
`editorial_notes.json` against the highlights that actually survived into the
final text and produces one explained entry per highlight (in Indonesian, for
the author). Watch its output:

- a **highlight with no note** is flagged in the catatan as unexplained -
  either add the missing note to `editorial_notes.json` and rerun, or (if the
  highlight was never meant to be there) remove it and rebuild.
- a **note with no live highlight** means the translator edited that span
  away during review; the note is dropped from the catatan with a warning,
  which is usually correct - just sanity-check it wasn't a mistake.

Both should come out clean before you deliver.

**Deliver both files together** (`v3_final.docx` + `catatan_penyuntingan.docx`).
A final document with unexplained yellow highlights and no accompanying
catatan is an incomplete deliverable - the whole point of the highlight is
that the author can find the passage *and* read why it's flagged.

## When something looks off

Read `references/known-limitations.md` first - most surprises (a nested
table's cells missing, a footnote that didn't translate, a heading that
stayed in Indonesian) trace back to a documented edge case there, and it'll
tell you where to look instead of guessing.
