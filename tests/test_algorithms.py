from __future__ import annotations

import pytest

from epistemap import (
    AssessmentValidationPolicy,
    Edge,
    GraphBundle,
    GraphShape,
    Node,
    ProvenanceRef,
    ancestors,
    assessment_validation_markdown,
    bridge_nodes,
    connected_components,
    cycle_nodes,
    descendants,
    diagnostics,
    graph_qa_report,
    k_hop_subgraph,
    neighborhood,
    shortest_path,
    topological_order,
    validate_assessment_readiness,
    validate_shape,
    write_assessment_validation_markdown,
)


def _bundle() -> GraphBundle:
    return GraphBundle(
        graph_id="test",
        nodes=[
            Node(id="concept::a", type="concept", title="A"),
            Node(id="concept::b", type="concept", title="B"),
            Node(id="concept::c", type="concept", title="C"),
            Node(id="concept::d", type="concept", title="D"),
            Node(id="source::s", type="source", title="Source"),
        ],
        edges=[
            Edge(source="concept::a", target="concept::b", type="prerequisite"),
            Edge(source="concept::b", target="concept::c", type="prerequisite"),
            Edge(source="concept::c", target="concept::d", type="prerequisite"),
            Edge(source="source::s", target="concept::a", type="supports"),
        ],
    )


def test_neighborhood_returns_edges_and_adjacent_nodes() -> None:
    payload = neighborhood(_bundle(), "concept::b")
    assert [node.id for node in payload["incoming_nodes"]] == ["concept::a"]
    assert [node.id for node in payload["outgoing_nodes"]] == ["concept::c"]


def test_connected_components_can_filter_node_types() -> None:
    assert connected_components(_bundle(), node_types={"concept"}) == [["concept::a", "concept::b", "concept::c", "concept::d"]]


def test_bridge_nodes_find_articulation_points() -> None:
    payload = bridge_nodes(_bundle(), node_types={"concept"})
    assert [item["node_id"] for item in payload] == ["concept::b", "concept::c"]


def test_topological_order_and_cycle_detection() -> None:
    assert topological_order(_bundle(), edge_types={"prerequisite"}, node_types={"concept"}) == [
        "concept::a",
        "concept::b",
        "concept::c",
        "concept::d",
    ]
    cyclic = _bundle()
    cyclic.edges.append(Edge(source="concept::d", target="concept::a", type="prerequisite"))
    assert cycle_nodes(cyclic, edge_types={"prerequisite"}, node_types={"concept"}) == [
        "concept::a",
        "concept::b",
        "concept::c",
        "concept::d",
    ]
    with pytest.raises(ValueError):
        topological_order(cyclic, edge_types={"prerequisite"}, node_types={"concept"})


def test_diagnostics_summary() -> None:
    payload = diagnostics(_bundle(), node_types={"concept"})
    assert payload["summary"]["node_count"] == 4
    assert payload["summary"]["bridge_node_count"] == 2


def test_closure_shortest_path_and_subgraph() -> None:
    bundle = _bundle()
    assert descendants(bundle, "concept::a", edge_types={"prerequisite"}) == [
        "concept::b",
        "concept::c",
        "concept::d",
    ]
    assert ancestors(bundle, "concept::d", edge_types={"prerequisite"}) == [
        "concept::a",
        "concept::b",
        "concept::c",
    ]
    assert shortest_path(bundle, "concept::a", "concept::d", edge_types={"prerequisite"}) == [
        "concept::a",
        "concept::b",
        "concept::c",
        "concept::d",
    ]
    subgraph = k_hop_subgraph(bundle, ["concept::b"], hops=1)
    assert {node.id for node in subgraph.nodes} == {"concept::a", "concept::b", "concept::c"}


def test_graph_qa_and_shape_validation() -> None:
    bundle = _bundle()
    bundle.edges.append(Edge(source="concept::a", target="concept::missing", type="prerequisite"))
    report = graph_qa_report(bundle)
    assert report["summary"]["missing_endpoint_count"] == 1
    validation = validate_shape(
        bundle,
        GraphShape(
            required_node_fields={"concept": {"title"}},
            required_edge_fields={"prerequisite": {"justification"}},
            acyclic_edge_types={"prerequisite"},
        ),
    )
    assert validation["summary"]["error_count"] >= 1


def test_assessment_validation_passes_auditable_graph(tmp_path) -> None:
    bundle = GraphBundle(
        graph_id="auditable",
        metadata={
            "bayesian_assessment_report": {"summary": {"node_count": 1}},
            "assessment_policy": {
                "bayesian_prior_profile": "neutral",
                "evidence_weighting_policy": "confidence_weighted_edges",
                "graph_extraction_policy": "one_hop_claim_neighborhood",
            },
        },
        nodes=[
            Node(id="claim::a", type="claim", title="Auditable claim"),
            Node(id="source::s", type="source", title="Reviewed source", metadata={"available_at": "2026-01-01"}),
        ],
        edges=[
            Edge(
                source="source::s",
                target="claim::a",
                type="supports",
                confidence=0.9,
                provenance=[ProvenanceRef(source_id="source::s", grounding_status="grounded")],
                metadata={"available_at": "2026-01-01"},
            )
        ],
    )

    report = validate_assessment_readiness(bundle)
    markdown = assessment_validation_markdown(report)
    destination = tmp_path / "assessment-validation.md"
    write_assessment_validation_markdown(report, destination)

    assert report["report_kind"] == "epistemap_assessment_validation_report"
    assert report["summary"]["status"] == "pass"
    assert report["findings"] == []
    assert "No validation findings" in markdown
    assert destination.read_text(encoding="utf-8") == markdown


def test_assessment_validation_surfaces_auditability_findings() -> None:
    bundle = GraphBundle(
        metadata={"bayesian_assessment_report": {"summary": {"node_count": 1}}},
        nodes=[
            Node(id="claim::a", type="claim", confidence=1.5),
            Node(id="source::s", type="source", title="Source"),
        ],
        edges=[
            Edge(source="source::s", target="claim::a", type="supports", confidence=1.2),
            Edge(source="source::s", target="claim::missing", type="contradicts"),
        ],
    )

    report = validate_assessment_readiness(bundle)
    codes = {finding["code"] for finding in report["findings"]}

    assert report["summary"]["status"] == "error"
    assert "missing_graph_id" in codes
    assert "missing_node_title" in codes
    assert "invalid_node_confidence" in codes
    assert "invalid_edge_confidence" in codes
    assert "missing_edge_endpoint" in codes
    assert "missing_evidence_provenance" in codes
    assert "missing_bayesian_policy_metadata" in codes


def test_assessment_validation_policy_can_require_grounding_status() -> None:
    bundle = GraphBundle(
        graph_id="grounding-policy",
        nodes=[
            Node(id="claim::a", type="claim", title="Claim"),
            Node(id="source::s", type="source", title="Source"),
        ],
        edges=[Edge(source="source::s", target="claim::a", type="supports", evidence_ids=["source::s"])],
    )

    report = validate_assessment_readiness(
        bundle,
        AssessmentValidationPolicy(require_grounding_for_evidence=True),
    )

    assert "missing_evidence_grounding_status" in {finding["code"] for finding in report["findings"]}
