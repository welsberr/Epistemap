from __future__ import annotations

from epistemap import (
    Edge,
    GraphBundle,
    Node,
    availability_lag,
    claim_status_at,
    evidence_available_at,
    first_contradiction_time,
    graph_at,
    stale_claims_after,
    tenability_window,
    timeline_events,
)


def _scholarship_bundle() -> GraphBundle:
    return GraphBundle(
        graph_id="timeline",
        nodes=[
            Node(
                id="claim::old",
                type="claim",
                title="Old tenable claim",
                status="promoted",
                metadata={"introduced_at": "1900-01-01"},
            ),
            Node(
                id="evidence::early",
                type="evidence",
                title="Early support",
                metadata={"available_at": "1901-01-01"},
            ),
            Node(
                id="evidence::decisive",
                type="evidence",
                title="Decisive later evidence",
                metadata={"available_at": "1953-04-25"},
            ),
        ],
        edges=[
            Edge(
                id="edge::support",
                source="evidence::early",
                target="claim::old",
                type="supports",
                metadata={"available_at": "1901-01-01"},
            ),
            Edge(
                id="edge::contradicts",
                source="evidence::decisive",
                target="claim::old",
                type="contradicts",
                metadata={"available_at": "1953-04-25"},
            ),
        ],
    )


def _detective_bundle() -> GraphBundle:
    return GraphBundle(
        graph_id="detective",
        nodes=[
            Node(id="claim::alibi", type="claim", title="The alibi is true", metadata={"timestep": 1}),
            Node(id="clue::ticket", type="evidence", title="Ticket timestamp", metadata={"timestep": 2}),
            Node(id="clue::clock", type="evidence", title="Clock contradiction", metadata={"timestep": 7}),
        ],
        edges=[
            Edge(source="clue::ticket", target="claim::alibi", type="supports", metadata={"timestep": 2}),
            Edge(source="clue::clock", target="claim::alibi", type="contradicts", metadata={"timestep": 7}),
        ],
    )


def test_graph_at_slices_by_available_date() -> None:
    early = graph_at(_scholarship_bundle(), "1902-01-01")

    assert {node.id for node in early.nodes} == {"claim::old", "evidence::early"}
    assert [edge.id for edge in early.edges] == ["edge::support"]


def test_claim_status_changes_when_contradiction_becomes_available() -> None:
    bundle = _scholarship_bundle()

    assert claim_status_at(bundle, "claim::old", "1902-01-01")["status"] == "supported"
    assert claim_status_at(bundle, "claim::old", "1954-01-01")["status"] == "contradicted"
    assert first_contradiction_time(bundle, "claim::old")["time"] == "1953-04-25"


def test_tenability_and_stale_claims_after_public_evidence() -> None:
    bundle = _scholarship_bundle()
    window = tenability_window(bundle, "claim::old")

    assert window["introduced_at"] == "1900-01-01"
    assert window["tenable_until"] == "1953-04-25"
    assert stale_claims_after(bundle, "1954-01-01")[0]["claim_id"] == "claim::old"


def test_detective_story_numeric_timesteps_support_recognition_lag() -> None:
    bundle = _detective_bundle()

    assert evidence_available_at(bundle, "claim::alibi", 3)["summary"]["challenge_count"] == 0
    assert evidence_available_at(bundle, "claim::alibi", 7)["summary"]["challenge_count"] == 1
    assert first_contradiction_time(bundle, "claim::alibi")["time"] == "7"
    assert availability_lag(1, 7, 9)["post_contradiction_persistence"] == 2.0


def test_timeline_events_are_sorted_and_keep_original_labels() -> None:
    events = timeline_events(_scholarship_bundle())

    assert [event["time"] for event in events[:2]] == ["1900-01-01", "1901-01-01"]
    assert events[-1]["time"] == "1953-04-25"
