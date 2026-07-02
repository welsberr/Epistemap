from __future__ import annotations

import json

from epistemap import Edge, GraphBundle, Node, to_cytoscape_json, to_graphviz_dot, to_jsonld, write_cytoscape_json, write_graphviz_dot, write_jsonld


def _bundle() -> GraphBundle:
    return GraphBundle(
        graph_id="graph::demo",
        title="Demo",
        description="Demo graph",
        nodes=[
            Node(id="concept::a", type="concept", title="A"),
            Node(id="concept::b", type="concept", title="B"),
        ],
        edges=[Edge(source="concept::a", target="concept::b", type="prerequisite", confidence=0.9)],
    )


def test_graphviz_export() -> None:
    dot = to_graphviz_dot(_bundle())
    assert "concept::a" in dot
    assert "prerequisite" in dot


def test_cytoscape_export() -> None:
    payload = to_cytoscape_json(_bundle())
    assert payload["nodes"][0]["data"]["id"] == "concept::a"
    assert payload["edges"][0]["data"]["source"] == "concept::a"


def test_jsonld_export() -> None:
    payload = to_jsonld(_bundle())
    assert payload["@id"] == "graph::demo"
    assert payload["@graph"]


def test_write_exports(tmp_path) -> None:
    bundle = _bundle()
    write_graphviz_dot(bundle, tmp_path / "graph.dot")
    write_cytoscape_json(bundle, tmp_path / "graph.cy.json")
    write_jsonld(bundle, tmp_path / "graph.jsonld")
    assert "digraph" in (tmp_path / "graph.dot").read_text(encoding="utf-8")
    assert json.loads((tmp_path / "graph.cy.json").read_text(encoding="utf-8"))["nodes"]
    assert json.loads((tmp_path / "graph.jsonld").read_text(encoding="utf-8"))["@graph"]
