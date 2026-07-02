from __future__ import annotations

import pytest

from epistemap import Edge, GraphBundle, Node, bridge_nodes, connected_components, cycle_nodes, diagnostics, neighborhood, topological_order


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

