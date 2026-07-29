# Epistemap Performance Implementation Roadmap

## Purpose

Improve Epistemap's performance on graphs containing thousands to tens of
thousands of nodes while preserving its Python API, deterministic output, and
domain-policy neutrality.

The first optimization pass is implemented on `main` after `v0.1.0a2` and is
covered by the checked-in benchmarks. Phases 0-4 and the shared-index portion
of Phase 5 are complete in the current tree. Remaining work is representative
integration profiling, regression monitoring, and the Rust decision gate. A
compatibility release/tag remains a separate release-management step;
performance results must not be presented as part of `v0.1.0a2`.

This roadmap is written for a coding model. Implement it as a sequence of small,
reviewable changes. Do not introduce Rust during these phases. The decision
about a Rust core comes only after the optimized Python implementation has been
measured on representative workloads.

## Measured Baseline

Measurements were taken on synthetic sparse graphs with the current Python
implementation:

| Workload | 1,000 nodes | 3,000 nodes |
| --- | ---: | ---: |
| Connected components | 0.0016 s | 0.0078 s |
| Shortest path | 0.0052 s | 0.0420 s |
| Bridge-node detection | 0.4545 s | 4.0259 s |
| Full diagnostics | 0.4418 s | 4.1574 s |

For independent source-to-claim pairs:

| Assessed nodes | Total nodes | Edges | `epistemic_report()` |
| ---: | ---: | ---: | ---: |
| 100 | 200 | 100 | 0.0572 s |
| 300 | 600 | 300 | 0.2449 s |
| 1,000 | 2,000 | 1,000 | 2.1530 s |
| 3,000 | 6,000 | 3,000 | 25.5701 s |

The principal causes are algorithmic:

- `bridge_nodes()` removes and re-walks every candidate node.
- `epistemic_report()` calls a summary operation that repeatedly indexes nodes
  and scans the entire edge collection.
- Several helpers independently reconstruct the same adjacency structures.
- `validate_shape()` calls `bundle.node_index()` twice per valid edge.

The first implementation target is therefore better asymptotic behavior and
index reuse, not lower-level execution.

## Compatibility Contract

All optimization work must preserve:

- Public function names, parameters, defaults, and return shapes.
- Existing Pydantic graph models and accepted serialized graph format.
- Deterministic ordering of returned nodes, edges, findings, and reports.
- Existing behavior for missing endpoints, self-loops, parallel edges,
  disconnected graphs, filtered node types, and filtered edge types.
- The distinction between graph analysis, epistemic assessment, and domain
  policy.
- Support for Python 3.10 and later.

Do not cache indexes directly on `GraphBundle` during this work. Its `nodes` and
`edges` lists are mutable, so a persistent cache would require an invalidation
contract that does not currently exist.

## Performance Targets

Use targets as regression gates, not as promises across every machine. Record
the baseline and optimized results on the same host and Python environment.

Minimum targets:

- `bridge_nodes()` on a 3,000-node path: under 0.10 seconds.
- `diagnostics()` on a 3,000-node path: under 0.15 seconds.
- `bridge_nodes()` and `diagnostics()` should exhibit approximately linear
  growth between 1,000 and 10,000 sparse nodes.
- `epistemic_report()` on 3,000 independent claim/source pairs: under
  1.5 seconds.
- No existing test failures and no public-output changes except where an
  existing nondeterminism is explicitly corrected and covered by a test.

Stretch targets:

- Full diagnostics on a 10,000-node sparse graph: under 0.5 seconds.
- Epistemic reporting on 10,000 independent claim/source pairs: under
  5 seconds.
- Peak resident memory no more than 3 times the serialized graph size for the
  benchmark workload.

## Phase 0: Establish Reproducible Benchmarks

### Objective

Create a stable measurement harness before changing implementation code.

### Changes

Add `benchmarks/benchmark_graph_operations.py`. Use only the standard library
and Epistemap itself; do not add `pytest-benchmark` yet.

The script must:

1. Generate deterministic graph families:
   - path;
   - star;
   - cycle;
   - disconnected components;
   - independent source-to-claim pairs;
   - sparse seeded pseudo-random graph.
2. Accept graph size and repeat count from command-line arguments.
3. Measure:
   - model construction separately;
   - connected components;
   - shortest path;
   - bridge nodes;
   - diagnostics;
   - assessment readiness;
   - epistemic report;
   - Bayesian assessment report.
