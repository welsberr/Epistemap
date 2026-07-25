# Unified Confidence Overhaul: Audited Implementation Status

**Audit date:** 2026-07-25

**Review state:** reviewed against local source and tests; not released

**Scope:** Epistemap, CiteGeist, GroundRecall, and Didactopus

## Executive Status

The overhaul is **in progress**. The local working trees contain a useful
portable assessment foundation and several consumer prototypes, but the
roadmap's definition of done has not been met.

All confidence-overhaul changes remain uncommitted. At audit time each
repository's `main` branch matched its remote-tracking tip:

| Repository | Audited `HEAD` | Confidence work in history? |
| --- | --- | --- |
| Epistemap | `f452d4f` | No; working tree only |
| GroundRecall | `6f98df8` | No; working tree only |
| CiteGeist | `40117c5` | No; working tree only |
| Didactopus | `5644c46` | No; working tree only |

Consequently, earlier implementation summaries are prototype reports rather
than release reports. They correctly identify many files and passing local
tests, but any statement that the unified roadmap was applied "to completion"
is too broad.

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
| C0 baseline and contract | partial | Roadmap, compatibility tests, explicit-zero and missing-value round trips | Cross-repository fixture directory, full semantic inventory, and recorded installed baseline |
| E1 portable assessment models | substantial | `confidence.py`; node/edge assessment lists; lineage validation; JSON, JSON-LD, and Cytoscape preservation | Tagged Epistemap release, fixture matrix, consumer-installed validation, and deprecation diagnostics at public API boundaries |
| E2 evidence ledger and Bayesian assessment | partial | Bayesian weighting prefers typed edge/source assessments and preserves explicit zero | `EvidenceUnit`, weighting-policy model, visible ledger, deterministic deduplication, source-family handling, revision-edge separation, reconstructable assessment output |
| E3 calibration utilities | partial | Brier, log loss, bins, ECE, JSON, Markdown, missing-value behavior | Dimension-specific eligibility rules, declared outcome interpretation, identity candidate-set policy, discrimination/coverage separation, broader fixtures |
| CITE1 / CG3 CiteGeist migration | partial | Versioned assessment table; identity assessments in verification output; dry-run-first idempotent migration function; OKF page rendering | CLI command, backup/rollback, portable interval storage, `match_score` alias migration, reviewed match outcomes/calibration, Epistemap graph export |
| G1 GroundRecall schema migration | partial | Optional bounded claim/observation scalars; typed assessment lists; explicit-zero-safe adapter selection | Store migration command, versioned migration events, ambiguity report, rollback, legacy-store fixtures, released Epistemap dependency |
| G2 GroundRecall producer semantics | partial | Query adapter emits typed compatibility assessments with a declared policy | Per-producer rule/method provenance, basis hashes, adapter fixture coverage, readiness report, removal of blanket legacy reinterpretation |
| G3 reviewer and temporal assessments | partial | Memory roadmap correctly separates expiry/supersession from historical confidence | Append-only identified reviewer records, disagreement/adjudication, query confidence profile, selection explanations |
| G4 GroundRecall Bayesian integration | partial | Existing Epistemap Bayesian sidecar integration predates this audit | Claim evidence ledgers, deduplication, source-family dependence, compatibility aliases, paired current/`as_of` fixtures |
| D1 Didactopus inventory and naming | partial | Machine-readable inventory and some bounded learner-state fields | Complete production occurrence inventory, duplicate-model alignment, optional ORM migration, ambiguity report, JSON/database compatibility tests |
| D2 evidence coverage separation | partial | Canonical `evidence_coverage` name plus legacy property/function aliases; corrected docs | Threshold/report alias migration, deprecation warnings, duplicate-evidence acceptance fixture, compatibility release |
| D3 graph and candidate migration | partial | Course graph emits typed extraction assessments; graph retrieval preserves profiles | Rule-specific extraction versus grounding semantics, candidate migration, mentor prompt changes, GroundRecall bridge fixtures |
| D4 response calibration | partial | Benchmark confidence remains response-correctness probability | Use Epistemap reports, abstention/discrimination/calibration split, minimum-sample policy gates, versioned learner policy manifests |
| X1 cross-repository release | blocked | Local suites can use sibling source trees | Commit/review phases, tag Epistemap, update consumer dependencies, clean installed-package matrix, consumer releases, then begin deprecation clock |

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

1. complete C0 fixtures and E2's evidence ledger;
2. finish E3 eligibility semantics;
3. implement and test CiteGeist and GroundRecall CLI migrations with rollback;
4. complete Didactopus D1-D4 compatibility work;
5. commit and review the scoped changes separately from concurrent feature
   work;
6. tag Epistemap and update consumer dependency declarations;
7. run the cross-repository matrix in clean environments without sibling
   `PYTHONPATH`;
8. tag consumer compatibility releases, then begin documented deprecation.

Release tagging, destructive/store-wide migration, and publication remain
human-authorized actions.
