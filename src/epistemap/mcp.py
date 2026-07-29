"""Optional, read-only MCP-style adapter for Epistemap graph operations.

The adapter deliberately has no MCP dependency. Hosts can map ``list_tools``
and ``call_tool`` to their transport of choice while retaining deterministic
library behavior and a clear boundary: Epistemap produces auditable analysis;
it does not authorize promotion or decide truth.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .algorithms import diagnostics, k_hop_subgraph, neighborhood
from .epistemic import bayesian_assessment_report, epistemic_report
from .io import load_graph_bundle
from .validation import validate_assessment_readiness

SERVER_INFO = {"name": "epistemap-mcp", "version": "0.1.0a2"}

TOOL_SCHEMAS: tuple[dict[str, Any], ...] = (
    {
        "name": "validate_graph",
        "description": "Validate graph readiness for auditable assessment.",
        "inputSchema": {"type": "object", "required": ["graph_bundle"], "properties": {"graph_bundle": {"type": "string"}}},
    },
    {
        "name": "graph_diagnostics",
        "description": "Run indexed graph diagnostics and connectivity analysis.",
        "inputSchema": {"type": "object", "required": ["graph_bundle"], "properties": {"graph_bundle": {"type": "string"}, "node_types": {"type": "array", "items": {"type": "string"}}}},
    },
    {
        "name": "graph_neighborhood",
        "description": "Return a node neighborhood with provenance-bearing graph records.",
        "inputSchema": {"type": "object", "required": ["graph_bundle", "node_id"], "properties": {"graph_bundle": {"type": "string"}, "node_id": {"type": "string"}, "hops": {"type": "integer", "minimum": 0, "maximum": 3}}},
    },
    {
        "name": "epistemic_report",
        "description": "Produce epistemic and reliability review affordances.",
        "inputSchema": {"type": "object", "required": ["graph_bundle"], "properties": {"graph_bundle": {"type": "string"}, "node_types": {"type": "array", "items": {"type": "string"}}}},
    },
    {
        "name": "bayesian_assessment",
        "description": "Produce Bayesian assessment rows and reliability labels.",
        "inputSchema": {"type": "object", "required": ["graph_bundle"], "properties": {"graph_bundle": {"type": "string"}, "node_types": {"type": "array", "items": {"type": "string"}}}},
    },
)


def list_tools() -> dict[str, Any]:
    """Return a versioned, transport-neutral tool listing."""
    return {"server": SERVER_INFO, "tools": list(TOOL_SCHEMAS)}


def _bundle(arguments: dict[str, Any]):
    return load_graph_bundle(Path(str(arguments["graph_bundle"])))


def _json_content(payload: Any) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(payload, sort_keys=True)}]}


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute one read-only tool and return MCP-compatible content blocks."""
    bundle = _bundle(arguments)
    node_types = set(arguments.get("node_types") or []) or None
    if name == "validate_graph":
        payload = validate_assessment_readiness(bundle)
    elif name == "graph_diagnostics":
        payload = diagnostics(bundle, node_types=node_types)
    elif name == "graph_neighborhood":
        node_id = str(arguments["node_id"])
        hops = int(arguments.get("hops", 1))
        if hops <= 1:
            payload = neighborhood(bundle, node_id)
            payload = {key: value.model_dump(mode="json") if hasattr(value, "model_dump") else [item.model_dump(mode="json") for item in value] if isinstance(value, list) else value for key, value in payload.items()}
        else:
            payload = k_hop_subgraph(bundle, [node_id], hops=hops).model_dump(mode="json")
    elif name == "epistemic_report":
        payload = epistemic_report(bundle, node_types=node_types)
    elif name == "bayesian_assessment":
        payload = bayesian_assessment_report(bundle, node_types=node_types)
    else:
        raise ValueError(f"unknown Epistemap MCP tool: {name}")
    return _json_content({"schema_version": "epistemap.mcp.result.v1", "tool": name, "graph_id": bundle.graph_id, "payload": payload})
