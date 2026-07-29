from __future__ import annotations

import json

from epistemap.mcp import call_tool, list_tools
from epistemap.models import Edge, GraphBundle, Node
from epistemap.io import write_graph_bundle


def _graph(path):
    write_graph_bundle(
        GraphBundle(
            graph_id="mcp-fixture",
            nodes=[Node(id="source", type="source", title="Source"), Node(id="claim", type="claim", title="Claim")],
            edges=[Edge(source="source", target="claim", type="supports")],
            metadata={"bayesian_prior_profile": "neutral"},
        ),
        path,
    )


def test_mcp_tool_listing_is_versioned_and_read_only() -> None:
    listing = list_tools()
    assert listing["server"]["name"] == "epistemap-mcp"
    assert {tool["name"] for tool in listing["tools"]} == {
        "validate_graph", "graph_diagnostics", "graph_neighborhood", "epistemic_report", "bayesian_assessment"
    }


def test_mcp_tools_match_library_shapes(tmp_path) -> None:
    path = tmp_path / "graph.json"
    _graph(path)
    result = call_tool("graph_diagnostics", {"graph_bundle": str(path)})
    payload = json.loads(result["content"][0]["text"])
    assert payload["schema_version"] == "epistemap.mcp.result.v1"
    assert payload["payload"]["summary"]["node_count"] == 2
    neighborhood_result = call_tool("graph_neighborhood", {"graph_bundle": str(path), "node_id": "claim"})
    neighborhood_payload = json.loads(neighborhood_result["content"][0]["text"])
    assert neighborhood_payload["payload"]["node"]["id"] == "claim"
    assert neighborhood_payload["payload"]["incoming"][0]["type"] == "supports"

