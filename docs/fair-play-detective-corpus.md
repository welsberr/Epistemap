# Fair-Play Detective Corpus

Epistemap includes a small annotation schema for contradiction-recognition
experiments using fair-play detective fiction. The goal is to create a
controlled corpus where false claims appear before later narrative evidence
contradicts them, and where the contradiction is available to the reader before
the denouement.

The annotation helper is `detective_story_annotation()`. Each story annotation
records:

- story id, title, author, source, license, and public-domain status;
- narrative unit, such as chapter, scene, page, or timestep;
- reveal point;
- fair-play status;
- claim annotations, including false or misleading claims;
- decisive evidence annotations, including the point where contradiction becomes
  available;
- graph, assessment manifest, and validation sidecar references.

Use `validate_detective_story_annotation()` before admitting a story to an
experiment. Validation checks for missing claims, missing false-claim
annotations, missing decisive evidence, evidence that points at unknown claims,
evidence available after reveal, and evidence hidden from the reader.

Use `detective_recognition_g_row()` to convert a model or learner recognition
result into a canonical `G` evaluation row. The row records the story id, claim
id, contradiction availability point, recognition point, recognition lag, and
fair-play rating.

Use `detective_corpus_summary()` to summarize a candidate corpus before running
experiments. The summary counts validation status, fair-play status, claims, and
decisive evidence annotations.

Use `detective_annotation_graph_bundle()` to convert an annotation into a
temporal `GraphBundle`. Claims become claim nodes, decisive evidence becomes
evidence nodes, and decisive evidence entries become `contradicts` edges with
availability metadata.

Use `detective_annotation_fair_play_diagnostic()` to run the temporal
fair-play diagnostic over false, misleading, or contradicted claims from an
annotation. This connects the detective schema to the same graph timing checks
used for scholarly temporal tenability.

Use `write_detective_corpus_sidecars()` or the `epistemap detective-sidecars`
CLI command to generate stable per-story sidecars:

- `epistemap_graph.json`
- `fair_play_diagnostic.json`
- `detective_corpus_sidecars.json`

Use `detective_treatment_manifest()` or the `epistemap detective-treatment`
CLI command to declare planned experimental conditions before rows are
collected. The default treatment manifest compares `plain-reading` and
`graph-assisted` conditions while keeping fair-play diagnostics and answer keys
hidden from subjects.

Use `detective_g_collection_template()` or the
`epistemap detective-g-template` CLI command to create a blank collection CSV
from a treatment manifest and corpus sidecar manifest. The template expands
story claims across planned conditions and phases, includes contradiction
availability timing, reviewed source anchors, and sidecar references, and
leaves `y`, `p`, response, and recognition fields blank for collection.
Use `epistemap detective-validate-g-rows` before summarizing completed rows;
`--allow-template` checks template structure without requiring completion
fields, while `--require-pass` makes incomplete or invalid completed exports
fail with exit status 2.
Use `epistemap detective-g-manifest` to derive an `epistemap_g_experiment`
manifest from completed rows before running `epistemap g-summary`.
Use `epistemap detective-run-sheets` to turn a reviewed collection template
into deterministic per-subject CSV sheets. This fills `run_id` and
`subject_id`, optionally filters conditions or phases, randomizes row order by
seed, and leaves outcome fields blank; it prepares experimental runs but does
not create results.
The static blinded run UI at `examples/detective_corpus/run_ui/index.html`
can import one prepared sheet and export a completed subject sheet without
showing reviewed quotes, fair-play labels, or diagnostic sidecar paths.
For stricter blinding, use `epistemap detective-blind-run-sheets` to remove
diagnostic columns from participant CSVs and keep a private rehydration key;
after completion, use `epistemap detective-unblind-run-sheets` to restore
canonical row metadata before summarization.
After real outcomes have been entered into blinded sheets, use
`epistemap detective-unblind-run-sheets` to restore canonical rows and validate
them before manifest generation. If an operator collected directly on canonical
sheets, `epistemap detective-merge-run-sheets` can consolidate those sheets.

Use `detective_anchor_review_template()` or the
`epistemap detective-anchor-template` CLI command to create a blank human-review
CSV for exact source anchors. The template lists each annotated claim and
decisive evidence item with its provisional narrative anchor, source URL, text,
and blank fields for reviewed locator, quote, reviewed anchor, reviewer, date,
and status.

The initial pilot has four public-domain stories with completed source-anchor
review metadata. Exclude or separately classify stories where the decisive
evidence is introduced only at the reveal or is available only to the detective.

Candidate fixtures live under `examples/detective_corpus/candidates/`. These
fixtures are provisional annotations for pipeline validation and experiment
design; they are not gold labels. Each candidate includes source metadata,
sidecar path placeholders, false or misleading claims, and decisive evidence
entries. Treat warning-bearing controls, such as withheld-evidence stories, as
negative or contrast cases rather than fair-play items.

The example pilot treatment manifest lives at
`examples/detective_corpus/treatments/detective_fair_play_pilot.json`. A blank
row collection template and anchor-review template can be regenerated with:

```bash
epistemap detective-g-template --treatment examples/detective_corpus/treatments/detective_fair_play_pilot.json --out examples/detective_corpus/treatments/detective_fair_play_g_collection_template.csv
epistemap detective-validate-g-rows examples/detective_corpus/treatments/detective_fair_play_g_collection_template.csv --allow-template
epistemap detective-run-sheets examples/detective_corpus/treatments/detective_fair_play_g_collection_template.csv --out-dir examples/detective_corpus/treatments/detective_fair_play_run_sheets --run-id-prefix detective-fair-play-pilot-001 --subject-prefix pilot-reader --subjects-per-condition 1 --seed 20260705
epistemap detective-blind-run-sheets examples/detective_corpus/treatments/detective_fair_play_run_sheets --out-dir examples/detective_corpus/treatments/detective_fair_play_blinded_run_sheets --key-file examples/detective_corpus/treatments/detective_fair_play_blinding_key.json
epistemap detective-unblind-run-sheets examples/detective_corpus/treatments/detective_fair_play_blinded_run_sheets --key-file examples/detective_corpus/treatments/detective_fair_play_blinding_key.json --out examples/detective_corpus/treatments/detective_fair_play_g_rows_unblinded_prepared.csv --allow-template --require-pass
epistemap detective-merge-run-sheets examples/detective_corpus/treatments/detective_fair_play_run_sheets --out examples/detective_corpus/treatments/detective_fair_play_g_rows_prepared.csv --allow-template --require-pass
epistemap detective-g-manifest examples/detective_corpus/treatments/detective_fair_play_g_rows_sample.csv --experiment-id detective-fair-play-pilot-sample-001 --out examples/detective_corpus/treatments/detective_fair_play_g_manifest_sample.json
epistemap detective-anchor-template examples/detective_corpus/candidates/*.json --out examples/detective_corpus/treatments/detective_anchor_review_template.csv
```

The completed anchor-review export is preserved at
`examples/detective_corpus/treatments/detective_anchor_review_completed.csv`.
Apply a completed review CSV back to annotation JSON with:

```bash
epistemap detective-apply-anchor-review examples/detective_corpus/candidates/*.json --review-csv examples/detective_corpus/treatments/detective_anchor_review_completed.csv --in-place
```
