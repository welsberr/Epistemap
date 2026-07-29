# Epistemap Performance Results

## Purpose

Record representative local measurements after the first optimization pass so
future work can compare against a checked-in baseline instead of synthetic
intuition.

These measurements describe the post-`v0.1.0a2` `main` branch. They are not a
new compatibility release; consumers pinned to `v0.1.0a2` do not receive these
optimizations until a later tagged release is published.

## Environment

- Host date: 2026-07-29
- Host: local Linux workstation (hardware details intentionally omitted)
- Python: `3.14.4`
- Command pattern: `PYTHONPATH=src python`

## Representative Graphs

These measurements use graph artifacts already present in nearby projects:

- Epistemap detective sidecars:
  `examples/detective_corpus/sidecars/*/epistemap_graph.json`
- Didactopus MIT OCW knowledge graph:
  `<DIDACTOPUS_ROOT>/domain-packs/mit-ocw-information-entropy/knowledge_graph.json`

The profiling artifact is saved at
`benchmarks/representative-local.json`.

The profiler also accepts sanitized `groundrecall_graph_bundle` exports and
projects their `nodes`/`edges` records into the Epistemap interchange shape.
This measures graph parsing and analysis cost only; it is not a GroundRecall
retrieval-quality or end-to-end latency benchmark.

## Shape Summary

| Graph | Nodes | Edges | Assessed nodes | Components | Largest component |
| --- | ---: | ---: | ---: | ---: | ---: |
| blue-carbuncle | 4 | 4 | 2 | 1 | 4 |
| purloined-letter-control | 4 | 4 | 2 | 1 | 4 |
| red-headed-league | 4 | 4 | 2 | 1 | 4 |
| speckled-band | 4 | 4 | 2 | 1 | 4 |
| didactopus-mit-ocw-information-entropy | 98 | 178 | 34 | 1 | 98 |

## Measured Timings

Representative medians from the optimized working tree:

| Graph | `diagnostics()` | `epistemic_report()` | `bayesian_assessment_report()` |
| --- | ---: | ---: | ---: |
| blue-carbuncle | 0.000061 s | 0.000481 s | 0.000500 s |
| purloined-letter-control | 0.000063 s | 0.000806 s | 0.000516 s |
| red-headed-league | 0.000055 s | 0.000479 s | 0.000489 s |
| speckled-band | 0.000057 s | 0.000484 s | 0.000461 s |
| didactopus-mit-ocw-information-entropy | 0.001549 s | 0.011184 s | 0.011270 s |

Synthetic independent source/claim pairs remain the clearest stress test for
batch epistemic reporting:

| Workload | Before | After |
| --- | ---: | ---: |
| `epistemic_report()` at 3,000 pairs | 25.5701 s | about 0.91 s |
| `bayesian_assessment_report()` at 3,000 pairs | not previously isolated | about 0.82 s |

## Interpretation

- The optimization pass removed the dominant asymptotic bottlenecks in both
  articulation-point detection and batch epistemic reporting.
- The representative real graphs currently in-tree are small enough that they
  serve mostly as behavior-preserving sanity checks rather than as hard stress
  tests.
- The Didactopus knowledge-graph profile required a light loader normalization
  step because its edge provenance is stored as path strings rather than full
  provenance objects.
- The next useful baseline should come from larger GroundRecall or Didactopus
  interchange bundles once they exist in checked-in, sanitizable form.

## Reproduction

Run:

```bash
export DIDACTOPUS_ROOT=/path/to/Didactopus
PYTHONPATH=src python benchmarks/profile_graph_bundles.py \
  examples/detective_corpus/sidecars/blue-carbuncle/epistemap_graph.json \
  examples/detective_corpus/sidecars/purloined-letter-control/epistemap_graph.json \
  examples/detective_corpus/sidecars/red-headed-league/epistemap_graph.json \
  examples/detective_corpus/sidecars/speckled-band/epistemap_graph.json \
  "$DIDACTOPUS_ROOT/domain-packs/mit-ocw-information-entropy/knowledge_graph.json" \
  --repeats 5 > benchmarks/representative-local.json
```