4. Use `time.perf_counter()`, run one unmeasured warmup, and report the minimum
   and median of at least three measured repetitions.
5. Emit deterministic JSON containing environment information, workload
   parameters, and timings.
6. Keep generated graphs in memory and outside the timed region unless the
   measurement is explicitly for construction or parsing.

Add a short "Performance benchmarks" section to `README.md` showing the command
to run the harness. Do not place absolute timing assertions in the ordinary
unit-test suite.

### Verification

- Run the benchmark twice at sizes 100, 1,000, and 3,000.
- Confirm result keys and workload counts are identical.
- Save the pre-optimization result as
  `benchmarks/baselines/python-before-indexing.json`.
- Run the complete test suite.

### Completion gate

Do not start algorithm changes until the baseline artifact is committed and
can be reproduced with one documented command.

## Phase 1: Add an Internal Indexed Graph View

### Objective

Build node and adjacency indexes once per high-level operation and pass them
through internal helpers.

### Design

Create `src/epistemap/index.py` containing an internal or provisionally public
`GraphIndex` type. Prefer a frozen dataclass with these fields:

- `nodes_by_id: dict[str, Node]`
- `node_ids: set[str]`
- `incoming_by_node: dict[str, tuple[Edge, ...]]`
- `outgoing_by_node: dict[str, tuple[Edge, ...]]`
- `incident_by_node: dict[str, tuple[Edge, ...]]`
- `undirected_neighbors: dict[str, frozenset[str]]`
- optionally, `edges_by_type: dict[str, tuple[Edge, ...]]`

Construct it in one pass over nodes and one pass over edges. Index only valid
endpoints in adjacency maps, but retain enough information for validation to
report invalid endpoints. Preserve input edge order within each tuple.

Make the type immutable from the caller's perspective. It may reference the
existing immutable-for-the-operation `Node` and `Edge` objects.

### Integration sequence

1. Add isolated unit tests for index construction.
2. Allow private adjacency helpers in `algorithms.py` to accept an existing
   index.
3. Refactor `incoming_edges()`, `outgoing_edges()`, and `neighborhood()` to use
   an index internally without changing their signatures.
4. Add private overload-style helpers, such as
   `_incoming_edges(index, node_id, edge_types)`, for callers that already own
   an index.
5. Refactor each high-level algorithm to create no more than one index.

Do not expose a `GraphBundle` cache and do not make callers manage cache
invalidation.

### Required tests

Cover:

- empty graph;
- isolated nodes;
- self-loop;
- duplicate parallel edges;
- edge with missing source;
- edge with missing target;
- directed and undirected adjacency;
- preservation of edge order;
- filtered edge types;
- duplicate node IDs, retaining existing `node_index()` semantics.

### Completion gate

- All tests pass.
- Existing algorithm return values match snapshots or direct comparisons
  against the pre-refactor implementation.
- Traversal benchmarks do not regress by more than 20% on small graphs.

## Phase 2: Replace Quadratic Bridge-Node Detection

### Objective

Replace repeated node removal with linear-time articulation-point detection.

Although the public function is named `bridge_nodes()`, its current semantics
identify articulation vertices, not bridge edges. Preserve the public name and
return format. Document the terminology internally; do not make an unrelated
API rename in this phase.

### Algorithm

Implement Tarjan articulation-point detection over the undirected graph:

- complexity: `O(V + E)`;
- process every connected component;
- track discovery order, low-link values, parent, and root child count;
- ignore edges whose endpoints are not in the selected node set;
- treat parallel edges and self-loops carefully;
- prefer an iterative depth-first search so graphs larger than Python's
  recursion limit remain supported.

The current result includes:

- `node_id`;
- `component_size`;
- `reachable_after_removal`.

Tarjan directly identifies articulation points but not the current
`reachable_after_removal` value. Preserve that value exactly. Compute component
partition sizes from DFS subtree sizes and low-link boundaries rather than
re-walking the graph for every articulation point.

For an articulation point, `reachable_after_removal` must continue to represent
the number reached from the particular start chosen by the old implementation.
Because the old start comes from set iteration and is nondeterministic, first
write characterization tests. Then choose and document a deterministic
definition:

- use the lexicographically smallest remaining node as the conceptual start;
- report the size of that start node's post-removal component.

