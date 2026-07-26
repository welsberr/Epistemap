# Unified Confidence Overhaul: Audited Implementation Status

**Audit date:** 2026-07-26

**Review state:** W0-W12 implementation PRs merged; W13 release-candidate
planning is prepared for review; Epistemap remains released as `v0.1.0a1`;
consumer compatibility releases and deprecation-clock start remain pending
explicit human approval

**Scope:** Epistemap, CiteGeist, GroundRecall, and Didactopus

## Executive Status

The overhaul is **implementation-complete through W12** and **release-gated at
W13**. The merged repositories contain the portable assessment foundation,
consumer migrations, compatibility aliases, evidence-coverage separation,
response calibration, and installed-matrix checks. The roadmap's definition of
done has not been met because release tagging, consumer compatibility releases,
and deprecation-clock start require explicit human approval.

The dependency-ordered coding-model queue for the remaining work is
[`confidence-overhaul-execution-roadmap.md`](confidence-overhaul-execution-roadmap.md).

Current merged heads after W0-W12:

| Repository | Current merged head | Last confidence-overhaul merge |
| --- | --- | --- |
| Epistemap | `324f9d0` | W9 installed cross-repository matrix |
| CiteGeist | `1ad1721` | W6 identity outcomes and graph export |
| GroundRecall | `cf19ffa` | W8 governed confidence profiles |
| Didactopus | `f10c5bd` | W12 response calibration reports |

These are implementation commits, not release tags. Any statement that the
unified roadmap is fully complete remains too broad until W13 release actions
are authorized and performed.

## Phase Status

Status meanings:

- `substantial`: the central behavior exists locally, with bounded remaining
  acceptance work;
- `partial`: some tasks exist, but one or more defining behaviors are absent;
- `not started`: no roadmap-specific implementation was found;
- `blocked`: implementation depends on an unreleased prerequisite or explicit
  release/migration authority.
- `merged`: roadmap acceptance work is merged, but release tagging may still be
  gated.

| Phase | Status | Evidence in the working trees | Work still required |
| --- | --- | --- | --- |
| C0 baseline and contract | merged | W0 synthetic fixture directory, compatibility matrix, scalar-field inventory, explicit-zero and missing-value round trips | Release note and deprecation clock remain W13-gated |
| E1 portable assessment models | merged | `confidence.py`; node/edge assessment lists; lineage validation; JSON, JSON-LD, and Cytoscape preservation; released in `v0.1.0a1` | Next release tag remains W13-gated |
| E2 evidence ledger and Bayesian assessment | merged | W1-W3 ledger models, graph-to-ledger conversion/deduplication, ledger-backed posterior output, typed-assessment weighting, explicit-zero preservation | Release note and downstream version freeze remain W13-gated |
| E3 calibration utilities | merged | W4 Brier/log loss/bins/ECE, eligibility contract, identity candidate-set policy, restricted-dimension guards, separated report blocks | Release note and downstream version freeze remain W13-gated |
| CITE1 / CG3 CiteGeist migration | merged | W5 dry-run/apply/restore migration CLI; W6 `match_score`, reviewed identity outcomes, calibration rows, deterministic Epistemap-compatible graph export | Consumer release remains W13-gated |
| G1 GroundRecall schema migration | merged | W7 typed assessments, migration contract, ambiguity reporting, legacy-store fixtures | Consumer release remains W13-gated |
| G2 GroundRecall producer semantics | merged | W7/W8 producer profile preservation, typed profile fixtures, rule/method provenance | Consumer release remains W13-gated |
| G3 reviewer and temporal assessments | merged | W8 governed profiles, reviewer disagreement, temporal applicability, expiry/supersession without destructive forgetting | Consumer release remains W13-gated |
| G4 GroundRecall Bayesian integration | merged | W8 Bayesian profile and evidence-ledger integration with current/as-of behavior | Consumer release remains W13-gated |
| D1 Didactopus inventory and naming | merged | W10 production inventory, optional ORM/API fields, candidate/citation typed assessments, migration ambiguity report | Consumer release remains W13-gated |
| D2 evidence coverage separation | merged | W11 canonical `evidence_coverage`, deprecated aliases with warnings, duplicate-evidence fixture, stop/export separation | Consumer release remains W13-gated |
| D3 graph and candidate migration | merged | W10 graph/candidate/citation extraction assessments and GroundRecall profile preservation | Consumer release remains W13-gated |
| D4 response calibration | merged | W12 Epistemap calibration reports, selected-answer correctness vs `p_true`, abstention/discrimination/evidence coverage split, minimum-sample warnings | Consumer release remains W13-gated |
| X1 cross-repository release | blocked | W9 installed matrix merged; W0-W12 implementation PRs merged | Tag consumer compatibility releases and start deprecation only after explicit approval |

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

- Changed the roadmap status from `proposed` to `in progress`.
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
  file to make W13 the remaining approval-gated release phase.
- Prepared the W13 release-candidate plan with proposed compatibility versions,
  current dependency state, corrected installed-matrix commands, and local
  8-row matrix validation.

## Release Gate

Do not start the scalar-confidence deprecation clock yet. The next defensible
sequence is now W13:

1. review [releases/confidence-compatibility-release-plan.md](releases/confidence-compatibility-release-plan.md);
2. approve or revise release versions for Epistemap, CiteGeist, GroundRecall,
   and Didactopus;
3. rerun the installed matrix against the selected release candidates;
4. tag consumer compatibility releases in dependency order;
5. begin the documented deprecation clock for legacy scalar graph confidence.

Destructive/store-wide migration and publication beyond the reviewed release
artifacts remain human-authorized actions.
