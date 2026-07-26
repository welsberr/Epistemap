# Unified Confidence Overhaul: Audited Implementation Status

**Audit date:** 2026-07-25

**Review state:** merged and released as Epistemap `v0.1.0a1`; consumer
compatibility releases remain pending

**Scope:** Epistemap, CiteGeist, GroundRecall, and Didactopus

## Executive Status

The overhaul is **in progress**. The merged repositories contain a released
portable assessment foundation and several partial consumer implementations,
but the roadmap's definition of done has not been met.

The dependency-ordered coding-model queue for the remaining work is
[`confidence-overhaul-execution-roadmap.md`](confidence-overhaul-execution-roadmap.md).

At the start of the audit, all confidence-overhaul changes were uncommitted and
each repository's `main` branch matched its remote-tracking tip. The reviewed
changes have since been committed and pushed on
`agent/reconcile-confidence-and-roadmaps`:

| Repository | Base `main` | Pushed implementation commit |
| --- | --- | --- |
| Epistemap | `f452d4f` | `0b0a579` |
| GroundRecall | `6f98df8` | `7dbe47b` |
| CiteGeist | `40117c5` | `61534cf` |
| Didactopus | `5644c46` | `f321a26` |

These are review-branch implementation commits, not release commits. Earlier
summaries correctly identify many files and passing local tests, but any
statement that the unified roadmap was applied "to completion" remains too
broad.

## Phase Status

Status meanings:

- `substantial`: the central behavior exists locally, with bounded remaining
  acceptance work;
- `partial`: some tasks exist, but one or more defining behaviors are absent;
- `not started`: no roadmap-specific implementation was found;
- `blocked`: implementation depends on an unreleased prerequisite or explicit
  release/migration authority.

| Phase | Status | Evidence in the working trees | Work still required |
| --- | --- | --- | --- |
| C0 baseline and contract | substantial | Roadmap, compatibility tests, explicit-zero and missing-value round trips, W0 synthetic fixture directory, compatibility matrix, and scalar-field inventory | Merge W0, then use the matrix as the gate for W1/W4/W5/W7; installed-package matrix remains X1/W9 work |
| E1 portable assessment models | substantial | `confidence.py`; node/edge assessment lists; lineage validation; JSON, JSON-LD, and Cytoscape preservation; released in `v0.1.0a1` | Fixture matrix, consumer-installed validation, and deprecation diagnostics at public API boundaries |
| E2 evidence ledger and Bayesian assessment | substantial | Bayesian weighting prefers typed edge/source assessments and preserves explicit zero; W1 evidence ledger models, W2 graph-to-ledger conversion/deduplication, and W3 ledger-backed posterior output exist locally | Broader downstream compatibility-alias hardening and installed-package validation |
| E3 calibration utilities | partial | Brier, log loss, bins, ECE, JSON, Markdown, missing-value behavior | Dimension-specific eligibility rules, declared outcome interpretation, identity candidate-set policy, discrimination/coverage separation, broader fixtures |
| CITE1 / CG3 CiteGeist migration | partial | Versioned assessment table; identity assessments in verification output; dry-run-first idempotent migration function; OKF page rendering | CLI command, backup/rollback, portable interval storage, `match_score` alias migration, reviewed match outcomes/calibration, Epistemap graph export |
| G1 GroundRecall schema migration | partial | Optional bounded claim/observation scalars; typed assessment lists; explicit-zero-safe adapter selection; consumes Epistemap `v0.1.0a1` | Store migration command, versioned migration events, ambiguity report, rollback, and legacy-store fixtures |
| G2 GroundRecall producer semantics | partial | Query adapter emits typed compatibility assessments with a declared policy | Per-producer rule/method provenance, basis hashes, adapter fixture coverage, readiness report, removal of blanket legacy reinterpretation |
| G3 reviewer and temporal assessments | partial | Memory roadmap correctly separates expiry/supersession from historical confidence | Append-only identified reviewer records, disagreement/adjudication, query confidence profile, selection explanations |
| G4 GroundRecall Bayesian integration | partial | Existing Epistemap Bayesian sidecar integration predates this audit | Claim evidence ledgers, deduplication, source-family dependence, compatibility aliases, paired current/`as_of` fixtures |
| D1 Didactopus inventory and naming | partial | Machine-readable inventory and some bounded learner-state fields | Complete production occurrence inventory, duplicate-model alignment, optional ORM migration, ambiguity report, JSON/database compatibility tests |
| D2 evidence coverage separation | partial | Canonical `evidence_coverage` name plus legacy property/function aliases; corrected docs | Threshold/report alias migration, deprecation warnings, duplicate-evidence acceptance fixture, compatibility release |
| D3 graph and candidate migration | partial | Course graph emits typed extraction assessments; graph retrieval preserves profiles | Rule-specific extraction versus grounding semantics, candidate migration, mentor prompt changes, GroundRecall bridge fixtures |
| D4 response calibration | partial | Benchmark confidence remains response-correctness probability | Use Epistemap reports, abstention/discrimination/calibration split, minimum-sample policy gates, versioned learner policy manifests |
| X1 cross-repository release | partial | All implementation PRs are merged; Epistemap `v0.1.0a1` is published; GroundRecall and Didactopus consume the tag; both suites pass with the tag installed and no sibling `PYTHONPATH` | Complete the golden cross-repository matrix, release consumers, then begin the deprecation clock |

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
relevance, retrieval rank, and claim support remain separate. The local
confidence module is a CiteGeist-owned canonical-equivalent prototype, but it
does not yet store the portable interval shape and is not connected to the
documented CLI migration or an Epistemap graph exporter.

Untracked `build/`, generated literature-explorer HTML, and a SQLite backup are
adjacent artifacts, not evidence that CG3 is complete. Publication/private-data
review is required before any generated artifact is committed or published.

### Didactopus learner and bridge work

The course-graph and retrieval changes align with the portable profile, and
the evidence engine now distinguishes evidence mass from mastery confidence.
However, Didactopus is pinned to Epistemap commit `f452d4f`, which predates the
new confidence API. Tests using `/home/netuser/bin/Epistemap/src` validate a
sibling working tree, not the declared installed dependency.

The repository also contains duplicate API and vendored GroundRecall models,
ORM scalars, promotion helpers, citation extractors, and adapters that still
use ambiguous defaults or lack method provenance. These are recorded as D1/D3
gaps rather than treated as completed migration.

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

## Release Gate

Do not start the scalar-confidence deprecation clock yet. The next defensible
sequence is:

1. merge C0/W0 fixtures and complete E2's evidence ledger;
2. finish E3 eligibility semantics;
3. implement and test CiteGeist and GroundRecall CLI migrations with rollback;
4. complete Didactopus D1-D4 compatibility work;
5. complete the remaining cross-repository golden fixtures;
6. tag consumer compatibility releases, then begin documented deprecation.

Destructive/store-wide migration and publication beyond the reviewed release
artifacts remain human-authorized actions.
