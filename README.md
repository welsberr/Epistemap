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

The current implementation sequence is tracked in `docs/roadmap.md`.

The `epistemap` CLI can summarize and compare G artifacts:

```bash
epistemap g-summary g_rows.csv --manifest g_manifest.json --out g_summary.json --out-md g_summary.md
epistemap g-summary g_rows.csv --manifest g_manifest.json --require-consistent
epistemap g-compare run-a/g_summary.json run-b/g_summary.json --baseline-id run-a --out comparison.json --out-md comparison.md
epistemap g-compare run-a/g_summary.json run-b/g_summary.json --require-compatible
```
