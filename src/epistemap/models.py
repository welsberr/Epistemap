from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProvenanceRef(BaseModel):
    source_id: str = ""
    artifact_id: str = ""
    origin_path: str = ""
    source_url: str = ""
    support_kind: str = ""
    grounding_status: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class Node(BaseModel):
    id: str
    type: str
    title: str = ""
    description: str = ""
    aliases: list[str] = Field(default_factory=list)
    status: str = ""
    confidence: float | None = None
    provenance: list[ProvenanceRef] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Edge(BaseModel):
    source: str
    target: str
    type: str
    id: str = ""
    title: str = ""
    justification: str = ""
    confidence: float | None = None
    status: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    provenance: list[ProvenanceRef] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphBundle(BaseModel):
    bundle_kind: str = "epistemap_graph_bundle"
    graph_id: str = ""
    title: str = ""
    description: str = ""
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def node_index(self) -> dict[str, Node]:
        return {node.id: node for node in self.nodes}

    def model_dump_legacy(self) -> dict[str, Any]:
        payload = self.model_dump(exclude_none=True)
        payload["summary"] = {
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            **dict(self.metadata.get("summary", {})),
        }
        return payload

