# Detective Fair-Play Pilot Protocol

This protocol is for running the prepared contradiction-recognition pilot. It
uses public-domain detective-story annotations, completed source-anchor review,
and blinded per-subject run sheets.

## Current Status

- Source-anchor review is complete.
- Candidate annotations and sidecars have been regenerated from the reviewed
  anchors.
- Collection templates, canonical per-condition run sheets, participant-safe
  blinded sheets, and a private blinding key are prepared.
- No real participant or model-run outcomes have been collected yet.

## Operator Setup

1. Open the blinded run UI:

   `examples/detective_corpus/run_ui/index.html`

2. For each participant or model-subject run, import one blinded CSV from:

   `examples/detective_corpus/treatments/detective_fair_play_blinded_run_sheets/`

3. Use one sheet per subject. Do not show the operator collection UI, source
   anchor review UI, fair-play diagnostics, sidecar JSON, answer keys, or
   reviewed quote metadata to participants.

4. Export the completed sheet from the run UI after all rows have `y` and `p`
   filled.

## Prepared Sheets

The current participant-safe packet contains:

- `detective-fair-play-pilot-001-plain-reading-01.blinded.csv`
- `detective-fair-play-pilot-001-graph-assisted-01.blinded.csv`

These sheets are randomized with seed `20260705`. They contain blank outcome
fields and are not result data. The private rehydration key is:

`examples/detective_corpus/treatments/detective_fair_play_blinding_key.json`

The key is ignored by git and should not be shared with participants. Completed
run exports are also local/private artifacts until they have been reviewed and
approved for publication.

To regenerate the canonical packet and the blinded participant packet:

```bash
epistemap detective-run-sheets examples/detective_corpus/treatments/detective_fair_play_g_collection_template.csv \
  --out-dir examples/detective_corpus/treatments/detective_fair_play_run_sheets \
  --run-id-prefix detective-fair-play-pilot-001 \
  --subject-prefix pilot-reader \
  --subjects-per-condition 1 \
  --seed 20260705

epistemap detective-blind-run-sheets examples/detective_corpus/treatments/detective_fair_play_run_sheets \
  --out-dir examples/detective_corpus/treatments/detective_fair_play_blinded_run_sheets \
  --key-file examples/detective_corpus/treatments/detective_fair_play_blinding_key.json
```

## Post-Run Merge

After completed blinded sheets are exported, place them in a separate
collection directory. Then rehydrate, merge, and validate:

```bash
epistemap detective-unblind-run-sheets completed_blinded_run_sheets \
  --key-file examples/detective_corpus/treatments/detective_fair_play_blinding_key.json \
  --out examples/detective_corpus/treatments/detective_fair_play_g_rows_completed.csv \
  --require-pass
```

Then create the manifest and summary:

```bash
epistemap detective-g-manifest examples/detective_corpus/treatments/detective_fair_play_g_rows_completed.csv \
  --experiment-id detective-fair-play-pilot-001 \
  --out examples/detective_corpus/treatments/detective_fair_play_g_manifest_completed.json \
  --name "Detective fair-play pilot" \
  --corpus examples/detective_corpus

epistemap g-summary examples/detective_corpus/treatments/detective_fair_play_g_rows_completed.csv \
  --manifest examples/detective_corpus/treatments/detective_fair_play_g_manifest_completed.json \
  --out examples/detective_corpus/treatments/detective_fair_play_g_summary_completed.json \
  --out-md examples/detective_corpus/treatments/detective_fair_play_g_summary_completed.md
```

## Prepared-Only Check

Before real outcomes exist, the blinded prepared sheets can be rehydrated only
in template mode:

```bash
epistemap detective-unblind-run-sheets examples/detective_corpus/treatments/detective_fair_play_blinded_run_sheets \
  --key-file examples/detective_corpus/treatments/detective_fair_play_blinding_key.json \
  --out examples/detective_corpus/treatments/detective_fair_play_g_rows_unblinded_prepared.csv \
  --allow-template \
  --require-pass
```

The prepared unblinded CSV is a workflow check, not experimental evidence.
