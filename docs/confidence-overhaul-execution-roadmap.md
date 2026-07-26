# Confidence Overhaul Execution Roadmap After v0.1.0a1

**Status:** W0 and W1 merged; W2 implemented locally; remaining packages await dependency gates

**Baseline date:** 2026-07-25

**Coordinator:** Epistemap

**Repositories:** Epistemap, GroundRecall, CiteGeist, Didactopus

**Starting release:** Epistemap `v0.1.0a1`

## Mission

Complete the remaining confidence overhaul without collapsing distinct
assessment meanings, rewriting ambiguous stored data, or removing compatibility
fields prematurely.

This document is the implementation queue. The broader design and rationale
remain in:

- `docs/confidence-overhaul-roadmap.md`;
- `docs/confidence-overhaul-implementation-status.md`;
- CiteGeist `docs/epistemap-knowledge-graph-roadmap.md`;
- GroundRecall `docs/memory-lifecycle-roadmap.md`;
- Didactopus `docs/confidence-inventory.json`.

When this execution roadmap conflicts with an older status statement, inspect
the merged source and update both documents in the same pull request.

## Verified Starting State

| Repository | Baseline `main` | Relevant release state |
| --- | --- | --- |
| Epistemap | `6103d9a` | `v0.1.0a1` published |
| GroundRecall | `3e4d1d2` | consumes Epistemap `v0.1.0a1` |
| CiteGeist | `edd1b85` | local canonical-equivalent assessment prototype |
| Didactopus | `e6e28cd` | consumes Epistemap `v0.1.0a1` |

Do not assume these hashes remain current. At the start of every work package,
fetch the remote, inspect `git status`, and rebase the plan on the current
default branch without discarding user changes.

## Non-Negotiable Invariants

- Missing is `None` or an explicit unknown state, never implicit `0.0`.
- Explicit zero survives parsing, storage, export, and fallback selection.
- Assessment dimension, method, version, subject, basis, and recording time
  remain available after every transformation.
- Extraction fidelity is not reviewer endorsement, source reliability,
  evidential support, current applicability, retrieval rank, or learner
  mastery.
- Expiry, supersession, retraction, and archival state do not rewrite
  historical assessments.
- Citation count, graph degree, bibliographic match, and retrieval relevance
  do not become source reliability or claim truth.
- Bayesian output is posterior evidential support under a declared policy, not
  a truth oracle or promotion authority.
- Reviewer disagreement is preserved; do not average it silently.
- Migrations are dry-run first, idempotent, additive, and report ambiguous
  rows instead of guessing.
- Legacy fields remain readable until the documented deprecation cycle is
  complete.

## Coding-Model Authority

The coding model may:

- edit source, tests, fixtures, and documentation in the named repository;
- create temporary stores and virtual environments for tests;
- add additive schemas and reversible migration code;
- create one scoped branch and pull request per work package.

The coding model must not:

- rewrite a user's real store while testing;
- delete legacy fields or historical assessments;
- infer a dimension for ambiguous legacy data;
- publish packages, create releases, tag versions, or begin deprecation without
  explicit human authorization;
- merge unrelated working-tree changes;
- expose database backups, participant results, credentials, local paths, or
  private run logs.

Stop and request a decision when:

- a stored field has more than one plausible semantic mapping;
- a schema change cannot preserve missing versus explicit zero;
- rollback would lose provenance or prior values;
- a dependency requires an unreleased API;
- a test failure predates the work package or belongs to unrelated changes.

## Required Work Loop

For every work package:

1. Read this file, the owning repository roadmap, and repository instructions.
2. Record `git status -sb`, current commit, dependency versions, and baseline
   test results.
3. Add failing acceptance tests before behavioral code.
4. Implement only the named package and prerequisites.
5. Run focused tests, the full owning suite, and stated integration tests.
6. Run `git diff --check`.
7. Update the implementation-status document and any changed public API docs.
8. Commit with a terse package-specific message.
9. Push a branch and open a draft pull request containing files changed,
   migrations, compatibility behavior, tests, ambiguities, and next package.

Generated migration reports and run logs are private by default. Commit only
synthetic fixtures and reviewed, allowlisted reports.

## Dependency Order

