# Cross-Repository Confidence Overhaul Roadmap

**Status:** in progress; audited implementation status is recorded in
[`confidence-overhaul-implementation-status.md`](confidence-overhaul-implementation-status.md)
**Primary repository:** Epistemap
**Consumers in scope:** CiteGeist, GroundRecall, and Didactopus
**Audience:** coding agents implementing one bounded phase at a time

## Objective

Replace ambiguous scalar `confidence` fields with typed, provenance-bearing,
versioned assessments while preserving compatibility during migration.

The overhaul must keep these questions separate:

1. Did an importer or extractor reproduce the source correctly?
2. Does a partial or free-text reference identify the same bibliographic work?
3. Is a graph assertion grounded in identifiable evidence?
4. How reliable is a source for this claim in this context?
5. What is the balance and quantity of supporting and challenging evidence?
6. What did an identified reviewer endorse?
7. Is a claim currently applicable for a time and scope?
8. Is a record relevant to a particular retrieval?
9. How likely is a learner or model response to be correct?
10. How much evidence supports a learner-mastery estimate?

No aggregate score may silently answer more than one of these questions.

## Repositories And Ownership

### Epistemap

Owns:

- portable confidence-assessment schemas;
- confidence bounds and missing-value semantics;
- evidence-unit and Bayesian assessment reports;
- prior and weighting-policy manifests;
- calibration metrics and assessment validation;
- graph serialization compatibility.

Does not own:

- CiteGeist bibliographic identity or review policy;
- GroundRecall promotion policy;
- GroundRecall reviewer authority;
- Didactopus learner-mastery policy;
- domain-specific source-trust judgments.

### CiteGeist

Owns:

- bibliographic identity and reference-resolution assessments;
- metadata-field and citation-relation provenance;
- topic-membership and discovery-ranking semantics;
- bibliography review state;
- the rule that citation topology is not claim truth or source quality.

Its Epistemap application and migration sequence are defined in
`CiteGeist/docs/epistemap-knowledge-graph-roadmap.md`.

### GroundRecall

Owns:

- extraction assessments from source adapters;
- reviewer assessments and their authority/provenance;
- claim validity, expiry, supersession, and retraction;
- mapping canonical evidence into Epistemap graph assessments;
- review and export presentation;
- the rule that Bayesian output is assessment metadata, not promotion authority.

### Didactopus

Owns:

- learner response probability and calibration;
- mastery estimates and evidence coverage;
- pedagogical thresholds and stop criteria;
- extraction/structural assessments created during course graph construction;
- presentation of Epistemap reliability without converting it into learner
  mastery or claim truth.

## Invariants

- Unknown is represented by `None` or an explicit `unknown` state, never `0.0`.
- Numeric probability-like values are finite and bounded from 0 through 1.
- An explicit zero is a real assessment and must not trigger fallback behavior.
- Every non-legacy assessment identifies its dimension, subject, method, and
  recording time.
- Computed assessments identify their input evidence and policy version.
- Confidence, current applicability, lifecycle status, and retrieval priority
  remain separate.
- Expiry and supersession do not lower confidence in a historical observation
  merely because it is no longer current.
- Bayesian posterior support is not labeled probability of truth.
- Revision relations such as `qualifies`, `corrects`, `retracts`, and
  `supersedes` are not automatically counted as ordinary negative evidence.
- Review confidence never authorizes promotion by itself.
- Existing JSON remains readable during the deprecation window.
- Migration is additive before it is subtractive.

## Terminology

Use these canonical dimension names in portable artifacts:

| Dimension | Meaning | Typical producer |
|---|---|---|
| `extraction_fidelity` | Confidence that content or structure was extracted correctly | parser or adapter |
| `identity_resolution` | Probability or score that a reference and candidate denote the same entity | resolver or reviewer |
| `grounding_strength` | Confidence that an assertion is traceable to its cited evidence | validation process |
| `source_reliability` | Context-specific assessment of a source | reviewer or calibrated source model |
| `evidential_support` | Support/challenge assessment under an explicit evidence policy | Epistemap |
| `reviewer_endorsement` | An identified reviewer's degree of endorsement | reviewer |
| `response_correctness` | Probability that a response or classification is correct | learner or model |
| `evidence_coverage` | Sufficiency or quantity of evidence for another estimate | Didactopus or audit process |

Do not encode the following as confidence dimensions:

- current applicability: use temporal validity and lifecycle records;
- retrieval relevance: keep it query-scoped in retrieval telemetry;
- promotion eligibility: compute it from policy requirements;
- sensitivity or privacy: use access-policy fields;
- lifecycle state: retain explicit status fields.

