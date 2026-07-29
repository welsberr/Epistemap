from __future__ import annotations

from dataclasses import dataclass

from .models import Edge, GraphBundle, Node


@dataclass(frozen=True)
class GraphIndex:
    edges: tuple[Edge, ...]
    edge_positions: dict[int, int]
    nodes_by_id: dict[str, Node]
    node_positions_by_id: dict[str, tuple[int, ...]]
    node_ids: frozenset[str]
    incoming_by_node: dict[str, tuple[Edge, ...]]
    outgoing_by_node: dict[str, tuple[Edge, ...]]
    incident_by_node: dict[str, tuple[Edge, ...]]
    undirected_neighbors: dict[str, frozenset[str]]
    edges_by_type: dict[str, tuple[Edge, ...]]


def build_graph_index(bundle: GraphBundle) -> GraphIndex:
    nodes_by_id = bundle.node_index()
    node_position_lists: dict[str, list[int]] = {}
    for index, node in enumerate(bundle.nodes):
        node_position_lists.setdefault(node.id, []).append(index)
    node_ids = frozenset(nodes_by_id)
    incoming_lists: dict[str, list[Edge]] = {node_id: [] for node_id in node_ids}
    outgoing_lists: dict[str, list[Edge]] = {node_id: [] for node_id in node_ids}
    incident_lists: dict[str, list[Edge]] = {node_id: [] for node_id in node_ids}
    undirected_neighbors: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
    edges_by_type_lists: dict[str, list[Edge]] = {}

    for edge in bundle.edges:
        edges_by_type_lists.setdefault(edge.type, []).append(edge)
        if edge.source in node_ids:
            outgoing_lists[edge.source].append(edge)
            incident_lists[edge.source].append(edge)
        if edge.target in node_ids:
            incoming_lists[edge.target].append(edge)
            if edge.target != edge.source or edge.source not in node_ids:
                incident_lists[edge.target].append(edge)
        if edge.source in node_ids and edge.target in node_ids:
            undirected_neighbors[edge.source].add(edge.target)
            undirected_neighbors[edge.target].add(edge.source)

    return GraphIndex(
        edges=tuple(bundle.edges),
        edge_positions={id(edge): index for index, edge in enumerate(bundle.edges)},
        nodes_by_id=nodes_by_id,
        node_positions_by_id={node_id: tuple(positions) for node_id, positions in node_position_lists.items()},
        node_ids=node_ids,
        incoming_by_node={node_id: tuple(edges) for node_id, edges in incoming_lists.items()},
        outgoing_by_node={node_id: tuple(edges) for node_id, edges in outgoing_lists.items()},
        incident_by_node={node_id: tuple(edges) for node_id, edges in incident_lists.items()},
        undirected_neighbors={node_id: frozenset(neighbors) for node_id, neighbors in undirected_neighbors.items()},
        edges_by_type={edge_type: tuple(edges) for edge_type, edges in edges_by_type_lists.items()},
    )