```text
W0 contract fixtures
├── W1 evidence ledger models
│   └── W2 ledger conversion and deduplication
│       ├── W3 Bayesian assessment output
│       │   └── W8 GroundRecall Bayesian integration
│       └── W9 cross-repository installed matrix
├── W4 calibration eligibility
│   ├── W6 CiteGeist identity calibration
│   └── W12 Didactopus response calibration
├── W5 CiteGeist migration CLI
│   └── W6 CiteGeist identity and graph completion
├── W7 GroundRecall schema migration
│   ├── W8 GroundRecall producer/reviewer/Bayesian integration
│   └── W10 Didactopus candidate bridge
└── W9 installed matrix
    └── W13 compatibility releases and deprecation start
```

Packages on separate branches may proceed in parallel only when the dependency
arrows are satisfied by merged commits or tagged releases.

## W0: Golden Contract And Semantic Inventory

**Repository:** Epistemap

**Depends on:** `v0.1.0a1`

**Local status:** implemented with synthetic raw/expected fixtures, matrix, and
inventory; merge this work before treating W1, W4, W5, or W7 as unblocked.

**Objective:** make compatibility claims executable before further migrations.

### Files

- add `tests/fixtures/confidence/`;
- extend `tests/test_confidence_compatibility.py`;
- add `docs/confidence-field-inventory.json`;
- add `docs/confidence-compatibility-matrix.md`.

### Tasks

1. Capture synthetic, minimal artifacts for:
   - legacy missing confidence;
   - legacy explicit zero;
   - legacy ordinary value;
   - typed assessments only;
   - both typed and legacy forms with a declared mapping;
   - namespaced extension dimension;
   - superseded assessment lineage;
   - invalid or ambiguous legacy mapping.
2. Add one fixture for each producer: Epistemap, CiteGeist, GroundRecall, and
   Didactopus. Do not copy real user stores.
3. Inventory every production `confidence`, `confidence_hint`, match score,
   evidence-coverage value, posterior-support value, and review score across
   all four repositories. Record producer, consumer, meaning, missing-value
   behavior, persistence location, and migration owner.
4. Add a test that fails when a declared fixture is missing from the
   compatibility matrix.
5. Preserve raw fixture payloads; expected normalized payloads belong in
   separate files.

### Acceptance

- all fixtures round-trip without unintended semantic conversion;
- missing and explicit zero remain distinct;
- every production scalar has an owner and declared disposition;
- fixture provenance identifies the source repository and schema version;
- `pytest -q` passes in Epistemap.

### Handoff

Report fixture IDs, inventory gaps, tests, and any ambiguous fields. W1, W4,
W5, and W7 unblock only after W0 merges.

## W1: Evidence Ledger Models

**Repository:** Epistemap

**Depends on:** W0

**Local status:** implemented with versioned evidence ledger models,
deterministic serialization/hash helpers, identity derivation, and validation;
merge this work before treating W2 or W3 as unblocked.

**Objective:** represent evidence inputs explicitly before aggregation.

### Files

- add `src/epistemap/evidence.py`;
- export models from `src/epistemap/__init__.py`;
- add `tests/test_evidence_ledger.py`;
- update `docs/bayesian-reliability.md`.

### Models

Implement versioned Pydantic models for:

- `EvidenceUnit`;
- `EvidenceReference`;
- `EvidenceWeightingPolicy`;
- `EvidenceLedger`;
- `EvidenceLedgerDiagnostic`.

Each evidence unit must retain:

- stable unit ID and subject claim ID;
- stance: support, challenge, neutral, or revision;
- source record, artifact, fragment, and graph-edge IDs;
- source-family IDs;
- typed input assessments;
- raw and effective weights;
- deduplication key and rationale;
- policy/method versions.

### Tasks

1. Define deterministic serialization and hashing.
2. Derive evidence identity in this order:
   explicit evidence ID; artifact plus fragment; edge ID; provenance hash.
3. Define revision relations separately from challenge evidence.
4. Add validators for duplicate IDs, missing subjects, invalid weights,
   dangling references, and unversioned policy methods.
5. Do not implement Bayesian aggregation in this package.

### Acceptance

- identical inputs serialize identically;
- explicit zero input assessments remain zero;
- missing weights remain missing until policy application;
- revisions cannot validate as ordinary challenge evidence;
- source-family dependence is representable without assuming an adjustment.

## W2: Graph-To-Ledger Conversion And Deduplication

**Repository:** Epistemap

**Depends on:** W1

**Local status:** implemented with graph/edge-to-ledger conversion,
deduplication, referring-edge preservation, raw/deduplicated count and weight
reports, missing-weight diagnostics, source-family recording, concept component
claim listing, and Bayesian compatibility report integration.

**Objective:** produce a visible, reconstructable ledger from graph evidence.

### Files