Applications may define namespaced dimensions such as
`didactopus:mastery_stability`. Portable Epistemap functions must ignore unknown
dimensions unless a caller explicitly requests them.

## Target Epistemap Schema

Implement these models in a new `src/epistemap/confidence.py` module. Exact
field names below are normative for the first implementation.

```python
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ConfidenceDimension = Literal[
    "extraction_fidelity",
    "identity_resolution",
    "grounding_strength",
    "source_reliability",
    "evidential_support",
    "reviewer_endorsement",
    "response_correctness",
    "evidence_coverage",
]

ConfidenceBand = Literal[
    "unknown",
    "very_low",
    "low",
    "moderate",
    "high",
    "very_high",
]


class ConfidenceInterval(BaseModel):
    level: float = Field(ge=0.0, le=1.0)
    lower: float = Field(ge=0.0, le=1.0)
    upper: float = Field(ge=0.0, le=1.0)
    method: str


class AssessmentMethodRef(BaseModel):
    name: str
    version: str
    policy_id: str = ""


class ConfidenceAssessment(BaseModel):
    schema_version: str = "1.0"
    assessment_id: str
    subject_id: str
    dimension: str
    value: float | None = Field(default=None, ge=0.0, le=1.0)
    band: ConfidenceBand = "unknown"
    interval: ConfidenceInterval | None = None
    assessor_id: str = ""
    method: AssessmentMethodRef
    basis_record_ids: list[str] = Field(default_factory=list)
    source_family_ids: list[str] = Field(default_factory=list)
    basis_hash: str = ""
    rationale: str = ""
    valid_at: str = ""
    recorded_at: str
    supersedes_assessment_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
```

Validation requirements:

- `interval.lower <= interval.upper`;
- `value`, when present, lies inside the interval;
- `band="unknown"` when `value is None`;
- `recorded_at` parses as an ISO-8601 timestamp;
- standard dimensions are documented, but namespaced extension dimensions
  containing `:` are accepted;
- an unnamespaced unknown dimension fails validation;
- duplicate `assessment_id` values fail bundle validation;
- a superseded assessment remains serialized and queryable.

Add `assessments: list[ConfidenceAssessment]` to `Node` and `Edge`. Retain the
legacy `confidence: float | None` field through the alpha deprecation window.
Legacy confidence must not be automatically assigned a semantic dimension.

## Compatibility Policy

### Reading

- Continue to accept graph bundles containing only legacy `confidence`.
- Validate a legacy value as finite and in the closed interval `[0, 1]`.
- Expose it in a `legacy_confidence` diagnostic.
- Do not synthesize a typed assessment unless the caller supplies a mapping
  policy such as `legacy_edge_confidence -> extraction_fidelity`.

### Writing

- New producers write typed assessments.
- During the compatibility window they may also write legacy `confidence` when
  a specific consumer requires it.
- A manifest must identify any down-conversion policy.
- No writer substitutes `0.0` for a missing assessment.

### Removal

Remove legacy graph confidence only after:

1. Epistemap has released the typed schema;
2. GroundRecall writes and reads it;
3. Didactopus writes and reads it;
4. golden cross-repository fixtures pass;
5. one tagged compatibility release has emitted deprecation warnings.

## Delivery Sequence

Implement phases in order. Each phase should be one pull request per affected
repository unless the phase explicitly says otherwise.

### Phase C0: Baseline And Contract

**Repository:** Epistemap
**Dependencies:** none

Tasks:

1. Add this document to the Epistemap roadmap index.
2. Capture representative graph fixtures from Epistemap, CiteGeist,
   GroundRecall, and Didactopus without rewriting them.
3. Add a compatibility matrix covering:
   - legacy graph with missing confidence;
   - legacy graph with explicit zero;
   - legacy graph with ordinary confidence;
   - graph with typed assessments only;
   - graph containing both representations;
   - namespaced extension dimension.
4. Document the semantic inventory of every current confidence field.
5. Record baseline test commands and results.

Files:

- `docs/confidence-overhaul-roadmap.md`
- `tests/fixtures/confidence/`
- `tests/test_confidence_compatibility.py`

Acceptance criteria:

- fixtures round-trip without semantic conversion;
- explicit zero survives a round trip;
- missing values remain missing;
- the inventory identifies the producing code and consumer for every field.

### Phase E1: Portable Assessment Models

**Repository:** Epistemap
**Dependencies:** C0

