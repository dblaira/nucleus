# Forms slice 7

Base: `9a46317b5575c17c22c3b2fc533a85042a09ec00`. Branch:
`codex/forms-slice-7`. Adam's October 2 ruling restores his graph as the meaning
layer and keeps human-approved forms. Only the review copy runs this slice.

At startup, RDFLib 7.6.0 reads every accepted Turtle file except the exact
`accepted-graph (from github).ttl` duplicate, plus `upper/bfo-bridge.ttl` and the
specified personal-authority axioms. No imports are fetched. No reverse edges,
reasoning or meanings are invented. Literal axiom statements stay literals.

Exact dictionary labels identify word nodes. Copy links become word → named
middle word → accepted Connection triples. Unknown words/kinds, unaccepted
records, inexact quotes and thumb-down links are excluded. Derived triples are
saved in `forms-review/forms-links.ttl`. Export guards protect source files,
ontology directories, symlinks, hard links, temporary aliases and databases.
Thumbs refresh only copied edges; source files remain read only.

Forward SPARQL paths ask whether every dictionary word touched by the normal
reader reaches an accepted record. All: `aligned`; some: `not_sure`; none:
`dont_know`. On graph failure or a shared budget miss, the old count fallback is
explicitly marked `count rule`. The graph day path contains no model or live
explanation call, even with `NUCLEUS_FORMS_ONLY=0`.

Each structured `when` compiles into SPARQL ASK. Readable conditions still own
display and duplicate identity. Generated queries are retained in additive
`form_graph_conditions` with proposal/run IDs; malformed old refusals remain
unchanged. ASK uses a unique temporary screen context in the loaded RDF store.
Only exact visible words, rows, quotes, counts and gaps enter that context.
Hidden triples cannot supply a blank or satisfy a missing middle word. Contexts
are removed after success or failure. Prepared queries are cached; parsing is
serialized. Existing plain-code filling and source checks remain intact.

The path index stores only existing forward adjacency, retaining each original
subject/predicate/object for inspection. Its one-predicate SPARQL path avoids
testing all 43 middle predicates at every hop. The full RDF and exported named
middle-word triples remain unchanged by that optimization.

A startup step stores build time, source hashes and graph statistics. Each graph
answer stores label time, form time, total milliseconds, the 300 ms budget and
misses. Form time includes projection, compilation, execution and cleanup. A
combined budget miss stops further form checks, discards the form, logs a miss
and uses the named count fallback. A hidden dictionary hit cannot become a
blank on the fixed `dont_know` screen.

Night practice uses the same graph ask path. Old screens are explicitly
replayed under current graph labels, with graph evidence beside the recovered
screen. Original answer text, words, records, missing fields and quotes are
never rewritten or enriched. The review page identifies graph-replayed fits.
Distinct-question counts, three-question/two-word/one-real-question floors,
exact screen-only blanks, fifth-grade frames, no advice, same-form refusal and
Adam's Yes all remain in force.

One manual pass generated 20 new practice screens and four candidates. None
passed: F-43/F-46 contained negative wording; F-44/F-45 read at grades 8/9.
The first query timings had five budget misses. A faithful path-index fix
preserved all reached record sets. Twenty appended timing rechecks of those
same saved word sets now take 2.098–42.111 ms, median 7.413 ms, with zero misses.
No second pass, new question or model call was used for that recheck. Original
answers and first timing traces remain intact. Startup took 422.240 ms for
14,591 triples; one form ASK took 5.256 ms cold and 0.938 ms warm. Startup is
outside the per-answer query budget. **488 tests pass.**

Run from this worktree, using its own environment and `requirements.txt`:

```sh
NUCLEUS_FORMS_ONLY=0 .venv/bin/python -m nucleus.serve --port 8767 \
  --store "$HOME/Library/Application Support/nucleus/forms-review/nucleus.sqlite3"
```

Default arguments still select 8766/live with their existing nongraph route.
Graph mode requires a copy before binding or opening SQLite; graph asks require
an explicit connected copy. No live environment or launchd job is changed.

Full questions, source quotes, model traces, RDF and screenshots remain local;
the nucleus repository is public. Companion JSON files contain only sanitized
night and preservation evidence. Nothing is approved or merged. Stop at slice 7.