- extend `src/epistemap/evidence.py`;
- integrate from `src/epistemap/bayesian.py` without removing old entry points;
- add deduplication fixtures to `tests/fixtures/confidence/`;
- extend `tests/test_evidence_ledger.py` and `tests/test_bayesian.py`.

### Tasks

1. Convert claim-level support, challenge, and revision edges into ledger
   entries.
2. Preserve all referring edge IDs when duplicate edges collapse to one unit.
3. Report raw and deduplicated counts and weights.
4. Apply a versioned missing-weight default and emit a diagnostic whenever it
   is used.
5. Record known source-family dependence even when the selected policy applies
   no correlation discount.
6. Make claim-level conversion primary. Concept-level conversion must list
   component claims.

### Acceptance

- paraphrases backed by the same fragment count once after deduplication;
- raw totals retain their original edge count;
- correction, retraction, qualification, and supersession are reported outside
  ordinary challenge totals;
- every effective weight identifies its input and policy rule;
- old callers continue to function.

## W3: Reconstructable Bayesian Assessment

**Repository:** Epistemap

**Depends on:** W2

**Objective:** make posterior-support reports reproducible from exported data.

### Files

- refactor `src/epistemap/bayesian.py`;
- extend `src/epistemap/confidence.py` only when schema changes are necessary;
- extend `tests/test_bayesian.py`;
- update `docs/bayesian-reliability.md`.

### Tasks

1. Aggregate only from an `EvidenceLedger`.
2. Preserve policy ID `beta_binomial_weighted_evidence_v1`.
3. Export prior parameters, raw and deduplicated totals, effective evidence
   mass, posterior support, interval method, interval bounds, prior
   sensitivity, diagnostics, and ledger basis IDs.
4. Emit an `evidential_support` `ConfidenceAssessment`.
5. Preserve old report keys as documented compatibility aliases.
6. Use an exact interval only when the method is explicit and reproducible;
   otherwise retain and name the normal approximation.

### Acceptance

- each posterior reconstructs exactly from its exported ledger, prior, and
  policy within documented floating-point tolerance;
- changing edge order does not change the result;
- duplicate evidence affects raw totals but not deduplicated totals;
- explicit zero never triggers a legacy or default fallback;
- old report consumers pass unchanged compatibility tests.

## W4: Calibration Eligibility And Report Contract

**Repository:** Epistemap

**Depends on:** W0

**Objective:** prevent mathematically valid but semantically invalid
calibration reports.

### Files

- extend `src/epistemap/calibration.py`;
- extend `tests/test_calibration.py`;
- add `docs/calibration-contract.md`.

### Tasks

1. Require a declared predicted event, outcome interpretation, sample
   selection policy, and assessment dimension.
2. Permit response correctness by default.
3. Permit identity resolution only with reviewed match/non-match outcomes and
   a declared candidate-set policy.
4. Reject extraction fidelity, source reliability, and reviewer endorsement
   unless resolved outcomes and an explicit probabilistic interpretation are
   supplied.
5. Separate calibration, discrimination, abstention, and evidence coverage in
   report output.
6. Preserve deterministic JSON and Markdown output.

### Acceptance

- perfect, underconfident, overconfident, abstaining, and empty fixtures pass;
- semantically ineligible dimensions fail with actionable errors;
- no missing prediction becomes zero;
- underpowered bins identify their sample count and warning threshold.

## W5: CiteGeist Durable Migration Command

**Repository:** CiteGeist

**Depends on:** W0

**Objective:** finish the dry-run-first migration surface without guessing
legacy meanings.

### Files

- extend `src/citegeist/confidence.py`;
- extend `src/citegeist/storage.py`;
- add command handling in `src/citegeist/cli.py`;
- extend `tests/test_storage.py` and `tests/test_cli.py`;
- update `docs/epistemap-knowledge-graph-roadmap.md`.

### Tasks

1. Store the complete portable assessment shape, including intervals.
2. Add:

   ```text
   citegeist --db DB confidence-migrate --report REPORT.json
   citegeist --db DB confidence-migrate --apply --report REPORT.json
   ```

3. Keep dry-run as the default.
4. Before apply, create or require an explicit backup destination.
5. Run apply in a transaction; record migration version and source row IDs.
6. Make reruns idempotent.
7. Add a tested restore procedure.
8. Report support-gap and retrieval scores as non-confidence fields.

### Acceptance

- dry-run writes nothing;
- apply and repeated apply produce the same assessment set;
- rollback/restore returns a fixture database to its prior representation;
- missing and explicit zero remain distinct;
- ambiguous rows appear in the report and are not migrated.

