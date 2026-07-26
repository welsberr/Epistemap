# Confidence Compatibility Release Plan

Status: prepared for W13 review. Do not tag, publish, or merge release
artifacts until the release versions and timing are explicitly approved.

## Proposed release order

1. Epistemap: tag a compatibility release after rerunning the installed matrix.
2. CiteGeist: update dependency notes against the approved Epistemap release
   and tag a consumer compatibility release.
3. GroundRecall: update dependency notes against the approved Epistemap release
   and tag a consumer compatibility release.
4. Didactopus: update dependency notes after CiteGeist/GroundRecall are
   available and tag a consumer compatibility release.
5. Start the legacy scalar graph-confidence deprecation clock only after the
   above tags exist.

## Release validation required before tags

- Run every repository's full test suite from a clean checkout.
- Run Epistemap's installed cross-repository matrix against the selected tagged
  or release-candidate versions.
- Confirm CiteGeist and GroundRecall migrations remain dry-run-first,
  idempotent, and restorable from documented backups.
- Confirm Didactopus JSON/database round trips still preserve missing versus
  explicit zero confidence.
- Confirm generated public artifacts exclude private stores, backups, run logs,
  human participant results, and local-only databases.

## Compatibility aliases and replacements

| Repository | Legacy alias | Replacement | Release behavior |
| --- | --- | --- | --- |
| Epistemap | legacy scalar node/edge `confidence` | typed `ConfidenceAssessment` with explicit dimension and method | Readable through compatibility window; do not infer dimension without policy. |
| Epistemap | old Bayesian report keys | ledger-backed posterior/evidence report blocks | Preserve aliases for compatibility consumers. |
| CiteGeist | `VerificationResult.confidence` | `VerificationResult.match_score` | Constructor/property compatibility emits `DeprecationWarning`. |
| CiteGeist | `VerificationResult.to_dict()["confidence"]` | `match_score` plus `assessments[].dimension == "identity_resolution"` | Keep serialized alias for one compatibility release. |
| CiteGeist | legacy `field_provenance.confidence` | `extraction_fidelity` assessment | Migrated by dry-run/apply CLI; original column retained. |
| CiteGeist | legacy `relation_provenance.confidence` | `extraction_fidelity` assessment on relation provenance | Migrated by dry-run/apply CLI; relation topology remains non-evidential. |
| CiteGeist | legacy `entry_topics.confidence` | topic-membership assessment / topic relevance context | Migrated by dry-run/apply CLI; topic topology remains non-evidential. |
| GroundRecall | claim/observation `confidence_hint` | typed extraction/profile assessments | Store migration preserves explicit zero and reports ambiguous legacy defaults. |
| GroundRecall | review scalar confidence | reviewer endorsement profile and disagreement/adjudication records | Retain compatibility fields through release window. |
| Didactopus | `KnowledgeCandidateCreate.confidence_hint` | `confidence_assessments[]` with `extraction_fidelity` | Alias retained; migration reports ambiguous zero defaults. |
| Didactopus | citation `confidence_hint` | citation `extraction_fidelity` assessments | Alias retained for draft artifact compatibility. |
| Didactopus | `ConceptEvidenceSummary.confidence` | `evidence_coverage` | Property compatibility emits `DeprecationWarning`. |
| Didactopus | `confidence_from_weight()` | `evidence_coverage_from_weight()` | Function compatibility emits `DeprecationWarning`. |
| Didactopus | `confidence_threshold` | `evidence_coverage_threshold` | API/config compatibility emits `DeprecationWarning`. |
| Didactopus | `min_confidence` / `low_confidence_threshold` | `min_evidence_coverage` / `low_evidence_coverage_threshold` | API compatibility emits `DeprecationWarning`. |
| Didactopus | `StopCriteria.min_average_confidence` | `min_average_evidence_coverage` | Constructor/property compatibility emits `DeprecationWarning`. |
| Didactopus | `decay_confidence()` | `decay_evidence_coverage()` | Function compatibility emits `DeprecationWarning`. |

## Unresolved ambiguous legacy data

- Epistemap scalar graph `confidence` without an explicit mapping policy remains
  ambiguous and must not be rewritten into typed assessments automatically.
- CiteGeist support-gap priority fields such as
  `claim_support.needs_support_score` are not confidence and are intentionally
  excluded from migration.
- CiteGeist query-scoped retrieval scores such as expansion relevance are not
  durable confidence and are intentionally excluded from migration.
- GroundRecall legacy zero values may mean either explicit zero confidence or a
  default/missing value; migration reports must preserve that ambiguity.
- Didactopus legacy `0.0` candidate confidence hints in SQLite may mean either
  explicit zero or missing/defaulted confidence; the migration reports
  `legacy_zero_ambiguous` and does not auto-convert those rows.

## Deprecation clock proposal

Start date: not started.

Proposed rule after approval: retain every listed alias for one compatibility
release, emit warnings naming replacements, and remove no legacy fields until a
subsequent release plan explicitly confirms downstream consumers have migrated.
