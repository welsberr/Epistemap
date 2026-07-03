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
                metadata={
                    "source_roles": ["argumentation"],
                    "source_quality": "low",
                    "source_stance": "manufactured_doubt",
                },
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
    assert summary["source_quality_summary"]["low"] == 1
    assert summary["source_stance_summary"]["manufactured_doubt"] == 1
    assert "low_trust_source_signal" in summary["flags"]
    assert "adversarial_source_signal" in summary["flags"]
    assert summary["reliability"]["band"] in {"weak", "moderate", "strong"}
    assert "challenge_penalty" in summary["reliability"]["components"]
    assert summary["reliability"]["components"]["source_quality"] < 1
    assert summary["reliability"]["components"]["adversarial_penalty"] > 0
    assert summary["bayesian_reliability"]["model"] == "beta_binomial_weighted_evidence"
    assert summary["bayesian_reliability"]["posterior"]["mean"] > 0.5
    assert summary["bayesian_reliability"]["prior_sensitivity"]["mean_range"] > 0


def test_epistemic_report_counts_flags() -> None:
    report = epistemic_report(_bundle())
    assert report["summary"]["node_count"] == 3
    assert report["summary"]["flag_counts"]["challenged"] >= 1
    assert report["summary"]["reliability_bands"]
