from __future__ import annotations

from collections import defaultdict, deque
from typing import Iterable

from .index import GraphIndex, build_graph_index
from .models import Edge, GraphBundle, Node


def incoming_edges(bundle: GraphBundle, node_id: str, edge_types: set[str] | None = None) -> list[Edge]:
    return _incoming_edges(build_graph_index(bundle), node_id, edge_types=edge_types)


def outgoing_edges(bundle: GraphBundle, node_id: str, edge_types: set[str] | None = None) -> list[Edge]:
    return _outgoing_edges(build_graph_index(bundle), node_id, edge_types=edge_types)


def neighborhood(bundle: GraphBundle, node_id: str, edge_types: set[str] | None = None) -> dict:
    index = build_graph_index(bundle)
    incoming = _incoming_edges(index, node_id, edge_types=edge_types)
    outgoing = _outgoing_edges(index, node_id, edge_types=edge_types)
    return {
        "node": index.nodes_by_id.get(node_id),
        "incoming": incoming,
        "outgoing": outgoing,
        "incoming_nodes": [index.nodes_by_id[edge.source] for edge in incoming if edge.source in index.nodes_by_id],
        "outgoing_nodes": [index.nodes_by_id[edge.target] for edge in outgoing if edge.target in index.nodes_by_id],
    }


def descendants(bundle: GraphBundle, node_id: str, edge_types: set[str] | None = None) -> list[str]:
    return sorted(_reachable(bundle, [node_id], direction="out", edge_types=edge_types) - {node_id})


def ancestors(bundle: GraphBundle, node_id: str, edge_types: set[str] | None = None) -> list[str]:
    return sorted(_reachable(bundle, [node_id], direction="in", edge_types=edge_types) - {node_id})


def shortest_path(bundle: GraphBundle, source: str, target: str, edge_types: set[str] | None = None) -> list[str]:
    index = build_graph_index(bundle)
    if source not in index.node_ids or target not in index.node_ids:
        return []
    adjacency = _directed_adjacency(index, index.node_ids, edge_types=edge_types, direction="out")
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
    index = build_graph_index(bundle)
    selected = _reachable(bundle, seeds, direction="both", edge_types=edge_types, max_depth=hops)
    selected &= set(index.node_ids)
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
    index = build_graph_index(bundle)
    node_ids = _filtered_node_ids(index, node_types)
    adjacency = _undirected_adjacency(index, node_ids)
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
    index = build_graph_index(bundle)
    node_ids = _filtered_node_ids(index, node_types)
    adjacency = _undirected_adjacency(index, node_ids)
    components = _connected_components_from_adjacency(adjacency, node_ids)
    return _bridge_nodes_from_adjacency(components, adjacency)


def topological_order(bundle: GraphBundle, edge_types: set[str] | None = None, node_types: set[str] | None = None) -> list[str]:
    index = build_graph_index(bundle)
    node_ids = _filtered_node_ids(index, node_types)
    outgoing: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
    indegree: defaultdict[str, int] = defaultdict(int)
    edges = _candidate_edges(index, edge_types)
    for edge in edges:
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
    index = build_graph_index(bundle)
    node_ids = index.node_ids
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
    index = build_graph_index(bundle)
    node_ids = _filtered_node_ids(index, node_types)
    neighbors = _undirected_adjacency(index, node_ids)
    components = _connected_components_from_adjacency(neighbors, node_ids)
    bridges = _bridge_nodes_from_adjacency(components, neighbors)
    inbound: defaultdict[str, int] = defaultdict(int)
    outbound: defaultdict[str, int] = defaultdict(int)
    for edge in _candidate_edges(index, None):
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
    index = build_graph_index(bundle)
    adjacency = _directed_adjacency(index, index.node_ids, edge_types=edge_types, direction=direction)
    seen = {start for start in starts if start in index.node_ids}
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
    index: GraphIndex,
    node_ids: Iterable[str],
    *,
    edge_types: set[str] | None,
    direction: str,
) -> dict[str, set[str]]:
    allowed = set(node_ids)
    adjacency: dict[str, set[str]] = {node_id: set() for node_id in allowed}
    for edge in _candidate_edges(index, edge_types):
        if edge.source not in allowed or edge.target not in allowed:
            continue
        if direction in {"out", "both"}:
            adjacency[edge.source].add(edge.target)
        if direction in {"in", "both"}:
            adjacency[edge.target].add(edge.source)
    return adjacency


def _filtered_node_ids(index: GraphIndex, node_types: set[str] | None) -> set[str]:
    return {
        node_id
        for node_id, node in index.nodes_by_id.items()
        if node_types is None or node.type in node_types
    }


def _undirected_adjacency(index: GraphIndex, node_ids: Iterable[str]) -> dict[str, set[str]]:
    allowed = set(node_ids)
    return {
        node_id: {neighbor for neighbor in index.undirected_neighbors.get(node_id, frozenset()) if neighbor in allowed}
        for node_id in allowed
    }


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


