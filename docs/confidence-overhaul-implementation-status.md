# Unified Confidence Overhaul: Audited Implementation Status

**Audit date:** 2026-07-26

**Review state:** W0-W13 complete; compatibility releases are tagged for all
four repositories; the legacy scalar graph-confidence deprecation clock started
on 2026-07-26

**Scope:** Epistemap, CiteGeist, GroundRecall, and Didactopus

## Executive Status

The overhaul is **complete through W13**. The merged repositories contain the
portable assessment foundation,
consumer migrations, compatibility aliases, evidence-coverage separation,
response calibration, installed-matrix checks, compatibility release tags, and
the documented deprecation-clock start.

The dependency-ordered coding-model queue for the remaining work is
[`confidence-overhaul-execution-roadmap.md`](confidence-overhaul-execution-roadmap.md).

Current released heads after W13:

| Repository | Released head | Compatibility tag |
| --- | --- | --- |
| Epistemap | `c6d2a07` | `v0.1.0a2` |
| CiteGeist | `91810d2` | `v0.1.1` |
| GroundRecall | `7366730` | `v0.1.0a1` |
| Didactopus | `aec136c` | `v0.1.1` |

These release tags are Git tags only; no package-index publication was
performed.

## Phase Status

Status meanings:

- `substantial`: the central behavior exists locally, with bounded remaining
  acceptance work;
- `partial`: some tasks exist, but one or more defining behaviors are absent;
- `not started`: no roadmap-specific implementation was found;
- `blocked`: implementation depends on an unreleased prerequisite or explicit
  release/migration authority.
- `merged`: roadmap acceptance work is merged but not necessarily released;
- `complete`: acceptance work is merged, released where required, and no
  remaining task is open for this overhaul.

| Phase | Status | Evidence in the working trees | Work still required |
| --- | --- | --- | --- |
| C0 baseline and contract | complete | W0 synthetic fixture directory, compatibility matrix, scalar-field inventory, explicit-zero and missing-value round trips | None for this overhaul |
| E1 portable assessment models | complete | `confidence.py`; node/edge assessment lists; lineage validation; JSON, JSON-LD, and Cytoscape preservation; released in `v0.1.0a2` | None for this overhaul |
| E2 evidence ledger and Bayesian assessment | complete | W1-W3 ledger models, graph-to-ledger conversion/deduplication, ledger-backed posterior output, typed-assessment weighting, explicit-zero preservation | None for this overhaul |
| E3 calibration utilities | complete | W4 Brier/log loss/bins/ECE, eligibility contract, identity candidate-set policy, restricted-dimension guards, separated report blocks | None for this overhaul |
| CITE1 / CG3 CiteGeist migration | complete | W5 dry-run/apply/restore migration CLI; W6 `match_score`, reviewed identity outcomes, calibration rows, deterministic Epistemap-compatible graph export; released in `v0.1.1` | None for this overhaul |
| G1 GroundRecall schema migration | complete | W7 typed assessments, migration contract, ambiguity reporting, legacy-store fixtures; released in `v0.1.0a1` | None for this overhaul |
| G2 GroundRecall producer semantics | complete | W7/W8 producer profile preservation, typed profile fixtures, rule/method provenance; released in `v0.1.0a1` | None for this overhaul |
| G3 reviewer and temporal assessments | complete | W8 governed profiles, reviewer disagreement, temporal applicability, expiry/supersession without destructive forgetting; released in `v0.1.0a1` | None for this overhaul |
| G4 GroundRecall Bayesian integration | complete | W8 Bayesian profile and evidence-ledger integration with current/as-of behavior; released in `v0.1.0a1` | None for this overhaul |
| D1 Didactopus inventory and naming | complete | W10 production inventory, optional ORM/API fields, candidate/citation typed assessments, migration ambiguity report; released in `v0.1.1` | None for this overhaul |
| D2 evidence coverage separation | complete | W11 canonical `evidence_coverage`, deprecated aliases with warnings, duplicate-evidence fixture, stop/export separation; released in `v0.1.1` | None for this overhaul |
| D3 graph and candidate migration | complete | W10 graph/candidate/citation extraction assessments and GroundRecall profile preservation; released in `v0.1.1` | None for this overhaul |
| D4 response calibration | complete | W12 Epistemap calibration reports, selected-answer correctness vs `p_true`, abstention/discrimination/evidence coverage split, minimum-sample warnings; released in `v0.1.1` | None for this overhaul |
| X1 cross-repository release | complete | W13 release tags pushed; installed matrix passed; deprecation clock started on 2026-07-26 | No legacy field removal until a later release plan confirms downstream migration |

