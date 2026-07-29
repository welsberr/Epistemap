from __future__ import annotations

import json
import runpy
from pathlib import Path


def test_profile_loader_normalizes_groundrecall_graph_bundle(tmp_path: Path) -> None:
    module = runpy.run_path(str(Path(__file__).parents[1] / "benchmarks" / "profile_graph_bundles.py"))
    path = tmp_path / "groundrecall.json"
    path.write_text(
        json.dumps(
            {
                "bundle_kind": "groundrecall_graph_bundle",
                "root_concept": {"concept_id": "concept::alpha"},
                "nodes": [{"node_id": "concept::alpha", "node_kind": "concept", "record": {"title": "Alpha"}}],
                "edges": [{"edge_id": "rel::1", "source_id": "concept::alpha", "target_id": "concept::alpha", "relation_type": "related_to", "provenance": {}}],
            }
        ),
        encoding="utf-8",
    )
    bundle = module["_load_bundle"](path.read_text(encoding="utf-8"))
    assert bundle.graph_id == "concept::alpha"
    assert bundle.nodes[0].title == "Alpha"
    assert bundle.edges[0].type == "related_to"