Tasks:

1. Add the target models to `src/epistemap/confidence.py`.
2. Export them from `src/epistemap/__init__.py`.
3. Add `assessments` collections to `Node` and `Edge`.
4. Bound legacy confidence values without changing `None`.
5. Add helpers:
   - `assessments_for(subject, dimension=None)`;
   - `active_assessments(...)`, excluding superseded assessments;
   - `latest_assessment(...)`, returning `None` on absence;
   - `validate_assessment_lineage(...)`.
6. Extend assessment-readiness validation with:
   - missing method;
   - invalid dimension;
   - duplicate ID;
   - dangling supersession;
   - interval/value inconsistency;
   - use of legacy confidence without a declared mapping policy.
7. Update JSON, JSON-LD, and Cytoscape exporters without flattening assessment
   provenance.

Acceptance criteria:

- all C0 fixtures pass;
- existing consumers can still load legacy bundles;
- out-of-range, NaN, and infinite values fail validation;
- typed assessments survive all supported exports;
- no helper converts absence to zero.

### Phase E2: Evidence Ledger And Bayesian Assessment

**Repository:** Epistemap
**Dependencies:** E1

Tasks:

1. Add `EvidenceUnit` and `EvidenceWeightingPolicy` models.
2. Convert graph edges into a visible evidence ledger before aggregation.
3. Derive evidence-unit identity in this order:
   - explicit evidence ID;
   - artifact plus source section or fragment;
   - edge ID;
   - deterministic hash of the serialized provenance tuple.
4. Deduplicate identical evidence units. Preserve all graph edges that referred
   to the unit.
5. Record source-family IDs. Do not assume different documents or edges are
   independent merely because their IDs differ.
6. Report both:
   - raw support/challenge totals;
   - deduplicated totals under the selected policy.
7. Rename report language from generic `confidence` to `posterior support`
   wherever the output is Bayesian evidence balance.
8. Keep support quantity, challenge quantity, effective evidence mass,
   posterior support, interval width, and prior sensitivity as separate output
   fields.
9. Exclude revision edges from challenge counts. Report them separately.
10. Add claim-level assessment as the primary operation. Concept-level output
    must identify the claims rolled into it.
11. Preserve the current beta-binomial method as policy version
    `beta_binomial_weighted_evidence_v1`.
12. Add an optional exact beta interval implementation or optional dependency.
    If unavailable, retain the normal approximation and state the method in
    every artifact. Never silently change interval methods.
13. Emit an `evidential_support` `ConfidenceAssessment` whose method and basis
    reference the evidence ledger and assessment manifest.

Acceptance criteria:

- duplicate paraphrases backed by one fragment count as one evidence unit;
- an explicit zero edge assessment is not replaced by a fallback;
- absent edge extraction fidelity invokes a documented weighting-policy
  default and emits a diagnostic;
- correction and supersession edges do not become ordinary failures;
- every posterior can be reconstructed from its ledger, prior, and policy;
- old Bayesian report keys remain readable for one compatibility release.

### Phase E3: Calibration Utilities

**Repository:** Epistemap
**Dependencies:** E1

Tasks:

1. Add Brier score, log loss, calibration-bin, and expected-calibration-error
   utilities for assessments whose semantics are genuine probabilities.
2. Require callers to declare the predicted event and observed outcome.
3. Refuse calibration of `extraction_fidelity`, `source_reliability`, or
   `reviewer_endorsement` unless the caller supplies resolved binary or
   probabilistic outcomes and a declared interpretation.
   `identity_resolution` may be calibrated when reviewed match/non-match
   outcomes and candidate-set policy are supplied.
4. Emit sample counts and warnings for underpowered bins.
5. Add deterministic JSON and Markdown calibration reports.

Acceptance criteria:

- tests cover perfect, underconfident, overconfident, and empty samples;
- no metric silently treats missing predictions as zero;
- reports distinguish discrimination, calibration, and evidence coverage.

### Phase CITE1: CiteGeist Confidence Migration

**Repository:** CiteGeist
**Dependencies:** E1; coordinate with CiteGeist CG0 and CG3

Tasks:

1. Inventory `VerificationResult.confidence`, alternate match scores,
   provenance confidence, topic confidence, claim support-gap scores, and graph
   expansion scores.
2. Map:
   - verification match scores to `identity_resolution`;
   - field provenance to `extraction_fidelity` or
     `citegeist:metadata_field_match`;
   - relation provenance to `extraction_fidelity` or `grounding_strength`;
   - topic membership to `citegeist:topic_relevance`;
   - claim support need to `support_gap_priority`, not confidence;
   - expansion rank to query-scoped retrieval telemetry.
