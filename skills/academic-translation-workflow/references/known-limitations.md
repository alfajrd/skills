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

**Bibliography detection is heading-text-based.** A paragraph is treated as a
bibliography entry once a heading matching "Daftar Pustaka" / "References" /
similar has been seen, until the next heading. If a source document doesn't
use a recognizable heading for its reference list, entries will be
classified as ordinary body/list paragraphs instead - harmless (they still
get a row and get translated), just not flagged with the `bibliography` type.
Bibliography entries are typically left as the original citation (title
untranslated, or with a bracketed translation added) rather than fully
translated - use judgment per academic convention, and ask the translator in
the Questions section if unsure.

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
