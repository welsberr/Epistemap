from __future__ import annotations

from epistemap import (
    Edge,
    G_ROW_FIELDS,
    GraphBundle,
    Node,
    delta_g,
    g_evaluation_row,
    g_estimate,
    g_rows_to_csv,
    graph_with_component_reliability,
    normalize_g_evaluation_row,
    reliability_level_sensitivity,
    write_g_rows_csv,
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


def test_g_evaluation_row_normalizes_and_preserves_temporal_fields() -> None:
    row = g_evaluation_row(
        y=True,
        p=0.85,
        env="K",
        run_id="run-1",
        subject_id="reader-7",
        condition="kg-assisted",
        item_id="story-3",
        claim_id="claim::alibi",
        recognized_at=42,
        contradiction_available_at=37,
        recognition_lag=5,
        fair_play_rating="available_before_reveal",
        metadata={"genre": "detective"},
    )

    assert row["y"] == 1
    assert row["p"] == 0.85
    assert row["recognition_lag"] == 5
    assert row["fair_play_rating"] == "available_before_reveal"
    assert row["genre"] == "detective"
    assert g_estimate([{"y": 1, "p": 0.9, "env": "C"}, {"y": 0, "p": 0.1, "env": "C"}, row])["n"]["target"] == 1


def test_normalize_g_evaluation_row_accepts_mapping_rows() -> None:
    row = normalize_g_evaluation_row(
        {"y": 0, "p": "0.2", "env": "K", "claim_id": "claim::x", "corpus": "bench"}
    )

    assert row["y"] == 0
    assert row["p"] == 0.2
    assert row["claim_id"] == "claim::x"
    assert row["corpus"] == "bench"


def test_g_rows_to_csv_uses_stable_header_with_extra_fields() -> None:
    rows = [
        g_evaluation_row(y=1, p=0.9, env="C", claim_id="claim::true", metadata={"corpus": "bench"}),
        g_evaluation_row(y=0, p=0.1, env="K", claim_id="claim::false", metadata={"corpus": "bench"}),
    ]

    csv_text = g_rows_to_csv(rows)

    assert csv_text.splitlines()[0].split(",")[: len(G_ROW_FIELDS)] == list(G_ROW_FIELDS)
    assert "corpus" in csv_text.splitlines()[0]
    assert "claim::true" in csv_text


def test_write_g_rows_csv_writes_to_path(tmp_path) -> None:
    destination = tmp_path / "g-rows.csv"

    write_g_rows_csv(
        [g_evaluation_row(y=1, p=0.9, env="K", metadata={"source": "story, chapter 4"})],
        destination,
    )

    assert destination.read_text(encoding="utf-8").startswith("run_id,subject_id,condition")
    assert '"story, chapter 4"' in destination.read_text(encoding="utf-8")


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