3. Add a versioned assessment table and a dry-run-first, idempotent migration.
4. Keep legacy columns and serialized aliases for one compatibility release.
5. Add reviewed match/non-match outcomes for identity-resolution calibration.
6. Do not derive source reliability or evidential support from citation count,
   graph degree, or bibliographic match score.

Acceptance criteria:

- missing and explicit zero remain distinct;
- every migrated value has one declared meaning and method;
- ambiguous legacy rows are reported rather than guessed;
- identity-resolution calibration uses reviewed outcomes;
- CiteGeist graph exports preserve typed assessments and their provenance.

### Phase G1: GroundRecall Schema Migration

**Repository:** GroundRecall
**Dependencies:** Epistemap E1 release

Tasks:

1. Change `confidence_hint` and `review_confidence` to optional bounded fields.
2. Add typed assessments to observations, claims, and relations using the
   Epistemap model or an explicitly lossless canonical equivalent.
3. Treat legacy `confidence_hint` as unknown unless an adapter-specific mapping
   declares its semantics.
4. Fix truthiness fallback:

   ```python
   review_confidence or confidence_hint or 0.0
   ```

   must not survive. Selection must test `is not None`.
5. Add a dry-run-first migration command:

   ```text
   groundrecall confidence-migrate STORE --report REPORT.json
   groundrecall confidence-migrate STORE --apply --report REPORT.json
   ```

6. Do not reinterpret legacy `0.0` automatically. Report it as ambiguous unless
   provenance demonstrates it was explicit.
7. Version migration events and preserve pre-migration records.

Files expected to change:

- `src/groundrecall/models.py`
- `src/groundrecall/epistemap_adapter.py`
- `src/groundrecall/promotion.py`
- `src/groundrecall/store.py`
- `src/groundrecall/cli.py`
- adapter modules that emit `confidence_hint`

Acceptance criteria:

- missing and explicit zero remain distinguishable;
- all numeric values are bounded;
- migration is idempotent;
- dry-run performs no store writes;
- rollback restores the pre-migration representation;
- legacy stores remain readable.

### Phase G2: GroundRecall Producer Semantics

**Repository:** GroundRecall
**Dependencies:** G1

Tasks:

1. Replace adapter hints with `extraction_fidelity` assessments.
2. Give every adapter rule a stable method name and version.
3. Record the extracted field, rule identifier, adapter version, basis record,
   and rationale.
4. Do not propagate extraction fidelity into reviewer endorsement or
   evidential support.
5. Add an assessment-readiness report for:
   - hardcoded values without method IDs;
   - unknown semantics;
   - missing basis records;
   - unbounded legacy values;
   - incompatible duplicate active assessments.
6. Update review and export payloads to display dimension names instead of a
   generic confidence label.

Acceptance criteria:

- each existing adapter fixture produces a typed assessment;
- identical adapter input produces identical basis hashes;
- hardcoded adapter values are visibly extraction assessments;
- no adapter output can be mistaken for probability of claim truth.

### Phase G3: Reviewer And Temporal Assessments

**Repository:** GroundRecall
**Dependencies:** G2 and memory-lifecycle R1 foundations

Tasks:

1. Add append-only reviewer-endorsement records with reviewer ID, method,
   rationale, evidence inspected, scope, and time.
2. Permit multiple active reviewer assessments; do not average them
   automatically.
3. Add adjudication records that reference the assessments considered.
4. Represent validity, confirmation, expiry, supersession, and retraction with
   lifecycle and temporal records, not confidence mutation.
5. Add a confidence profile to query and review bundles containing:
   - extraction fidelity;
   - grounding strength;
   - reviewer endorsements and disagreement;
   - Bayesian evidential support;
   - temporal applicability as a separate block;
   - missingness and readiness diagnostics.
6. Keep promotion policy based on provenance, authority, lifecycle, and review
   completion. Confidence values may prioritize review but may not authorize
   promotion.

Acceptance criteria:

- a reviewer can enter an explicit zero endorsement;
- disagreement remains visible after adjudication;
- expiry changes current applicability without modifying historical support;
- supersession links old and new records;
- query exports explain which assessment was selected and why.

### Phase G4: GroundRecall Bayesian Integration

**Repository:** GroundRecall
**Dependencies:** Epistemap E2 and GroundRecall G2

Tasks:

