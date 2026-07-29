# Epistemap

Epistemap is a small shared library for provenance-aware knowledge graph
bundles. It provides a neutral node/edge schema, ID helpers, traversal
utilities, graph diagnostics, and adapters that projects can use without
coupling their internal domain models to each other.

Initial users are expected to include GroundRecall and Didactopus:

- GroundRecall can project reviewed concepts, claims, relations, and provenance
  into an Epistemap bundle.
- Didactopus can emit course/pack graphs and consume GroundRecall context
  through the same graph utilities.

The library intentionally stays below domain policy. It does not decide what a
review status means, how a learner should be scored, or how claims should be
promoted. It gives those systems a common graph representation and reusable
operations.

Epistemap also includes experimental helpers for analyzing practical `G`
grounding-effectiveness outcomes from claim-level learner/model evaluations.
These are intended for counterfactual graph-intervention and reliability
sensitivity analysis, not as truth scores. See
`docs/scientific-change-and-g.md` for the scientific-change framing and the
distinction between evidence, source reliability, and `G`.

Temporal epistemic graph operations are documented in
`docs/temporal-epistemic-graphs.md`. These support graph slices, tenability
windows, contradiction timing, and stale-claim detection for both scholarly
timelines and fair-play detective-story experiments.

Bayesian reliability estimates are documented in
`docs/bayesian-reliability.md`. These add explicit posterior support estimates
and prior-sensitivity checks alongside the existing heuristic epistemic
reliability summaries.

Assessment-readiness validation checks whether graph assessment artifacts are
auditable before their outputs are treated as meaningful. The validator reports
graph integrity, evidential provenance, temporal metadata, confidence bounds,
and Bayesian policy metadata findings as deterministic JSON or Markdown.
Assessment manifests record the policies and artifact paths needed to reproduce
graph assessment conditions across GroundRecall, Didactopus, and experiment
runners.

Fair-play detective-corpus annotation helpers are documented in
`docs/fair-play-detective-corpus.md`. These support controlled
contradiction-recognition experiments using public-domain detective stories.

The current implementation sequence is tracked in `docs/roadmap.md`.

The `epistemap` CLI can summarize and compare G artifacts:

```bash
epistemap g-summary g_rows.csv --manifest g_manifest.json --out g_summary.json --out-md g_summary.md
epistemap g-summary g_rows.csv --manifest g_manifest.json --require-consistent
epistemap g-compare run-a/g_summary.json run-b/g_summary.json --baseline-id run-a --out comparison.json --out-md comparison.md
epistemap g-compare run-a/g_summary.json run-b/g_summary.json --require-compatible
```

It can also run graph-level Bayesian assessment reports from an Epistemap graph
bundle:

```bash
epistemap bayesian-assessment epistemap_graph.json --out bayesian_assessment.json --out-md bayesian_assessment.md
epistemap bayesian-assessment epistemap_graph.json --node-type claim --node-type concept
```

For detective-corpus pilots, the CLI can generate blank contradiction
recognition collection templates from a treatment manifest:

```bash
epistemap detective-g-template --treatment examples/detective_corpus/treatments/detective_fair_play_pilot.json --out g_collection_template.csv
epistemap detective-run-sheets g_collection_template.csv --out-dir run_sheets --run-id-prefix detective-pilot --subjects-per-condition 1 --seed 20260705
epistemap detective-blind-run-sheets run_sheets --out-dir blinded_run_sheets --key-file blinding_key.json
epistemap detective-unblind-run-sheets completed_blinded_run_sheets --key-file blinding_key.json --out g_collection_rows.csv --require-pass
epistemap detective-validate-g-rows g_collection_rows.csv --require-pass
epistemap detective-g-manifest g_collection_rows.csv --experiment-id detective-pilot --out g_manifest.json
epistemap detective-anchor-template examples/detective_corpus/candidates/*.json --out detective_anchor_review_template.csv
epistemap detective-apply-anchor-review examples/detective_corpus/candidates/*.json --review-csv detective_anchor_review_completed.csv --in-place
```

The human anchor-review UI is a static page at
`examples/detective_corpus/review_ui/index.html`.
The detective G collection UI is a static page at
`examples/detective_corpus/collection_ui/index.html`.
The blinded detective run UI is a static page at
`examples/detective_corpus/run_ui/index.html`.

Performance benchmarks can be run with:

```bash
PYTHONPATH=src python3 benchmarks/benchmark_graph_operations.py --sizes 100 1000 3000 --repeats 5 > benchmarks/latest-local.json
```
