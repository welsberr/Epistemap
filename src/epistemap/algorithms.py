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


def descendants(bundle: GraphBundle, node_id: str, edge_types: set[str] | None = None) -> list[str]:
    return sorted(_reachable(bundle, [node_id], direction="out", edge_types=edge_types) - {node_id})


def ancestors(bundle: GraphBundle, node_id: str, edge_types: set[str] | None = None) -> list[str]:
    return sorted(_reachable(bundle, [node_id], direction="in", edge_types=edge_types) - {node_id})


def shortest_path(bundle: GraphBundle, source: str, target: str, edge_types: set[str] | None = None) -> list[str]:
    node_ids = {node.id for node in bundle.nodes}
    if source not in node_ids or target not in node_ids:
        return []
    adjacency = _directed_adjacency(bundle, node_ids, edge_types=edge_types, direction="out")
    queue: deque[tuple[str, list[str]]] = deque([(source, [source])])
    seen = {source}
    while queue:
        node_id, path = queue.popleft()
        if node_id == target:
            return path
        for neighbor in sorted(adjacency[node_id]):
            if neighbor in seen:
                continue
            seen.add(neighbor)
            queue.append((neighbor, path + [neighbor]))
    return []


def k_hop_subgraph(bundle: GraphBundle, seeds: list[str], hops: int = 1, edge_types: set[str] | None = None) -> GraphBundle:
    node_ids = {node.id for node in bundle.nodes}
    selected = _reachable(bundle, seeds, direction="both", edge_types=edge_types, max_depth=hops)
    selected &= node_ids
    return GraphBundle(
        graph_id=f"{bundle.graph_id}:subgraph" if bundle.graph_id else "subgraph",
        title=bundle.title,
        description=f"{hops}-hop subgraph",
        nodes=[node for node in bundle.nodes if node.id in selected],
        edges=[
            edge
            for edge in bundle.edges
            if edge.source in selected
            and edge.target in selected
            and (edge_types is None or edge.type in edge_types)
        ],
        metadata={**bundle.metadata, "subgraph_seeds": list(seeds), "subgraph_hops": hops},
    )


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


def graph_qa_report(bundle: GraphBundle, *, required_provenance_edge_types: set[str] | None = None) -> dict:
    required_provenance_edge_types = required_provenance_edge_types or set()
    node_ids = {node.id for node in bundle.nodes}
    missing_targets = [
        {"source": edge.source, "target": edge.target, "type": edge.type}
        for edge in bundle.edges
        if edge.source not in node_ids or edge.target not in node_ids
    ]
    duplicate_node_ids = sorted(_duplicates(node.id for node in bundle.nodes))
    weak_edges = [
        {"source": edge.source, "target": edge.target, "type": edge.type, "confidence": edge.confidence}
        for edge in bundle.edges
        if edge.confidence is not None and edge.confidence < 0.5
    ]
    missing_provenance = [
        {"source": edge.source, "target": edge.target, "type": edge.type}
        for edge in bundle.edges
        if edge.type in required_provenance_edge_types and not edge.provenance and not edge.evidence_ids
    ]
    return {
        "summary": {
            "node_count": len(bundle.nodes),
            "edge_count": len(bundle.edges),
            "duplicate_node_id_count": len(duplicate_node_ids),
            "missing_endpoint_count": len(missing_targets),
            "weak_edge_count": len(weak_edges),
            "missing_provenance_count": len(missing_provenance),
        },
        "duplicate_node_ids": duplicate_node_ids,
        "missing_targets": missing_targets,
        "weak_edges": weak_edges,
        "missing_provenance": missing_provenance,
    }


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


def _reachable(
    bundle: GraphBundle,
    starts: list[str],
    *,
    direction: str,
    edge_types: set[str] | None,
    max_depth: int | None = None,
) -> set[str]:
    node_ids = {node.id for node in bundle.nodes}
    adjacency = _directed_adjacency(bundle, node_ids, edge_types=edge_types, direction=direction)
    seen = {start for start in starts if start in node_ids}
    queue: deque[tuple[str, int]] = deque((start, 0) for start in seen)
    while queue:
        node_id, depth = queue.popleft()
        if max_depth is not None and depth >= max_depth:
            continue
        for neighbor in adjacency[node_id]:
            if neighbor in seen:
                continue
            seen.add(neighbor)
            queue.append((neighbor, depth + 1))
    return seen


def _directed_adjacency(
    bundle: GraphBundle,
    node_ids: Iterable[str],
    *,
    edge_types: set[str] | None,
    direction: str,
) -> dict[str, set[str]]:
    allowed = set(node_ids)
    adjacency: dict[str, set[str]] = {node_id: set() for node_id in allowed}
    for edge in bundle.edges:
        if edge_types is not None and edge.type not in edge_types:
            continue
        if edge.source not in allowed or edge.target not in allowed:
            continue
        if direction in {"out", "both"}:
            adjacency[edge.source].add(edge.target)
        if direction in {"in", "both"}:
            adjacency[edge.target].add(edge.source)
    return adjacency


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


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    dupes: set[str] = set()
    for value in values:
        if value in seen:
            dupes.add(value)
        seen.add(value)
    return dupes
