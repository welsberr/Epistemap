# Confidence Compatibility Release Plan

Status: completed on 2026-07-26 after explicit approval. Compatibility release
tags exist for all four repositories; no package-index publication was
performed.

## Completed release order

1. Epistemap `v0.1.0a2`: tagged after rerunning the installed matrix.
2. CiteGeist `v0.1.1`: tagged as a consumer compatibility release.
3. GroundRecall `v0.1.0a1`: dependency pin updated to Epistemap `v0.1.0a2`
   and tagged as a consumer compatibility release.
4. Didactopus `v0.1.1`: dependency pin updated to Epistemap `v0.1.0a2` and
   tagged as a consumer compatibility release.
5. Legacy scalar graph-confidence deprecation clock started on 2026-07-26.

## Released compatibility versions

These tags were pushed on 2026-07-26.

| Repository | Previous version | Compatibility version | Reason |
| --- | ---: | ---: | --- |
| Epistemap | `0.1.0a1` | `0.1.0a2` | Alpha compatibility update to the shared assessment, ledger, calibration, and installed-matrix contract. |
| GroundRecall | `0.1.0a0` | `0.1.0a1` | Alpha consumer compatibility update over the Epistemap `0.1.0a2` contract. |
| CiteGeist | `0.1.0` | `0.1.1` | Patch/minor-compatible bibliography workbench update; keeps SQLite schema additive and public aliases intact. |
| Didactopus | `0.1.0` | `0.1.1` | Patch/minor-compatible learner-workflow update; keeps API aliases and migration compatibility intact. |

## Release validation performed before tags

- Run every repository's full test suite from a clean checkout.
- Run Epistemap's installed cross-repository matrix against the selected tagged
  or release-candidate versions.
- Confirm CiteGeist and GroundRecall migrations remain dry-run-first,
  idempotent, and restorable from documented backups.
- Confirm Didactopus JSON/database round trips still preserve missing versus
  explicit zero confidence.
- Confirm generated public artifacts exclude private stores, backups, run logs,
  human participant results, and local-only databases.

### Validation commands

Run from clean checkouts with no sibling `PYTHONPATH` unless explicitly noted:

```bash
cd /home/netuser/bin/Epistemap
python -m pytest -q
python -m epistemap.cli installed-matrix --dry-run --out /tmp/epistemap-installed-matrix-dry-run.json
python -m epistemap.cli installed-matrix --out /tmp/epistemap-installed-matrix-report.json

cd /home/netuser/bin/CiteGeist
.venv/bin/python -m pytest -q

cd /home/netuser/bin/GroundRecall
python -m pytest -q

cd /home/netuser/bin/Didactopus
pytest -q
```

W13 release checks on 2026-07-26:

- Epistemap `python -m pytest -q`: 156 passed.
- `python -m epistemap.cli installed-matrix --dry-run --out /tmp/epistemap-installed-matrix-dry-run.json`
  generated all 8 planned matrix rows. Dry-run rows are reported as
  `status: dry_run`, so the report's aggregate `passed` value is not treated as
  a release pass.
- `python -m epistemap.cli installed-matrix --out /tmp/epistemap-installed-matrix-report.json`
  passed all 8 installed cross-repository matrix rows.
- CiteGeist `.venv/bin/python -m pytest -q`: 295 passed, 5 skipped, 13
  expected deprecation warnings.
- GroundRecall `python -m pytest -q`: 126 passed.
- Didactopus `pytest -q`: 288 passed.

### Released dependency state

- Epistemap has compatibility tag `v0.1.0a2`.
- GroundRecall currently depends on
  `epistemap @ git+https://github.com/welsberr/Epistemap.git@v0.1.0a2`.
- Didactopus currently depends on
  `epistemap @ git+https://github.com/welsberr/Epistemap.git@v0.1.0a2`.
- CiteGeist currently has no runtime Epistemap dependency; its
  Epistemap-compatible graph profile is a deterministic JSON projection.

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

## Deprecation clock

Start date: 2026-07-26.

Rule: retain every listed alias for one compatibility release, emit warnings
naming replacements, and remove no legacy fields until a subsequent release plan
explicitly confirms downstream consumers have migrated.
