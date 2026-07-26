# Detective Corpus Candidate Fixtures

This directory contains provisional candidate annotations for public-domain
detective stories. They are intended to exercise the Epistemap fair-play
detective corpus tooling before gold annotations are produced.

The labels are conservative working labels:

- `fair_play`: the contradiction evidence is annotated as reader-available
  before the denouement.
- `withheld_decisive_evidence`: the decisive observation is not fully available
  to the reader before the explanatory reveal, so the story is useful as a
  control rather than as a fair-play item.

Each candidate includes public source metadata, sidecar path placeholders, one
or more false or misleading claims, and one or more decisive-evidence entries.
Use `validate_detective_story_annotation()` and `detective_corpus_summary()`
before adding a story to an experiment.

Generated sidecars live under `sidecars/`. Each sidecar directory contains an
`epistemap_graph.json` temporal graph and a `fair_play_diagnostic.json` report.
The top-level `sidecars/detective_corpus_sidecars.json` manifest summarizes the
generated sidecars and their fair-play diagnostic ratings.

Treatment manifests live under `treatments/`. The example pilot manifest
compares `plain-reading` and `graph-assisted` conditions and keeps diagnostics
and answer keys hidden from subjects.

The static review UI lives under `review_ui/`. Open
`review_ui/index.html` in a browser to review detective source anchors, import
or export anchor-review CSV files, and track rows as `needs_review`,
`reviewed`, or `blocked`.

The static collection UI lives under `collection_ui/`. Open
`collection_ui/index.html` in a browser to fill contradiction-recognition rows
from the reviewed pilot template, enter recognition outcomes and confidence,
auto-calculate recognition lag, validate rows locally, and export completed
CSV rows.

The blinded run UI lives under `run_ui/`. Open `run_ui/index.html` to import a
single prepared run-sheet CSV, collect recognition responses, and export a
completed subject sheet without showing reviewed quotes, fair-play ratings, or
sidecar diagnostic paths.

Prepared run sheets live under
`treatments/detective_fair_play_run_sheets/`. They are randomized,
condition-specific CSV sheets with `run_id` and `subject_id` filled in. They
are ready for experimental collection but still contain blank outcome fields.
Participant-safe sheets live under
`treatments/detective_fair_play_blinded_run_sheets/`; these omit fair-play
ratings, sidecar paths, claims, and other diagnostic columns, retaining only a
private `row_key` for rehydration with
`treatments/detective_fair_play_blinding_key.json`.
`treatments/detective_fair_play_g_rows_prepared.csv` is the merged version of
those prepared sheets, validated in template mode; it is not completed run
data.

The pilot runbook is
`treatments/detective_fair_play_pilot_protocol.md`. It specifies which UI to
use, which prepared sheets to import, what materials must remain hidden from
participants, and the post-run merge, manifest, and summary commands.

The initial anchor review is complete. The reviewed export is preserved at
`treatments/detective_anchor_review_completed.csv`, and candidate annotations
carry the reviewed locator, quote, anchor, reviewer, and review date under
`metadata.anchor_review`. These fixtures are still pilot materials, not final
literary scholarship.

The treatment directory also includes sample completed `G` rows, validation,
manifest, and summary artifacts for exercising the workflow. The sample rows
are deterministic fixtures, not human or model performance data; they contain
only target-environment rows, so full `G` estimates retain the expected
clean/reference-environment warning.