## Reconciliation Of Concurrent Changes

### Epistemap detective-corpus work

The concurrent detective-corpus collection, run, review, genealogy, and UI
changes are a separate experimental feature set. Their use of respondent
confidence belongs to response correctness and experimental calibration, so it
does not inherently conflict with the overhaul. The generated graph sidecars
remain legacy fixtures unless they explicitly adopt typed assessments. They
must not be counted as confidence-overhaul fixtures without that review.

### GroundRecall memory lifecycle work

The memory-lifecycle roadmap aligns with the overhaul. It preserves expiry,
supersession, retraction, archival state, provenance, and current
applicability separately from historical confidence. No destructive migration
of stored user data was performed.

### CiteGeist knowledge-graph work

The graph roadmap aligns at the policy level: bibliographic identity, topic
relevance, retrieval rank, and claim support remain separate. W5 added the
dry-run/apply/restore migration command and W6 added canonical `match_score`,
reviewed identity outcomes, calibration rows, and a deterministic
Epistemap-compatible graph exporter. Citation and topic topology are marked as
non-evidential in that export.

Untracked `build/`, generated literature-explorer HTML, and a SQLite backup are
adjacent artifacts, not evidence that CG3 is complete. Publication/private-data
review is required before any generated artifact is committed or published.

### Didactopus learner and bridge work

The course-graph and retrieval changes align with the portable profile, and
the evidence engine now distinguishes evidence mass from mastery confidence.
W10-W12 completed the production inventory, optional ORM/API migration,
candidate and citation extraction assessments, GroundRecall profile
preservation, evidence-coverage aliases/warnings, duplicate-evidence guard, and
response-calibration reports.

## Corrections Made During This Audit

- Reconciled the repository roadmap with the completed W0-W13 status and the
  separately tracked post-release performance work.
- Removed a duplicate `confidence_band()` definition.
- Made calibration JSON output deterministic by sorting keys and ending with a
  newline.
- Corrected Didactopus weighted-evidence and FAQ language to use
  `evidence_coverage`.
- Expanded the Didactopus machine-readable inventory and marked it partial.
- Reconciled CiteGeist's source-expansion reports: Semantic Scholar is
  implemented, the full suite now has a recorded result, and confidence CG3 is
  explicitly separate and partial.
- Added truthful phase-status pointers to the affected repository roadmaps.
- Completed W6 and W10-W12 after the original audit, then updated this status
  file to make W13 the remaining approval-gated release phase at that time.
- Prepared the W13 release-candidate plan with proposed compatibility versions,
  current dependency state, corrected installed-matrix commands, and local
  8-row matrix validation.
- Tagged Epistemap `v0.1.0a2`, CiteGeist `v0.1.1`, GroundRecall `v0.1.0a1`,
  and Didactopus `v0.1.1`; updated consumer Epistemap pins where applicable;
  started the scalar-confidence deprecation clock on 2026-07-26.

## Compatibility Clock

The scalar-confidence deprecation clock started on 2026-07-26. Retain legacy
aliases through the compatibility window and remove no legacy fields until a
later release plan explicitly confirms downstream migration.

Destructive/store-wide migration and publication beyond the reviewed release
artifacts remain human-authorized actions.
