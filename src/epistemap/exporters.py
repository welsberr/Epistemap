from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Edge, GraphBundle, Node


def to_graphviz_dot(bundle: GraphBundle, *, graph_name: str = "Epistemap") -> str:
    lines = [f"digraph {_dot_id(graph_name)} {{"]
    for node in bundle.nodes:
        label = node.title or node.id
        lines.append(f'  "{_escape(node.id)}" [label="{_escape(label)}", type="{_escape(node.type)}"];')
    for edge in bundle.edges:
        label = edge.type
        lines.append(f'  "{_escape(edge.source)}" -> "{_escape(edge.target)}" [label="{_escape(label)}"];')
    lines.append("}")
    return "\n".join(lines)


def write_graphviz_dot(bundle: GraphBundle, path: str | Path, *, graph_name: str = "Epistemap") -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(to_graphviz_dot(bundle, graph_name=graph_name), encoding="utf-8")


def to_cytoscape_json(bundle: GraphBundle) -> dict[str, list[dict[str, Any]]]:
    return {
        "nodes": [{"data": _node_payload(node)} for node in bundle.nodes],
        "edges": [{"data": _edge_payload(edge)} for edge in bundle.edges],
    }


def write_cytoscape_json(bundle: GraphBundle, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(to_cytoscape_json(bundle), indent=2), encoding="utf-8")


def to_jsonld(bundle: GraphBundle) -> dict[str, Any]:
    graph: list[dict[str, Any]] = []
    for node in bundle.nodes:
        payload = {
            "@id": node.id,
            "@type": node.type,
            "name": node.title,
            "description": node.description,
            "status": node.status,
            **node.metadata,
        }
        if node.provenance:
            payload["prov:wasDerivedFrom"] = [_provenance_payload(item) for item in node.provenance]
        graph.append(_strip_empty(payload))
    for edge in bundle.edges:
        edge_id = edge.id or f"{edge.source}--{edge.type}--{edge.target}"
        payload = {
            "@id": edge_id,
            "@type": edge.type,
            "source": {"@id": edge.source},
            "target": {"@id": edge.target},
            "name": edge.title,
            "description": edge.justification,
            "confidence": edge.confidence,
            "status": edge.status,
            "evidence": edge.evidence_ids,
            **edge.metadata,
        }
        if edge.provenance:
            payload["prov:wasDerivedFrom"] = [_provenance_payload(item) for item in edge.provenance]
        graph.append(_strip_empty(payload))
    return {
        "@context": {
            "name": "http://schema.org/name",
            "description": "http://schema.org/description",
            "source": {"@id": "http://schema.org/source", "@type": "@id"},
            "target": {"@id": "http://schema.org/target", "@type": "@id"},
            "confidence": "https://welsberr.github.io/epistemap/vocab/confidence",
            "evidence": "https://welsberr.github.io/epistemap/vocab/evidence",
            "prov": "http://www.w3.org/ns/prov#",
        },
        "@id": bundle.graph_id,
        "@type": "EpistemapGraphBundle",
        "name": bundle.title,
        "description": bundle.description,
        "@graph": graph,
    }


def write_jsonld(bundle: GraphBundle, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(to_jsonld(bundle), indent=2), encoding="utf-8")


def _node_payload(node: Node) -> dict[str, Any]:
    return _strip_empty(
        {
            "id": node.id,
            "type": node.type,
            "title": node.title,
            "description": node.description,
            "status": node.status,
            "confidence": node.confidence,
            **node.metadata,
        }
    )


def _edge_payload(edge: Edge) -> dict[str, Any]:
    return _strip_empty(
        {
            "id": edge.id,
            "source": edge.source,
            "target": edge.target,
            "type": edge.type,
            "title": edge.title,
            "justification": edge.justification,
            "confidence": edge.confidence,
            "status": edge.status,
            "evidence_ids": edge.evidence_ids,
            **edge.metadata,
        }
    )


def _provenance_payload(provenance) -> dict[str, Any]:
    return _strip_empty(
        {
            "source_id": provenance.source_id,
            "artifact_id": provenance.artifact_id,
            "origin_path": provenance.origin_path,
            "source_url": provenance.source_url,
            "support_kind": provenance.support_kind,
            "grounding_status": provenance.grounding_status,
            **provenance.metadata,
        }
    )


def _strip_empty(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value not in ("", None, [], {})}


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _dot_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in value)
    return cleaned or "Epistemap"
