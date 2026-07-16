# Client data schema

Each client gets a folder under `data/<client-slug>/` (slug = lowercase,
hyphenated version of whatever name the translator gives you, e.g. "Universitas
Sari" -> `universitas-sari`). Create the folder the first time you work with a
new client. Two files live in it:

## `glossary.json`

A flat list, one entry per source term that's been translated at least once.
Read this file at the start of Step 3 (translating) for the current client
and reuse any matching term's `target_term` instead of re-deriving it -
that's the whole point of keeping it.

```json
[
  {
    "source_term": "gotong royong",
    "target_term": "gotong royong",
    "gloss": "communal work",
    "notes": "No single-word English equivalent; kept as an italicized loanword per academic convention.",
    "status": "confirmed",
    "first_seen_in": "universitas-sari_gotongroyong_v1_proposed.docx",
    "last_confirmed": "2026-07-16"
  }
]
```

- `target_term` is what you actually put in the translation (for loanwords,
  usually identical to `source_term` but still worth recording so future
  documents are consistent even if you ever change your mind about it).
- `status` is `"confirmed"` once the translator has accepted or corrected a
  row using this term at least once; `"proposed"` if you're using it for the
  first time and haven't seen it get accepted/overridden yet.
- When a translator overrides a row that contains a glossary term with a
  *different* rendering of that term, update the entry (`target_term`,
  bump `status` back to reflect the correction, update `last_confirmed`)
  rather than leaving stale data - the whole file should reflect the
  translator's most recent preference, not history for its own sake.

## `style_profile.json`

Freeform running notes on this client/translator's preferences, built up from
patterns in what they accept vs. override. Keep it short and only add an
entry when you notice an actual pattern (not from a single data point) -
this is meant to sharpen future proposals, not become a log.

```json
{
  "observations": [
    "Prefers \"et al.\" over spelling out all authors in-text (seen across 2+ documents).",
    "Leans toward active voice even when the Indonesian original uses passive constructions."
  ]
}
```

Before drafting proposed translations for a returning client, skim this file
and lean into the preferences it records.
