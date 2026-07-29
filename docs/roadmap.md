# Epistemap Roadmap

The cross-repository confidence redesign is specified in
[confidence-overhaul-roadmap.md](confidence-overhaul-roadmap.md). Implement it
in dependency order from Epistemap to GroundRecall and Didactopus; do not infer
one confidence meaning from another repository's scalar field.

The evidence-backed phase audit is maintained in
[confidence-overhaul-implementation-status.md](confidence-overhaul-implementation-status.md).
The unified confidence overhaul is complete through W0-W13, including the
portable assessment models, evidence ledger, migration commands, installed
matrix, consumer compatibility releases, and deprecation-clock documentation.
Future work below is additive experimentation or separately scoped integration,
not unfinished overhaul acceptance work.

The portable assessment contract is available in alpha release
[`v0.1.0a2`](releases/v0.1.0a2.md). This release preserves legacy readers and
begins the documented compatibility/deprecation window; scalar-field removal
still requires a later release plan and downstream confirmation.

Coding models should execute the remaining work from
[confidence-overhaul-execution-roadmap.md](confidence-overhaul-execution-roadmap.md).
It converts the post-release gaps into dependency-ordered work packages with
explicit tests, migration rules, authority limits, and handoff requirements.

This roadmap organizes Epistemap work around the current shared use case:
GroundRecall supplies provenance-rich graph memory, CiteGeist supplies
provenance-rich bibliography and citation assertions, Didactopus consumes graph
and reliability context for learning workflows, and Epistemap supplies the
portable graph, temporal, Bayesian, and `G` assessment operations between them.

Epistemap remains below domain policy. It should expose auditable operations and
assessment artifacts, not decide claim truth or promotion status.

## Current implementation state (2026-07-29)

The first Python performance pass is implemented in `v0.1.0a3`; the current
compatibility patch release is `v0.1.0a4`.
Epistemap now has indexed graph views, shared-index diagnostics, linear-time
bridge analysis, and batch epistemic/Bayesian reporting that reuses indexes.
Checked-in representative measurements show `epistemic_report()` improving from
about 25.6 seconds to about 0.91 seconds for 3,000 independent source/claim
pairs. Epistemap has 162 passing tests.

Benchmark artifacts are sanitized and use portable path placeholders. GroundRecall
and Didactopus can update their immutable pins to `v0.1.0a4`.
The current Rust decision gate is explicitly deferred pending larger full-store
and end-to-end evidence.

## Current Capability

- Provenance-aware `GraphBundle`, `Node`, `Edge`, and `ProvenanceRef` models.
- Graph traversal, subgraph, connected-component, bridge, cycle, and QA
  diagnostics.
- Graph export to Graphviz DOT, Cytoscape JSON, and JSON-LD.
- Heuristic epistemic reports over support, challenge, grounding, revision, and
  source-trust signals.
- Bayesian reliability estimates over weighted support/challenge evidence.
- Named Bayesian prior profiles for neutral, skeptical, supportive,
  source-conservative, and adversarial-aware assessment.
- Bayesian Markdown reports.
- Assessment-readiness validation reports for checking graph auditability before
  treating assessment outputs as meaningful.
- Assessment manifests that record graph extraction, Bayesian prior, evidence
  weighting, temporal, reliability, and validation policies for reproducible
  experiments.
- Fair-play detective story annotations, validation, corpus summaries,
  annotation-to-temporal-graph conversion, temporal fair-play diagnostics, and
  contradiction-recognition `G` row generation.
- Detective-corpus treatment manifests, anchor-review templates, and pilot `G`
  collection templates.
- Temporal graph slices, tenability windows, contradiction timing, stale-claim
  detection, recognition windows, and fair-play diagnostics.
- Canonical `G` evaluation rows, manifests, summaries, comparisons,
  Markdown reports, and reliability-level sensitivity helpers.

## Near-Term Implementation

1. **Assessment labels**
   - Status: implemented.
   - Add `classify_bayesian_reliability()` labels:
     `stable_support`, `fragile_support`, `contested`, `thin_evidence`, and
     `prior_sensitive`.
   - Keep labels as review triage, not promotion authority.

2. **Named prior profiles**
   - Status: implemented.
   - Expose reusable prior profiles such as `neutral`, `skeptical`,
     `source_conservative`, and `adversarial_aware`.
   - Let callers request profile names without hand-building alpha/beta pairs.

3. **Graph-level Bayesian assessment**
   - Status: implemented.
   - Batch over claim or concept nodes.
   - Rank by thin evidence, wide intervals, prior sensitivity, and contested
     support.
   - Emit deterministic JSON and compact Markdown.

4. **Assessment validation**
   - Status: implemented.
   - Add SHACL-inspired readiness checks for graph integrity, evidential
     provenance, temporal availability metadata, confidence bounds, and
     Bayesian policy metadata.
   - Emit deterministic JSON and compact Markdown.

5. **Assessment manifests**
   - Status: implemented.
   - Extend experiment metadata to record Bayesian prior profile, graph
     extraction policy, evidence weighting policy, temporal policy, and
     reliability treatment.
   - Keep the existing `G` row format stable.

