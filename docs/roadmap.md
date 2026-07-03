# Epistemap Roadmap

This roadmap organizes Epistemap work around the current shared use case:
GroundRecall supplies provenance-rich graph memory, Didactopus consumes graph
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
- Bayesian Markdown reports.
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
   - Expose reusable prior profiles such as `neutral`, `skeptical`,
     `source_conservative`, and `adversarial_aware`.
   - Let callers request profile names without hand-building alpha/beta pairs.

3. **Graph-level Bayesian assessment**
   - Batch over claim or concept nodes.
   - Rank by thin evidence, wide intervals, prior sensitivity, and contested
     support.
   - Emit deterministic JSON and compact Markdown.

4. **Assessment manifests**
   - Extend experiment metadata to record Bayesian prior profile, graph
     extraction policy, evidence weighting policy, temporal policy, and
     reliability treatment.
   - Keep the existing `G` row format stable.

5. **CLI support**
   - Add graph-bundle input commands for Bayesian assessment reports once
     downstream graph export paths are stable enough for ordinary use.

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
   - Use fair detective stories as controlled contradiction-recognition
     experiments.
   - Exclude or separately classify stories that withhold decisive evidence
     until the reveal.

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