If this changes existing output, call it out in release notes as a
nondeterminism fix.

### Required tests

Add cases for:

- path: all internal nodes are articulation points;
- cycle: no articulation points;
- star: center only;
- complete graph: none;
- disconnected mixture of paths and cycles;
- two-node and one-node components;
- self-loops;
- parallel edges;
- node-type filtering;
- invalid endpoints;
- path with at least 5,000 nodes to prove there is no recursion failure.

Add a property-style reference test without a new dependency: for many small
seeded random graphs, compare the Tarjan result with a simple brute-force
remove-and-walk implementation kept in the test module.

### Completion gate

- Exact articulation-node equivalence with the brute-force reference.
- Deterministic payload ordering and values.
- 3,000-node path target met.
- Approximately linear scaling through 10,000 sparse nodes.

## Phase 3: Make Diagnostics a Shared-Index Pipeline

### Objective

Ensure `diagnostics()` builds graph structures once and shares them among
component, articulation, degree, and edge-count calculations.

### Changes

- Add private index-aware versions of connected components and articulation
  analysis.
- Have `diagnostics()` construct one `GraphIndex`.
- Compute connected components once.
- Pass those components into articulation analysis.
- Reuse adjacency for degree ranking.
- Count valid selected edges during index construction or in one pass.
- Preserve the existing result schema and sorting.

Avoid calling public convenience functions from `diagnostics()` when doing so
would rebuild indexes.

### Verification

- Compare complete diagnostics dictionaries before and after the refactor on
  all algorithm fixtures.
- Run deterministic randomized comparisons for small graphs.
- Meet the 3,000- and 10,000-node diagnostics targets.

## Phase 4: Batch Epistemic Assessment

### Objective

Eliminate the repeated whole-graph scans performed once per assessed node.

### Design

Split public report construction from internal indexed computation:

1. `epistemic_summary(bundle, node_id)` remains a compatible convenience API.
2. It builds a `GraphIndex` once and delegates to a private
   `_epistemic_summary(index, bundle_metadata, node_id, ...)`.
3. `epistemic_report()` and `bayesian_assessment_report()` build one index and
   call the private helper for every selected node.

Before implementation, characterize `_claim_ids_for_target()` and all helper
functions in `epistemic.py`. Identify which signals require:

- direct incident edges;
- claim-to-concept links;
- evidence edges incident to related claims;
- referenced nodes;
- source-quality, stance, trust, grounding, and provenance metadata.

Use index lookups to construct exactly the same relevant-node and relevant-edge
sets. Avoid scanning `bundle.edges` or rebuilding `bundle.node_index()` inside
the per-node loop.

Preserve current ordering:

- summary rows follow the established order before report-level sorting;
- edge excerpts retain bundle edge order;
- counts and flags remain unchanged;
- Bayesian floating-point results remain equal within the existing precision.

### Optional second optimization

If profiling shows repeated Bayesian prior-sensitivity calculation dominates
after indexing, cache only immutable resolved prior profiles and pure
distribution constants. Do not memoize results by mutable model identity.

### Required tests

- Directly compare old/reference and optimized summaries on existing fixtures.
- Cover concepts with multiple claims.
- Cover evidence linked on either side of a claim.
- Cover shared evidence supporting multiple claims.
- Cover challenges, revisions, low-confidence nodes, source roles, source
  quality, adversarial stance, and grounding status.
- Cover missing target node IDs.
- Confirm excerpt limits and ordering.
- Confirm `epistemic_report()` and `bayesian_assessment_report()` output equality.

Keep a test-only reference implementation long enough to compare many seeded
small graphs. Remove it only if it becomes costly to maintain after the
optimization stabilizes.

### Completion gate

- 3,000-pair report target met.
- Scaling is approximately linear for independent claim/source pairs.
- All epistemic and Bayesian output-equivalence tests pass.

## Phase 5: Remove Remaining Accidental Re-indexing

### Objective

Address smaller hotspots after the primary gains have landed.

### Audit targets

- In `validation.py`, construct `nodes = bundle.node_index()` once in
  `validate_shape()` rather than twice per edge.
- In `temporal.py`, reuse a node map within high-level operations instead of
  repeatedly calling `bundle.node_index()`.
- In exporters, avoid repeated model serialization where a payload has already
  been computed.