1. Produce claim-level evidence ledgers before concept summaries.
2. Map fragments, observations, claims, and source families to stable evidence
   identities.
3. Prevent derived claims and their source observations from being counted as
   independent evidence when they share a basis.
4. Export raw and deduplicated evidence totals, policy ID, prior profile,
   posterior support, interval method, prior sensitivity, and diagnostics.
5. Preserve compatibility aliases for current Bayesian export consumers.
6. Add paired current-state and historical `as_of` fixtures.

Acceptance criteria:

- each concept posterior names its component claim assessments;
- each claim posterior is reproducible from exported evidence;
- source-family dependence is visible even when no adjustment is applied;
- Bayesian output never changes canonical review confidence or status.

### Phase D1: Didactopus Confidence Inventory And Naming

**Repository:** Didactopus
**Dependencies:** Epistemap E1

Tasks:

1. Add a machine-readable inventory mapping each existing field to one of:
   - graph extraction/structural assessment;
   - learner response probability;
   - mastery score;
   - evidence coverage;
   - knowledge-candidate extraction assessment;
   - legacy ambiguous.
2. Change Pydantic and ORM numeric fields to bounded optional values where
   absence is meaningful.
3. Add an ORM migration; do not rewrite existing zero values without an
   ambiguity report.
4. Retain API aliases during the compatibility window.

Files requiring explicit review:

- `src/didactopus/models.py`
- `src/didactopus/learner_state.py`
- `src/didactopus/evidence_engine.py`
- `src/didactopus/orm.py`
- `src/didactopus/knowledge_graph.py`
- `src/didactopus/graph_retrieval.py`
- `src/didactopus/recommendations.py`
- `src/didactopus/readiness.py`
- `src/didactopus/stop_criteria.py`
- benchmark and experiment modules emitting response confidence

Acceptance criteria:

- the inventory covers every `confidence` and `confidence_hint` occurrence in
  production code;
- database and JSON round trips preserve missing versus explicit zero;
- API compatibility tests document every deprecated alias.

### Phase D2: Separate Learner Evidence Coverage From Confidence

**Repository:** Didactopus
**Dependencies:** D1

Tasks:

1. Rename `confidence_from_weight(total_weight)` to
   `evidence_coverage_from_weight(total_weight)`.
2. Rename `ConceptEvidenceSummary.confidence` to `evidence_coverage`.
3. Rename stop, readiness, and recommendation thresholds accordingly.
4. Retain deprecated aliases at API boundaries for one compatibility release.
5. Do not call the saturating evidence-mass function a probability or
   confidence.
6. Keep mastery score separate from evidence coverage.
7. If a mastery uncertainty model is later added, give it a separate typed
   assessment and validation dataset.

Acceptance criteria:

- increasing duplicate evidence does not masquerade as increased correctness;
- mastery and evidence coverage remain separately visible;
- legacy callers receive warnings and unchanged numeric behavior;
- documentation no longer describes evidence mass as confidence.

### Phase D3: Graph And Candidate Assessment Migration

**Repository:** Didactopus
**Dependencies:** D1 and Epistemap E2

Tasks:

1. Replace hardcoded knowledge-graph edge confidence with typed
   `extraction_fidelity` or `grounding_strength`, according to the producing
   rule.
2. Give each graph-building rule a stable method name and version.
3. Migrate knowledge-candidate `confidence_hint` to a typed extraction or
   synthesis assessment; do not map it to source reliability.
4. Consume the Epistemap confidence profile without flattening it into one
   number.
5. Update mentor/evaluator prompts to distinguish posterior support,
   provenance strength, prior sensitivity, and missing assessment.
6. Update GroundRecall bridge sidecars and golden fixtures.

Acceptance criteria:

- structural inference is visibly different from source-grounded assertion;
- mentor context does not describe posterior support as truth probability;
- old pack fixtures remain loadable;
- new pack fixtures preserve typed assessments.

### Phase D4: Response Calibration And Learner Policy

**Repository:** Didactopus
**Dependencies:** Epistemap E3 and D2

Tasks:

1. Keep benchmark answer confidence explicitly defined as probability the
   selected answer is correct.
2. Preserve the separate derived `p_true` transformation for
   true/false/unknown tasks.
3. Use Epistemap calibration utilities for Brier, log-loss, bin, and ECE
   reports.
4. Report abstention, discrimination, and calibration separately.
5. Require minimum sample warnings before using calibration results to change
   mentoring or stop policies.
6. Version all learner-policy thresholds and record them in experiment
   manifests.