## W6: CiteGeist Identity Outcomes And Graph Export

**Repository:** CiteGeist

**Depends on:** W4 and W5

**Objective:** complete bibliographic identity semantics and portable export.

### Tasks

1. Introduce canonical `match_score`; retain `confidence` as a deprecated
   read-only compatibility alias.
2. Store reviewed match/non-match outcomes with reviewer, time, candidate-set
   policy, and evidence inspected.
3. Produce identity-resolution calibration rows for Epistemap W4.
4. Export typed assessments through a deterministic Epistemap graph profile.
5. Preserve metadata assertions, relation provenance, source families,
   conflicts, correction events, and review state.
6. Keep citation topology and topic relevance out of evidential support.

### Acceptance

- verification output cannot be mistaken for source reliability;
- graph exports are deterministic;
- calibration uses only reviewed outcomes;
- correction history and rejected alternatives remain auditable;
- no structural graph metric is named confidence, reliability, quality, or
  truth.

## W7: GroundRecall Store Migration And Producer Contract

**Repository:** GroundRecall

**Depends on:** W0

**Objective:** migrate schema and producer semantics before adding reviewer or
Bayesian policy.

### Files

- `src/groundrecall/models.py`;
- `src/groundrecall/store.py`;
- `src/groundrecall/groundrecall_store.py` if still active;
- `src/groundrecall/promotion.py`;
- `src/groundrecall/cli.py`;
- `src/groundrecall/groundrecall_source_adapters/`;
- corresponding tests and synthetic stores.

### Tasks

1. Add a versioned, append-only assessment persistence representation.
2. Add:

   ```text
   groundrecall confidence-migrate STORE --report REPORT.json
   groundrecall confidence-migrate STORE --apply --report REPORT.json
   ```

3. Preserve pre-migration records and add a tested rollback operation.
4. Treat legacy zero as ambiguous unless provenance proves it was explicit.
5. Replace blanket `confidence_hint` mapping with adapter-specific policies.
6. Give every producer rule a stable method/version, basis IDs, deterministic
   basis hash, rationale, and extracted field.
7. Add an assessment-readiness command/report.

### Acceptance

- legacy stores remain readable;
- dry-run and rollback behavior are tested;
- every mapped value identifies its producer policy;
- hardcoded hints without a method fail readiness;
- no extraction assessment becomes review endorsement or promotion authority.

## W8: GroundRecall Reviewer, Temporal, And Bayesian Profiles

**Repository:** GroundRecall

**Depends on:** W3 and W7

**Objective:** expose a governed confidence profile without changing promotion
authority.

### Tasks

1. Add append-only reviewer endorsements with reviewer identity, scope,
   rationale, evidence inspected, method, and time.
2. Preserve multiple active assessments and disagreement.
3. Add adjudication records referencing the assessments considered.
4. Keep validity, confirmation, expiry, supersession, and retraction in
   temporal/lifecycle records.
5. Map GroundRecall claims and fragments into Epistemap evidence ledgers.
6. Export query/review profiles containing extraction, grounding, reviewer,
   posterior-support, temporal-applicability, and readiness blocks.
7. Explain assessment selection without silently averaging reviewers.

### Acceptance

- explicit zero reviewer endorsement is valid;
- adjudication does not erase disagreement;
- expiry changes current applicability without changing historical support;
- claim posteriors reconstruct from exported ledgers;
- promotion tests prove confidence alone cannot promote a record.

## W9: Installed Cross-Repository Matrix

**Coordinator:** Epistemap

**Depends on:** W0, W2, W5, and W7

**Objective:** eliminate accidental sibling-checkout compatibility.

### Tasks

1. Add an allowlisted matrix manifest describing producer, consumer, artifact,
   schema/release versions, and expected test command.
2. Test these paths:
   - legacy Epistemap to current Epistemap;
   - CiteGeist to Epistemap;
   - CiteGeist to GroundRecall;
   - CiteGeist to Didactopus;
   - GroundRecall to Epistemap;
   - GroundRecall to Didactopus;
   - Didactopus to Epistemap;
   - Didactopus to GroundRecall.
3. Create clean temporary environments with declared dependencies installed.
4. Unset sibling `PYTHONPATH`.
5. Verify deterministic artifact hashes where the format promises
   determinism.
6. Store only synthetic fixtures and compact expected outputs.

### Acceptance

- every matrix row is automated;
- no test imports another repository from its working tree accidentally;
- declared dependency versions appear in the report;
- failures identify producer, consumer, fixture, and schema versions.

## W10: Didactopus Inventory, ORM, And Candidate Migration