- In graph QA, combine compatible edge scans only where clarity is retained.

Use a profiler before and after each change. Do not combine loops merely to
reduce their count if doing so makes validation logic hard to audit.

### Completion gate

- No `bundle.node_index()` call remains inside an edge or node loop.
- No high-level batch operation calls a public convenience function that
  reconstructs the same index for every item.
- Tests and benchmark targets continue to pass.

## Phase 6: Profile Representative Integration Workloads

### Objective

Measure real use rather than extrapolating solely from synthetic graphs.

### Inputs

Obtain sanitized, secret-free graph bundles representative of:

- GroundRecall query and export graphs;
- GroundRecall full-store diagnostics;
- Didactopus course or pack graphs;
- detective-corpus temporal graphs;
- a projected 10× growth case for the largest current graph.

Do not commit private graph contents. Commit only:

- graph shape statistics;
- a reproducible synthetic generator matching those distributions;
- sanitized timing results.

### Measurements

Record:

- graph parsing time;
- model construction time;
- each major graph operation;
- report serialization time;
- peak resident memory;
- total command latency;
- node and edge counts;
- degree distribution summary;
- number and size of connected components;
- assessed-node count.

Use `cProfile` or `py-spy` if available. Keep generated profiles out of version
control unless reduced to a small text report.

### Completion gate

Create `docs/performance-results.md` containing:

- hardware and Python version;
- benchmark commands;
- before/after tables;
- remaining top hotspots;
- whether current targets are met;
- a recommendation on whether to stop optimizing Python.

## Phase 7: Rust Decision Gate

Do not begin Rust implementation merely because a kernel could be faster.
Recommend a Rust prototype only if at least one of these is true after Phase 6:

- A documented production latency or throughput target is still missed by at
  least 2×.
- CPU-bound Epistemap code accounts for at least 40% of end-to-end runtime.
- Peak Python object memory prevents required graph sizes.
- A stable graph-analysis core is needed by non-Python consumers.
- Parallel CPU execution is required and process-based parallelism is
  operationally unsuitable.

Do not recommend Rust when:

- JSON/filesystem/database/model latency dominates;
- graph workloads remain below roughly 1,000 nodes and complete comfortably;
- the core API or semantics are still changing rapidly;
- optimized Python already satisfies the target with adequate headroom.

### Rust prototype scope

If the gate is met, prototype one narrow kernel using PyO3 and maturin:

1. articulation-point and component analysis, or
2. graph index construction plus batched traversal.

The prototype must:

- accept primitive Python data or a compact serialized representation rather
  than depending on Pydantic internals;
- return the existing Python-compatible payload;
- keep a pure-Python fallback;
- ship wheels for supported platforms before becoming a required dependency;
- demonstrate at least a 3× end-to-end improvement in the target workload,
  including conversion overhead;
- introduce no output differences.

Do not port validation policy, report formatting, CLI behavior, or rapidly
changing epistemic-domain logic in the first Rust experiment.

## Patch Sequence for a Coding Model

Implement one logical change per patch:

1. Benchmark harness and baseline artifact.
2. `GraphIndex` with isolated tests.
3. Traversal helpers migrated to the index.
4. Tarjan articulation points with brute-force equivalence tests.
5. Shared-index diagnostics.
6. Indexed single-node epistemic summary.
7. Batched epistemic and Bayesian reports.
8. Validation and temporal re-indexing cleanup.
9. Integration benchmarks and results document.
10. Rust decision record.

For every patch:

1. Inspect the relevant public tests before editing.
2. Add characterization tests for behavior that is not obviously specified.
3. Make the smallest compatible implementation change.
4. Run targeted tests.
5. Run the complete suite.
6. Run the affected benchmark at a small and representative large size.
7. Report correctness results and before/after timings.

Do not mix formatting, renaming, public API redesign, or unrelated roadmap
features into performance patches.

## Definition of Done

The Python optimization project is complete when:

- all existing and new tests pass;
- public output is compatible and deterministic;
- bridge-node and diagnostics operations scale linearly on sparse graphs;
- batch epistemic assessment no longer performs whole-graph work per node;
- stated minimum performance targets are met or misses are documented;
- representative integration workloads have before/after evidence;
- the repository contains a written Rust decision based on profiles and
  end-to-end measurements rather than microbenchmark speculation.
