# Known limitations of the docx pipeline

Worth knowing before you trust the scripts blindly on an unusual document.

**Sentence splitting is heuristic.** `segment_docx.py`'s splitter handles
common Indonesian academic abbreviations (dkk., dll., dst., titles like Dr./Prof.,
decimal numbers) but will occasionally over- or under-split on unusual
punctuation. Always skim `segments.json` before translating and merge/fix any
obviously wrong splits - everything downstream just trusts whatever rows are
in the file at that point, so this is the cheapest place to catch it.

Concretely: "dkk." (et al.) is treated as an abbreviation that usually
doesn't end a sentence, but sometimes it genuinely does - e.g. "...menurut
Susanto dkk. Penelitian ini bertujuan..." is two sentences, not one, even
though "dkk." is on the abbreviation list. There's no way to resolve this
kind of case mechanically (it depends on meaning, not punctuation), which is
exactly why this is a review step and not something to "fix" in the
splitter itself.

**One level of table nesting.** A table inside a table cell is not walked
into. If the source document has nested tables, those inner cells won't show
up as rows - check for this manually if the document contains complex tables.

**Headings/captions/list items/table cells are not sentence-split**, even if
they contain multiple sentences (rare for these paragraph types, but
possible for e.g. a long list item). They become a single row instead. If you
hit a genuinely multi-sentence one, translate it as a unit rather than
forcing a split that the rebuild step wouldn't know how to reverse.

**Bibliography detection is text-based.** A paragraph starts bibliography
mode when it matches "Daftar Pustaka" / "References" / "Bibliografi" as its
ENTIRE text, whether it's styled as a real Word heading or just a bare
paragraph (common in draft manuscripts that don't use heading styles
consistently) - everything after it, until the next heading, is treated as
a `bibliography` row. If a source document's reference list uses some other
marker entirely (e.g. a language/spelling this regex doesn't cover), entries
fall back to being classified as ordinary body/list paragraphs - harmless
(they still get a row and get translated), just not flagged with the
`bibliography` type, so skim the end of `segments.json` to check. Bibliography
entries are typically left as the original citation (title untranslated, or
with a bracketed translation added) rather than fully translated - use
judgment per academic convention, and ask the translator in the Questions
section if unsure.

**Reference-manager citation fields (Zotero/Mendeley/EndNote) are preserved
as live fields on rebuild**, not flattened to plain text - see the
"Watch for `citation_fields`" note in `SKILL.md` Step 2. This works by
finding the field's exact visible text again inside the translated sentence
and splicing the original field XML back in around it; if that exact text
isn't found (because the citation itself got reworded during translation),
`rebuild_final_docx.py` prints a `WARNING` naming the affected paragraph and
falls back to writing the citation as plain, unlinked text rather than
failing - check any such warning before delivering, since it means that one
citation lost its live link back to the client's reference library. This
preservation only applies to `apply_translated_text`'s normal paragraph/cell
path; it has not been extended to `write_footnotes` (footnote text), so a
citation field embedded inside a footnote will currently be flattened - flag
this to the translator if you spot one.

**Footnotes require `word/footnotes.xml` to already exist** in the source
file, which it will for any real Word document that has actual footnotes.
The read/write logic accesses this part directly via XML (python-docx has no
footnote API) - this is more fragile than the main body-paragraph path, so
if a document's footnotes look wrong after rebuild, check `word/footnotes.xml`
directly (it's just a zip entry) rather than assuming the rest of the
pipeline is also broken.

**The `*italic*` markup convention** assumes source text doesn't itself
contain literal asterisks. Academic Indonesian prose essentially never does,
but if you ever hit one, escape or reword around it rather than fighting the
convention.

**Headers/footers/comments/tracked-changes** are not touched by this pipeline
at all - they pass through unmodified. If a source document's title or
running head lives in a header (not the body), it won't be picked up by
`segment_docx.py` and will stay in Indonesian in the final document. Check
for this on documents with unusual title placement.