def _incoming_edges(index: GraphIndex, node_id: str, edge_types: set[str] | None = None) -> list[Edge]:
    edges = index.incoming_by_node.get(node_id, ())
    if edge_types is None:
        return list(edges)
    return [edge for edge in edges if edge.type in edge_types]


def _outgoing_edges(index: GraphIndex, node_id: str, edge_types: set[str] | None = None) -> list[Edge]:
    edges = index.outgoing_by_node.get(node_id, ())
    if edge_types is None:
        return list(edges)
    return [edge for edge in edges if edge.type in edge_types]


def _candidate_edges(index: GraphIndex, edge_types: set[str] | None) -> tuple[Edge, ...]:
    if edge_types is None:
        return index.edges
    return tuple(edge for edge in index.edges if edge.type in edge_types)


def _connected_components_from_adjacency(adjacency: dict[str, set[str]], node_ids: Iterable[str]) -> list[list[str]]:
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


def _bridge_nodes_from_adjacency(components: list[list[str]], adjacency: dict[str, set[str]]) -> list[dict]:
    payloads: list[dict] = []
    for component in components:
        if len(component) < 3:
            continue
        payloads.extend(_articulation_payloads(component, adjacency))
    return sorted(payloads, key=lambda item: (-item["component_size"], item["node_id"]))


def _articulation_payloads(component: list[str], adjacency: dict[str, set[str]]) -> list[dict]:
    discovery: dict[str, int] = {}
    low: dict[str, int] = {}
    parent: dict[str, str | None] = {}
    subtree_size: dict[str, int] = {}
    exit_order: dict[str, int] = {}
    root_child_count: defaultdict[str, int] = defaultdict(int)
    separating_children: defaultdict[str, list[str]] = defaultdict(list)
    clock = 0

    for root in component:
        if root in discovery:
            continue
        parent[root] = None
        discovery[root] = clock
        low[root] = clock
        subtree_size[root] = 1
        clock += 1
        stack: list[tuple[str, list[str], int]] = [(root, sorted(adjacency[root]), 0)]
        while stack:
            node_id, neighbors, offset = stack[-1]
            if offset >= len(neighbors):
                stack.pop()
                exit_order[node_id] = clock
                clock += 1
                parent_id = parent[node_id]
                if parent_id is not None:
                    subtree_size[parent_id] += subtree_size[node_id]
                    if low[node_id] >= discovery[parent_id]:
                        separating_children[parent_id].append(node_id)
                    low[parent_id] = min(low[parent_id], low[node_id])
                continue

            neighbor = neighbors[offset]
            stack[-1] = (node_id, neighbors, offset + 1)
            if neighbor == parent.get(node_id):
                continue
            if neighbor not in discovery:
                parent[neighbor] = node_id
                discovery[neighbor] = clock
                low[neighbor] = clock
                subtree_size[neighbor] = 1
                clock += 1
                if parent[node_id] is None:
                    root_child_count[node_id] += 1
                stack.append((neighbor, sorted(adjacency[neighbor]), 0))
                continue
            low[node_id] = min(low[node_id], discovery[neighbor])

    payloads: list[dict] = []
    component_size = len(component)
    component_node_ids = set(component)
    for node_id in component:
        if parent.get(node_id) is None:
            if root_child_count[node_id] <= 1:
                continue
        elif not separating_children[node_id]:
            continue
        remaining = sorted(component_node_ids - {node_id})
        if not remaining:
            continue
        conceptual_start = remaining[0]
        reachable_after_removal = _reachable_component_after_removal(
            node_id=node_id,
            conceptual_start=conceptual_start,
            component_size=component_size,
            parent=parent,
            discovery=discovery,
            exit_order=exit_order,
            subtree_size=subtree_size,
            root_child_count=root_child_count,
            separating_children=separating_children,
        )
        payloads.append(
            {
                "node_id": node_id,
                "component_size": component_size,
                "reachable_after_removal": reachable_after_removal,
            }
        )
    return payloads


def _reachable_component_after_removal(
    *,
    node_id: str,
    conceptual_start: str,
    component_size: int,
    parent: dict[str, str | None],
    discovery: dict[str, int],
    exit_order: dict[str, int],
    subtree_size: dict[str, int],
    root_child_count: defaultdict[str, int],
    separating_children: defaultdict[str, list[str]],
) -> int:
    if parent.get(node_id) is None:
        for child_id in separating_children[node_id]:
            if _is_descendant(conceptual_start, child_id, discovery, exit_order):
                return subtree_size[child_id]
        return 0

    separated_total = 0
    for child_id in separating_children[node_id]:
        separated_total += subtree_size[child_id]
        if _is_descendant(conceptual_start, child_id, discovery, exit_order):
            return subtree_size[child_id]

    if root_child_count[node_id] > 1 and parent.get(node_id) is None:
        return 0
    return component_size - 1 - separated_total


def _is_descendant(
    node_id: str,
    ancestor_id: str,
    discovery: dict[str, int],
    exit_order: dict[str, int],
) -> bool:
    return discovery[ancestor_id] <= discovery[node_id] <= exit_order[ancestor_id]
