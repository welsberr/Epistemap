# Confidence Compatibility Matrix

Status: W0 contract fixture baseline.

These fixtures are synthetic. They are not exports from user stores and do not
contain private run data. Raw producer payloads live in
`tests/fixtures/confidence/raw/`; expected normalized Epistemap payloads live in
`tests/fixtures/confidence/expected/`.

| Fixture ID | Producer | Source schema | Case | Expected disposition |
| --- | --- | --- | --- | --- |
| `epistemap_legacy_missing` | Epistemap | `epistemap_graph_bundle.v1` | Legacy missing confidence | Preserve missing as absent/`None`; do not coerce to zero. |
| `epistemap_legacy_explicit_zero` | Epistemap | `epistemap_graph_bundle.v1` | Legacy explicit zero | Preserve `0.0` on node and edge. |
| `epistemap_legacy_ordinary_value` | Epistemap | `epistemap_graph_bundle.v1` | Legacy ordinary scalar | Preserve legacy scalar without assigning a dimension. |
| `citegeist_typed_only` | CiteGeist | `citegeist.confidence_assessments.v1` | Typed assessment only | Preserve identity-resolution dimension and method metadata. |
| `groundrecall_typed_and_legacy` | GroundRecall | `groundrecall_query_epistemap.v1` | Typed plus legacy with mapping | Preserve typed reviewer endorsement and legacy compatibility value. |
| `citegeist_namespaced_extension` | CiteGeist | `citegeist.confidence_assessments.v1` | Namespaced extension dimension | Accept `citegeist:topic_relevance` without treating it as portable truth. |
| `groundrecall_superseded_lineage` | GroundRecall | `groundrecall_query_epistemap.v1` | Superseded lineage | Preserve old and new assessments; active helper should select the new one. |
| `didactopus_ambiguous_legacy_mapping` | Didactopus | `didactopus.course_graph.v1` | Ambiguous legacy mapping | Validate payload but emit readiness warning until a mapping policy is declared. |
| `epistemap_deduplicated_graph_edges` | Epistemap | `epistemap_graph_bundle.v1` | Duplicate graph evidence | Preserve raw graph edges; W2 ledger conversion deduplicates repeated artifact fragments separately. |

## Coverage Rules

- Each matrix row must have one raw fixture and one expected normalized fixture.
- Fixture IDs must match raw payload `metadata.fixture_id`.
- Missing legacy confidence must remain absent after normalization.
- Explicit zero must remain `0.0` after normalization.
- Legacy scalar values must not be converted into typed assessments unless the
  fixture declares a mapping policy.
- Namespaced dimensions are allowed; unnamespaced unknown dimensions remain
  invalid.
