# Epistemap Roadmap

The cross-repository confidence redesign is specified in
[confidence-overhaul-roadmap.md](confidence-overhaul-roadmap.md). Implement it
in dependency order from Epistemap to GroundRecall and Didactopus; do not infer
one confidence meaning from another repository's scalar field.

The evidence-backed phase audit is maintained in
[confidence-overhaul-implementation-status.md](confidence-overhaul-implementation-status.md).
The overhaul is in progress, not complete: portable assessment models are
merged, while evidence-ledger, migration-command, installed-package,
consumer-release, and deprecation work remains.

The portable assessment contract is available in alpha release
[`v0.1.0a1`](releases/v0.1.0a1.md). This release preserves legacy readers and
does not begin scalar-field removal.

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
