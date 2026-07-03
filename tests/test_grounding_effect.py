from __future__ import annotations

from epistemap import (
    Edge,
    GraphBundle,
    Node,
    delta_g,
    g_estimate,
    graph_with_component_reliability,
    reliability_level_sensitivity,
)


def _rows(*, target_confidence: float) -> list[dict]:
    return [
        {"y": 1, "p": 0.9, "env": "C"},
        {"y": 0, "p": 0.1, "env": "C"},
        {"y": 1, "p": target_confidence, "env": "K"},
        {"y": 0, "p": 1.0 - target_confidence, "env": "K"},
    ]


def test_g_estimate_combines_truth_tracking_discrimination_and_robustness() -> None:
    grounded = g_estimate(_rows(target_confidence=0.9))
    uncalibrated = g_estimate(_rows(target_confidence=0.5))

    assert grounded["G"] > uncalibrated["G"]
    assert grounded["components"]["S_T"]["point"] > uncalibrated["components"]["S_T"]["point"]
    assert grounded["components"]["S_D"]["point"] == 1.0
    assert grounded["components"]["S_R"]["point"] == 1.0


def test_g_estimate_accepts_one_shot_iterables() -> None:
    rows = (row for row in _rows(target_confidence=0.9))

    estimate = g_estimate(rows)

    assert estimate["n"] == {"clean": 2, "target": 2}
    assert estimate["G"] > 0


def test_delta_g_reports_normalized_gain() -> None:
    effect = delta_g(_rows(target_confidence=0.5), _rows(target_confidence=0.9))

    assert effect["delta_G"] > 0
    assert effect["normalized_delta_G"] > 0
    assert effect["before"]["G"] < effect["after"]["G"]


def test_reliability_level_sensitivity_is_counterfactual_not_verdict() -> None:
    sensitivity = reliability_level_sensitivity(
        {
            "low": _rows(target_confidence=0.55),
            "high": _rows(target_confidence=0.9),
        },
        baseline_level="low",
    )

    assert sensitivity["baseline_level"] == "low"
    assert sensitivity["effects"]["high"]["delta_from_baseline"] > 0
    assert "not a truth score" in sensitivity["interpretation"]


def test_graph_with_component_reliability_sets_counterfactual_metadata_on_copy() -> None:
    bundle = GraphBundle(
        nodes=[Node(id="claim::a", type="claim"), Node(id="source::s", type="source")],
        edges=[Edge(id="edge::support", source="source::s", target="claim::a", type="supports")],
    )

    changed_node = graph_with_component_reliability(bundle, "claim::a", "low")
    changed_edge = graph_with_component_reliability(bundle, "edge::support", 0.25)

    assert bundle.nodes[0].metadata == {}
    assert changed_node.nodes[0].metadata["counterfactual_reliability"] == "low"
    assert changed_edge.edges[0].metadata["counterfactual_reliability"] == 0.25
    assert changed_edge.metadata["counterfactuals"][0]["component_found"] is True