6. **CLI support**
   - Status: implemented.
   - Add graph-bundle input commands for Bayesian assessment reports.
   - `epistemap bayesian-assessment` loads a graph bundle, optionally filters
     node types, and emits deterministic JSON and compact Markdown.

7. **Interoperability concepts from adjacent packages**
   - RDFLib: optional RDF/JSON-LD/Turtle import/export with stable namespace
     handling.
   - pySHACL: formal shape validation for scholarly graph and assessment
     artifacts.
   - OWL-RL: conservative, provenance-marked rule entailment.
   - NetworkX: adapters for broader graph algorithms without making NetworkX a
     core representation.
   - graspologic: graph statistics and anomaly/embedding experiments for
     scholarly versus denialist corpora.
   - pgmpy/PyMC/ArviZ: optional probabilistic dependency models and richer
     Bayesian diagnostics.

8. **Model Context Protocol adapter**
   - Status: initial read-only adapter implemented.
   - `src/epistemap/mcp.py` exposes transport-neutral tool schemas and
     deterministic calls for validation, diagnostics, neighborhoods, epistemic
     reports, and Bayesian assessments without making Epistemap a policy or
     promotion authority.
   - Initial read-only tools should load or validate `GraphBundle` artifacts,
     run traversals and diagnostics, produce Bayesian/reliability reports,
     emit `G` summaries, and return machine-readable assessment manifests.
   - Mutation-capable MCP tools, if added later, should be limited to derived
     artifact generation; they must not decide GroundRecall promotion,
     CiteGeist bibliographic identity, or Didactopus learner mastery.
   - Every MCP response should preserve provenance references, assessment
     dimension, method, prior profile, effective sample size, warnings, and
     temporal scope rather than flattening results into a single confidence
     score.

   Acceptance criteria:

   - MCP schemas are versioned and covered by fixture tests;
   - read-only tools produce the same deterministic outputs as the CLI/library
     paths for representative graph bundles;
   - unknown producer-specific confidence dimensions are preserved or ignored
     according to the compatibility contract, not reinterpreted;
   - documentation states that MCP outputs are review affordances, not truth or
     promotion decisions.

   The adapter now includes a minimal stdio JSON-RPC host supporting
   `initialize`, `tools/list`, and `tools/call`. Remaining MCP work is host
   authentication, deployment integration, and optional policy-context
   plumbing by consuming repositories.

## Medium-Term Experiments

1. **Source-quality ablation**
   - Compare graph conditions where source-quality metadata is visible,
     flattened, or adversarial-aware.
   - Measure posterior stability and `G`.

2. **Denialist stress tests**
   - Compare genuine challenge evidence with manufactured-doubt signals.
   - Expect useful diagnostics to surface low effective sample size, prior
     sensitivity, or failure to improve `G`.

3. **Temporal tenability**
   - Track when claims move from reasonable ignorance to contradicted,
     superseded, stale, or untenable.
   - Compare temporal assessment with learner/model revision behavior.

4. **Fair-play detective corpus**
   - Status: candidate fixtures, temporal graph bridge, sidecar generation,
     treatment manifests, anchor-review templates, pilot `G` collection
     templates, blinded run UI, run sheets, merge tooling, and pilot protocol
     implemented; initial source-anchor review complete.
   - Use fair detective stories as controlled contradiction-recognition
     experiments.
   - Exclude or separately classify stories that withhold decisive evidence
     until the reveal.
   - Next: collect actual plain-reading versus graph-assisted participant or
     model-subject outcomes.

5. **Notebook and mentor interventions**
   - Compare plain source reading, graph-neighborhood reading, Bayesian
     reliability summaries, and mentor explanations that communicate
     uncertainty.

## Deferred

- Full Bayesian networks over dependent claims.
- MCMC or heavyweight probabilistic-programming dependencies.
- Automatic claim promotion based only on Bayesian posterior or `G`.
- Any single-score tribunal for scientific revolutions.

## Integration Notes

GroundRecall should use Epistemap labels and reports as review affordances for
query bundles, review bundles, and public exports. Didactopus should treat the
same artifacts as learner/mentor context and experiment covariates. In both
cases, provenance, source reliability, temporal tenability, Bayesian posterior,
and `G` remain separate surfaces.

CiteGeist should use Epistemap for a rebuildable bibliography graph projection,
structural diagnostics, temporal views, and typed assessments. CiteGeist remains
the bibliography authority. Ordinary citation edges must not be interpreted as
claim support, and citation topology must not be treated as truth or source
quality. The implementation sequence is defined in CiteGeist's
`docs/epistemap-knowledge-graph-roadmap.md`.

MCP integrations should follow the same boundary. Epistemap may provide
assistant-callable graph diagnostics and assessment reports, but repository
owners decide how those reports affect review state. GroundRecall, CiteGeist,
and Didactopus MCP adapters should call Epistemap operations as derived,
auditable analyses rather than delegating authority to Epistemap.
