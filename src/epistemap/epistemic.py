from __future__ import annotations

from collections import Counter
from typing import Any

from .models import Edge, GraphBundle, Node

SUPPORT_EDGE_TYPES = {"supports", "supports_claim", "about_concept", "supports_concept", "teaches_concept"}
CHALLENGE_EDGE_TYPES = {"contradicts", "challenges", "disputes"}
REVISION_EDGE_TYPES = {"supersedes", "corrects", "retracts", "qualifies"}


def epistemic_summary(bundle: GraphBundle, node_id: str, *, low_confidence_threshold: float = 0.5) -> dict[str, Any]:
    nodes = bundle.node_index()
    target = nodes.get(node_id)
    incident = [edge for edge in bundle.edges if edge.source == node_id or edge.target == node_id]
    incoming = [edge for edge in incident if edge.target == node_id]
    outgoing = [edge for edge in incident if edge.source == node_id]
    claim_ids = _claim_ids_for_target(bundle, node_id)
    claim_evidence_edges = [edge for edge in bundle.edges if edge.target in claim_ids or edge.source in claim_ids]
    relevant_node_ids = (
        {node_id}
        | claim_ids
        | {edge.source for edge in incident}
        | {edge.target for edge in incident}
        | {edge.source for edge in claim_evidence_edges}
        | {edge.target for edge in claim_evidence_edges}
    )
    relevant_edges = [
        edge
        for edge in bundle.edges
        if edge.source in relevant_node_ids and edge.target in relevant_node_ids
    ]
    relevant_nodes = [node for node in bundle.nodes if node.id in relevant_node_ids]
    support_edges = [edge for edge in relevant_edges if edge.type in SUPPORT_EDGE_TYPES and (edge.target == node_id or edge.target in claim_ids)]
    challenge_edges = [edge for edge in relevant_edges if edge.type in CHALLENGE_EDGE_TYPES]
    revision_edges = [edge for edge in relevant_edges if edge.type in REVISION_EDGE_TYPES]
    low_confidence_nodes = [
        node
        for node in relevant_nodes
        if node.confidence is not None and node.confidence < low_confidence_threshold
    ]
    grounding = Counter(_grounding_values(relevant_nodes, relevant_edges))
    source_roles = Counter(_source_roles(relevant_nodes))
    flags = _epistemic_flags(
        support_edges=support_edges,
        challenge_edges=challenge_edges,
        revision_edges=revision_edges,
        low_confidence_nodes=low_confidence_nodes,
        grounding=grounding,
        source_roles=source_roles,
    )
    return {
        "node_id": node_id,
        "node_type": target.type if target is not None else "",
        "title": target.title if target is not None else "",
        "summary": {
            "direct_support_count": len(support_edges),
            "challenge_count": len(challenge_edges),
            "revision_count": len(revision_edges),
            "low_confidence_node_count": len(low_confidence_nodes),
            "incoming_count": len(incoming),
            "outgoing_count": len(outgoing),
        },
        "grounding_status_summary": dict(sorted(grounding.items())),
        "source_role_summary": dict(sorted(source_roles.items())),
        "flags": flags,
        "support_edges": [_edge_ref(edge) for edge in support_edges[:12]],
        "challenge_edges": [_edge_ref(edge) for edge in challenge_edges[:12]],
        "revision_edges": [_edge_ref(edge) for edge in revision_edges[:12]],
        "low_confidence_nodes": [_node_ref(node) for node in low_confidence_nodes[:12]],
    }


def epistemic_report(bundle: GraphBundle, *, node_types: set[str] | None = None) -> dict[str, Any]:
    node_types = node_types or {"concept", "claim"}
    summaries = [
        epistemic_summary(bundle, node.id)
        for node in bundle.nodes
        if node.type in node_types
    ]
    flag_counts: Counter[str] = Counter()
    for summary in summaries:
        flag_counts.update(summary["flags"])
    return {
        "summary": {
            "node_count": len(summaries),
            "flagged_node_count": sum(1 for item in summaries if item["flags"]),
            "flag_counts": dict(sorted(flag_counts.items())),
        },
        "nodes": summaries,
    }


def _claim_ids_for_target(bundle: GraphBundle, node_id: str) -> set[str]:
    nodes = bundle.node_index()
    target = nodes.get(node_id)
    if target is not None and target.type == "claim":
        return {node_id}
    return {
        edge.source
        for edge in bundle.edges
        if edge.target == node_id and edge.type == "about_concept" and nodes.get(edge.source, Node(id="", type="")).type == "claim"
    }


def _grounding_values(nodes: list[Node], edges: list[Edge]) -> list[str]:
    values: list[str] = []
    for node in nodes:
        if node.status in {"grounded", "partially_grounded", "ungrounded"}:
            values.append(node.status)
        values.extend(item.grounding_status for item in node.provenance if item.grounding_status)
    for edge in edges:
        values.extend(item.grounding_status for item in edge.provenance if item.grounding_status)
    return values


def _source_roles(nodes: list[Node]) -> list[str]:
    roles: list[str] = []
    for node in nodes:
        role = str(node.metadata.get("source_role", "")).strip()
        if role:
            roles.append(role)
        roles.extend(str(value).strip() for value in node.metadata.get("source_roles", []) if str(value).strip())
    return roles


def _epistemic_flags(
    *,
    support_edges: list[Edge],
    challenge_edges: list[Edge],
    revision_edges: list[Edge],
    low_confidence_nodes: list[Node],
    grounding: Counter[str],
    source_roles: Counter[str],
) -> list[str]:
    flags: list[str] = []
    if not support_edges:
        flags.append("no_direct_support")
    if challenge_edges:
        flags.append("challenged")
    if revision_edges:
        flags.append("revised_or_qualified")
    if low_confidence_nodes:
        flags.append("low_confidence")
    if grounding.get("ungrounded", 0) or (grounding and not grounding.get("grounded", 0)):
        flags.append("weak_grounding")
    if len(source_roles) == 1:
        flags.append("narrow_source_role")
    return flags


def _edge_ref(edge: Edge) -> dict[str, Any]:
    return {
        "source": edge.source,
        "target": edge.target,
        "type": edge.type,
        "confidence": edge.confidence,
        "evidence_ids": list(edge.evidence_ids),
    }


def _node_ref(node: Node) -> dict[str, Any]:
    return {
        "id": node.id,
        "type": node.type,
        "title": node.title,
        "confidence": node.confidence,
        "status": node.status,
    }
