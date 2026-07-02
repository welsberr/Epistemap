from __future__ import annotations

from dataclasses import dataclass, field

from .algorithms import cycle_nodes, graph_qa_report
from .models import GraphBundle


@dataclass
class GraphShape:
    required_node_fields: dict[str, set[str]] = field(default_factory=dict)
    required_edge_fields: dict[str, set[str]] = field(default_factory=dict)
    allowed_edge_types: dict[str, set[str]] = field(default_factory=dict)
    acyclic_edge_types: set[str] = field(default_factory=set)
    provenance_required_edge_types: set[str] = field(default_factory=set)


def validate_shape(bundle: GraphBundle, shape: GraphShape) -> dict:
    findings: list[dict] = []
    node_ids = {node.id for node in bundle.nodes}
    for node in bundle.nodes:
        for field_name in shape.required_node_fields.get(node.type, set()):
            if not _node_field_present(node, field_name):
                findings.append(
                    {
                        "severity": "error",
                        "code": "missing_node_field",
                        "node_id": node.id,
                        "field": field_name,
                    }
                )
    for edge in bundle.edges:
        if edge.source not in node_ids or edge.target not in node_ids:
            findings.append(
                {
                    "severity": "error",
                    "code": "missing_edge_endpoint",
                    "source": edge.source,
                    "target": edge.target,
                    "edge_type": edge.type,
                }
            )
            continue
        source_type = bundle.node_index()[edge.source].type
        target_type = bundle.node_index()[edge.target].type
        allowed_targets = shape.allowed_edge_types.get(source_type)
        if allowed_targets is not None and target_type not in allowed_targets:
            findings.append(
                {
                    "severity": "warning",
                    "code": "unexpected_edge_target_type",
                    "source": edge.source,
                    "target": edge.target,
                    "edge_type": edge.type,
                    "source_type": source_type,
                    "target_type": target_type,
                }
            )
        for field_name in shape.required_edge_fields.get(edge.type, set()):
            if not _edge_field_present(edge, field_name):
                findings.append(
                    {
                        "severity": "error",
                        "code": "missing_edge_field",
                        "source": edge.source,
                        "target": edge.target,
                        "edge_type": edge.type,
                        "field": field_name,
                    }
                )
    for edge_type in sorted(shape.acyclic_edge_types):
        nodes = cycle_nodes(bundle, edge_types={edge_type})
        if nodes:
            findings.append(
                {
                    "severity": "error",
                    "code": "edge_type_cycle",
                    "edge_type": edge_type,
                    "node_ids": nodes,
                }
            )
    qa = graph_qa_report(bundle, required_provenance_edge_types=shape.provenance_required_edge_types)
    for item in qa["missing_provenance"]:
        findings.append({"severity": "warning", "code": "missing_edge_provenance", **item})
    return {
        "summary": {
            "error_count": sum(1 for item in findings if item["severity"] == "error"),
            "warning_count": sum(1 for item in findings if item["severity"] == "warning"),
            **qa["summary"],
        },
        "findings": findings,
    }


def _node_field_present(node, field_name: str) -> bool:
    if hasattr(node, field_name):
        return getattr(node, field_name) not in ("", None, [], {})
    return node.metadata.get(field_name) not in ("", None, [], {})


def _edge_field_present(edge, field_name: str) -> bool:
    if hasattr(edge, field_name):
        return getattr(edge, field_name) not in ("", None, [], {})
    return edge.metadata.get(field_name) not in ("", None, [], {})