**Repository:** Didactopus

**Depends on:** W7 and W9 fixture conventions

**Objective:** finish D1 and migrate knowledge-candidate confidence safely.

### Files

- `docs/confidence-inventory.json`;
- `src/didactopus/models.py`;
- `src/didactopus/learner_state.py`;
- `src/didactopus/orm.py`;
- `src/didactopus/knowledge_graph.py`;
- `src/didactopus/graph_retrieval.py`;
- citation and GroundRecall bridge adapters;
- migration and compatibility tests.

### Tasks

1. Add a test that inventories every production `confidence` and
   `confidence_hint` occurrence.
2. Classify duplicate API, learner-state, ORM, bridge, citation, benchmark, and
   experiment fields.
3. Make absence-meaningful Pydantic and ORM fields optional and bounded.
4. Add an additive ORM migration and zero-ambiguity report.
5. Preserve API aliases and JSON/database round trips.
6. Convert candidate and citation extraction hints into typed assessments with
   stable rule IDs and basis hashes.
7. Consume GroundRecall profiles without flattening.

### Acceptance

- inventory coverage is enforced by tests;
- database and JSON round trips preserve missing versus zero;
- structural inference differs visibly from source-grounded assertion;
- old packs remain readable;
- new bridge fixtures preserve typed profiles.

## W11: Didactopus Evidence-Coverage API Completion

**Repository:** Didactopus

**Depends on:** W10

**Objective:** finish the compatibility boundary around evidence coverage.

### Tasks

1. Rename internal thresholds and report keys from generic confidence to
   evidence coverage.
2. Retain deprecated aliases only at public boundaries.
3. Emit deprecation warnings naming the replacement.
4. Add a duplicate-evidence fixture proving increased evidence mass does not
   claim increased correctness.
5. Keep mastery score and evidence coverage separately visible in exports and
   stop policies.

### Acceptance

- internal code no longer calls evidence mass confidence;
- legacy callers receive warnings and unchanged numeric behavior;
- docs and examples use the canonical name;
- duplicate evidence cannot alter a correctness probability.

## W12: Didactopus Response Calibration

**Repository:** Didactopus

**Depends on:** W4 and W11

**Objective:** use the shared calibration contract for learner/model response
probabilities.

### Tasks

1. Keep response confidence defined as probability the selected answer is
   correct.
2. Preserve the separate `p_true` transform for true/false/unknown tasks.
3. Use Epistemap calibration reports for benchmark and experiment output.
4. Report correctness discrimination, calibration, abstention, and evidence
   coverage separately.
5. Version mentoring/stop-policy thresholds in experiment manifests.
6. Prevent graph posterior support from entering learner mastery state.

### Acceptance

- perfect, underconfident, overconfident, and abstaining fixtures pass;
- small samples warn before policy changes;
- policy changes reconstruct from manifests;
- no learner progression decision consumes graph support as mastery
  confidence.

## W13: Compatibility Releases And Deprecation Start

**Repositories:** all four

**Depends on:** W3-W12 and a fully passing W9

**Objective:** release the completed compatibility layer without removing
legacy data.

### Human approval required

The coding model prepares release pull requests and notes but must not tag,
publish, or merge releases without explicit authorization.

### Tasks

1. Select release versions according to each repository's existing policy.
2. Freeze dependency tags/ranges and installed-package test results.
3. Publish compatibility notes listing every legacy alias, replacement, and
   warning.
4. Tag consumer releases in dependency order.
5. Begin a documented deprecation clock for legacy scalar graph confidence.
6. Do not remove legacy fields in this package.

### Acceptance

- W9 passes against tagged versions;
- migration and rollback commands are documented and tested;
- warnings name exact replacements;
- release notes list unresolved ambiguous legacy data;
- public artifacts exclude private stores, backups, run logs, and participant
  results.

## Definition Of Execution Complete

This execution roadmap is complete only when:

- W0-W13 are merged;
- the installed matrix passes against tagged versions;
- evidence posteriors reconstruct from exported ledgers and policies;
- CiteGeist and GroundRecall migrations are dry-run-first and reversible;
- GroundRecall reviewer disagreement and temporal applicability remain
  auditable;
- Didactopus separates evidence coverage, mastery, response probability, and
  graph support throughout persistence and policy;
- consumer compatibility releases are published;
- the legacy deprecation clock has started but no legacy field has yet been
  removed.

Update `docs/confidence-overhaul-implementation-status.md` after every merged
work package. Never mark the overhaul complete merely because all current tests
pass.
