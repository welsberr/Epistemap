from __future__ import annotations

from epistemap import Edge, GraphBundle, Node, ProvenanceRef, epistemic_report, epistemic_summary


def _bundle() -> GraphBundle:
    return GraphBundle(
        graph_id="science-claim",
        nodes=[
            Node(id="concept::climate", type="concept", title="Climate Change"),
            Node(
                id="claim::main",
                type="claim",
                title="Main claim",
                confidence=0.9,
                provenance=[ProvenanceRef(grounding_status="grounded")],
                metadata={"source_roles": ["mechanism", "overview"]},
            ),
            Node(
                id="claim::denial",
                type="claim",
                title="Denialist counterclaim",
                confidence=0.2,
                provenance=[ProvenanceRef(grounding_status="ungrounded")],
                metadata={"source_roles": ["argumentation"]},
            ),
            Node(
                id="obs::paper",
                type="observation",
                title="Peer-reviewed support",
                status="grounded",
                metadata={"source_role": "mechanism"},
            ),
        ],
        edges=[
            Edge(source="claim::main", target="concept::climate", type="about_concept"),
            Edge(source="obs::paper", target="claim::main", type="supports_claim"),
            Edge(source="claim::denial", target="claim::main", type="contradicts"),
        ],
    )


def test_epistemic_summary_surfaces_support_challenge_and_grounding() -> None:
    summary = epistemic_summary(_bundle(), "concept::climate")
    assert summary["summary"]["direct_support_count"] == 2
    assert summary["summary"]["challenge_count"] == 1
    assert "challenged" in summary["flags"]
    assert summary["source_role_summary"]["mechanism"] == 2


def test_epistemic_report_counts_flags() -> None:
    report = epistemic_report(_bundle())
    assert report["summary"]["node_count"] == 3
    assert report["summary"]["flag_counts"]["challenged"] >= 1
