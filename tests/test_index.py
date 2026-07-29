from __future__ import annotations

from epistemap import Edge, GraphBundle, Node
from epistemap.index import build_graph_index


def test_graph_index_handles_empty_graph() -> None:
    index = build_graph_index(GraphBundle())
    assert index.node_ids == frozenset()
    assert index.incoming_by_node == {}
    assert index.outgoing_by_node == {}
    assert index.incident_by_node == {}
    assert index.undirected_neighbors == {}


def test_graph_index_preserves_edge_order_and_neighbors() -> None:
    bundle = GraphBundle(
        nodes=[
            Node(id="a", type="concept"),
            Node(id="b", type="concept"),
            Node(id="c", type="concept"),
        ],
        edges=[
            Edge(source="a", target="b", type="supports"),
            Edge(source="c", target="b", type="supports"),
            Edge(source="b", target="b", type="qualifies"),
            Edge(source="b", target="a", type="supports"),
        ],
    )

    index = build_graph_index(bundle)

    assert [edge.source for edge in index.incoming_by_node["b"]] == ["a", "c", "b"]
    assert [edge.target for edge in index.outgoing_by_node["b"]] == ["b", "a"]
    assert [edge.type for edge in index.incident_by_node["b"]] == ["supports", "supports", "qualifies", "supports"]
    assert index.undirected_neighbors["b"] == frozenset({"a", "b", "c"})
    assert [edge.type for edge in index.edges_by_type["supports"]] == ["supports", "supports", "supports"]


def test_graph_index_ignores_missing_endpoints_in_adjacency() -> None:
    bundle = GraphBundle(
        nodes=[Node(id="a", type="concept"), Node(id="b", type="concept")],
        edges=[
            Edge(source="missing", target="a", type="supports"),
            Edge(source="a", target="missing", type="supports"),
            Edge(source="a", target="b", type="supports"),
        ],
    )

    index = build_graph_index(bundle)

    assert [edge.source for edge in index.incoming_by_node["a"]] == ["missing"]
    assert [edge.target for edge in index.outgoing_by_node["a"]] == ["missing", "b"]
    assert index.undirected_neighbors["a"] == frozenset({"b"})
    assert index.undirected_neighbors["b"] == frozenset({"a"})


def test_graph_index_uses_last_duplicate_node_id_consistently() -> None:
    bundle = GraphBundle(
        nodes=[
            Node(id="dup", type="concept", title="first"),
            Node(id="dup", type="claim", title="second"),
        ],
        edges=[Edge(source="dup", target="dup", type="supports")],
    )

    index = build_graph_index(bundle)

    assert index.nodes_by_id["dup"].type == "claim"
    assert index.node_ids == frozenset({"dup"})
    assert len(index.incoming_by_node["dup"]) == 1
    assert len(index.outgoing_by_node["dup"]) == 1
