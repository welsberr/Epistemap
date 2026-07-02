from __future__ import annotations

from collections import defaultdict, deque
from typing import Iterable

from .models import Edge, GraphBundle, Node


def incoming_edges(bundle: GraphBundle, node_id: str, edge_types: set[str] | None = None) -> list[Edge]:
    return [
        edge
        for edge in bundle.edges
        if edge.target == node_id and (edge_types is None or edge.type in edge_types)
    ]


def outgoing_edges(bundle: GraphBundle, node_id: str, edge_types: set[str] | None = None) -> list[Edge]:
    return [
        edge
        for edge in bundle.edges
        if edge.source == node_id and (edge_types is None or edge.type in edge_types)
    ]


def neighborhood(bundle: GraphBundle, node_id: str, edge_types: set[str] | None = None) -> dict:
    nodes = bundle.node_index()
    incoming = incoming_edges(bundle, node_id, edge_types=edge_types)
    outgoing = outgoing_edges(bundle, node_id, edge_types=edge_types)
    return {
        "node": nodes.get(node_id),
        "incoming": incoming,
        "outgoing": outgoing,
        "incoming_nodes": [nodes[edge.source] for edge in incoming if edge.source in nodes],
        "outgoing_nodes": [nodes[edge.target] for edge in outgoing if edge.target in nodes],
    }


def connected_components(bundle: GraphBundle, node_types: set[str] | None = None) -> list[list[str]]:
    node_ids = _filtered_node_ids(bundle, node_types)
    adjacency = _undirected_adjacency(bundle, node_ids)
    remaining = set(node_ids)
    components: list[list[str]] = []
    while remaining:
        start = remaining.pop()
        stack = [start]
        component = {start}
        while stack:
            node = stack.pop()
            for neighbor in adjacency[node]:
                if neighbor in component:
                    continue
                component.add(neighbor)
                remaining.discard(neighbor)
                stack.append(neighbor)
        components.append(sorted(component))
    return sorted(components, key=lambda item: (-len(item), item))


def bridge_nodes(bundle: GraphBundle, node_types: set[str] | None = None) -> list[dict]:
    node_ids = _filtered_node_ids(bundle, node_types)
    adjacency = _undirected_adjacency(bundle, node_ids)
    payloads: list[dict] = []
    for component in connected_components(bundle, node_types=node_types):
        if len(component) < 3:
            continue
        component_set = set(component)
        for candidate in component:
            remaining = component_set - {candidate}
            start = next(iter(remaining))
            visited = _walk(start, adjacency, blocked=candidate, allowed=remaining)
            if len(visited) != len(remaining):
                payloads.append(
                    {
                        "node_id": candidate,
                        "component_size": len(component),
                        "reachable_after_removal": len(visited),
                    }
                )
    return sorted(payloads, key=lambda item: (-item["component_size"], item["node_id"]))


def topological_order(bundle: GraphBundle, edge_types: set[str] | None = None, node_types: set[str] | None = None) -> list[str]:
    node_ids = _filtered_node_ids(bundle, node_types)
    outgoing: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
    indegree: defaultdict[str, int] = defaultdict(int)
    for edge in bundle.edges:
        if edge_types is not None and edge.type not in edge_types:
            continue
        if edge.source not in node_ids or edge.target not in node_ids:
            continue
        if edge.target not in outgoing[edge.source]:
            outgoing[edge.source].add(edge.target)
            indegree[edge.target] += 1
            indegree.setdefault(edge.source, indegree[edge.source])

    ready = deque(sorted(node_id for node_id in node_ids if indegree[node_id] == 0))
    ordered: list[str] = []
    while ready:
        node_id = ready.popleft()
        ordered.append(node_id)
        for target in sorted(outgoing[node_id]):
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
    if len(ordered) != len(node_ids):
        cycle = sorted(node_ids - set(ordered))
        raise ValueError(f"graph contains a cycle involving: {', '.join(cycle)}")
    return ordered


def cycle_nodes(bundle: GraphBundle, edge_types: set[str] | None = None, node_types: set[str] | None = None) -> list[str]:
    try:
        topological_order(bundle, edge_types=edge_types, node_types=node_types)
        return []
    except ValueError as exc:
        message = str(exc)
        _, _, nodes = message.partition(": ")
        return [value for value in nodes.split(", ") if value]


def diagnostics(bundle: GraphBundle, node_types: set[str] | None = None) -> dict:
    node_ids = _filtered_node_ids(bundle, node_types)
    components = connected_components(bundle, node_types=node_types)
    bridges = bridge_nodes(bundle, node_types=node_types)
    inbound: defaultdict[str, int] = defaultdict(int)
    outbound: defaultdict[str, int] = defaultdict(int)
    neighbors = _undirected_adjacency(bundle, node_ids)
    for edge in bundle.edges:
        if edge.source in node_ids and edge.target in node_ids:
            outbound[edge.source] += 1
            inbound[edge.target] += 1
    degree_ranked = sorted(
        (
            {
                "node_id": node_id,
                "degree": len(neighbors[node_id]),
                "inbound_count": inbound[node_id],
                "outbound_count": outbound[node_id],
            }
            for node_id in node_ids
        ),
        key=lambda item: (-item["degree"], -item["inbound_count"], item["node_id"]),
    )
    return {
        "summary": {
            "node_count": len(node_ids),
            "edge_count": sum(1 for edge in bundle.edges if edge.source in node_ids and edge.target in node_ids),
            "connected_component_count": len(components),
            "largest_component_size": max((len(component) for component in components), default=0),
            "isolated_node_count": sum(1 for component in components if len(component) == 1),
            "bridge_node_count": len(bridges),
        },
        "components": [
            {"component_id": f"component-{index}", "size": len(component), "node_ids": component}
            for index, component in enumerate(components, start=1)
        ],
        "bridge_nodes": bridges,
        "top_connected_nodes": degree_ranked[:10],
    }


def _filtered_node_ids(bundle: GraphBundle, node_types: set[str] | None) -> set[str]:
    return {node.id for node in bundle.nodes if node_types is None or node.type in node_types}


def _undirected_adjacency(bundle: GraphBundle, node_ids: Iterable[str]) -> dict[str, set[str]]:
    allowed = set(node_ids)
    adjacency: dict[str, set[str]] = {node_id: set() for node_id in allowed}
    for edge in bundle.edges:
        if edge.source not in allowed or edge.target not in allowed:
            continue
        adjacency[edge.source].add(edge.target)
        adjacency[edge.target].add(edge.source)
    return adjacency


def _walk(start: str, adjacency: dict[str, set[str]], *, blocked: str, allowed: set[str]) -> set[str]:
    visited = {start}
    stack = [start]
    while stack:
        node = stack.pop()
        for neighbor in adjacency.get(node, set()):
            if neighbor == blocked or neighbor not in allowed or neighbor in visited:
                continue
            visited.add(neighbor)
            stack.append(neighbor)
    return visited