Acceptance criteria:

- perfect, underconfident, overconfident, and abstaining fixtures produce the
  expected reports;
- no learner progression decision consumes graph evidential support as learner
  mastery confidence;
- policy changes are reproducible from a manifest.

### Phase X1: Cross-Repository Release

**Repositories:** Epistemap, CiteGeist, GroundRecall, Didactopus
**Dependencies:** E1, E2, CITE1, G1–G4, D1–D4

Release order:

1. Tag an Epistemap alpha release containing typed assessments and compatibility
   readers.
2. Update CiteGeist's optional graph dependency to that release range.
3. Update GroundRecall's Epistemap requirement to that release range.
4. Update Didactopus from its pinned Epistemap commit to the tagged compatible
   release or a documented new commit.
5. Run golden fixtures against installed packages, not only sibling source
   paths.
6. Tag consumer compatibility releases.
7. Begin the deprecation clock for legacy scalar graph confidence.

Required integration matrix:

| Producer | Consumer | Required artifact |
|---|---|---|
| legacy Epistemap | new Epistemap | legacy graph fixture |
| CiteGeist | Epistemap | bibliography graph and identity assessments |
| CiteGeist | GroundRecall | OKF graph, source slots, and reviewed anchors |
| CiteGeist | Didactopus | reviewed bibliography source bundle |
| GroundRecall | Epistemap | claim evidence ledger and assessment manifest |
| GroundRecall | Didactopus | query bundle and pack sidecars |
| Didactopus | Epistemap | course graph and response-calibration rows |
| Didactopus | GroundRecall | knowledge-candidate import fixture |

Acceptance criteria:

- each matrix row has an automated fixture;
- installed-package tests use the declared dependency versions;
- no test relies accidentally on another repository's working tree;
- deprecation warnings identify the exact replacement field or assessment.

## Testing Commands

Run commands from the named repository. A coding agent must capture failures
before editing and compare them with the final result.

### Epistemap

```bash
pytest -q
```

### GroundRecall against a local Epistemap checkout

```bash
PYTHONPATH=src pytest -q
```

### CiteGeist against a local Epistemap checkout

```bash
PYTHONPATH=src pytest -q
```

### Didactopus against a local Epistemap checkout

```bash
PYTHONPATH=src pytest -q
```

Before a release, repeat CiteGeist, GroundRecall, and Didactopus tests in clean
virtual environments with the declared Epistemap package installed and without
the sibling source path.

## Coding-Agent Execution Rules

For every phase:

1. Read repository instructions and inspect `git status`.
2. Do not overwrite unrelated working-tree changes.
3. Implement only the named phase and its prerequisites.
4. Add failing tests before changing behavior.
5. Prefer additive schema changes and explicit migration commands.
6. Do not bulk-rewrite stored user data.
7. Make migrations dry-run by default and idempotent.
8. Preserve raw inputs and emit a machine-readable migration report.
9. Record schema, method, policy, and adapter versions in generated artifacts.
10. Run the repository test suite and the relevant cross-repository fixtures.
11. Update documentation and deprecation notes in the same change.
12. Stop if a semantic mapping is ambiguous; report the affected field and
    require an explicit mapping policy rather than guessing.

Each phase handoff must report:

- files changed;
- schema/API changes;
- migration behavior;
- compatibility aliases added or removed;
- tests run and results;
- unresolved ambiguous legacy data;
- the next unblocked phase.

## Non-Goals

- A universal probability that a claim is true.
- Automatic promotion or rejection from confidence.
- Confidence decay based only on age.
- Automatic averaging of reviewer disagreement.
- A heavyweight Bayesian network before evidence dependency is represented.
- Replacing provenance with source reputation.
- Treating citation count, citation topology, or bibliographic match as claim
  truth.
- Converting learner evidence quantity into probability of mastery.
- Removing legacy fields before all consumers migrate.

## Definition Of Done

The overhaul is complete when:

- all new assessments are typed, bounded, provenance-bearing, and versioned;
- missing and explicit zero are distinct throughout all four repositories;
- adapter fidelity, identity resolution, reviewer endorsement, posterior
  support, temporal applicability, retrieval relevance, learner response
  probability, and evidence coverage are not conflated;
- Bayesian reports are reproducible from an evidence ledger and policy
  manifest;
- current applicability changes do not rewrite historical support;
- calibration metrics are available where outcomes make calibration
  meaningful;
- cross-repository fixtures pass against installed package versions;
- legacy scalar graph confidence has completed a documented deprecation cycle.
