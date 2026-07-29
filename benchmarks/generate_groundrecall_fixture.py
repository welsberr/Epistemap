from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_fixture(scale: int = 1) -> dict:
    scale = max(1, int(scale))
    nodes = []
    for index in range(6 * scale):
        if index % 3 == 0:
            kind = "concept"
        elif index % 3 == 1:
            kind = "claim"
        else:
            kind = "observation"
        nodes.append(
            {
                "node_id": f"{kind}::fixture-{index}",
                "node_kind": kind,
                "status": "reviewed" if index % 4 else "promoted",
                "record": {"title": f"Sanitized fixture record {index}"},
            }
        )
    edges = []
    for index in range(5 * scale):
        source = nodes[index % len(nodes)]["node_id"]
        target = nodes[(index + 1) % len(nodes)]["node_id"]
        edges.append(
            {
                "edge_id": f"relation::fixture-{index}",
                "source_id": source,
                "target_id": target,
                "relation_type": "supports" if index % 3 == 0 else "related_to",
                "status": "reviewed",
                "provenance": {},
            }
        )
    return {
        "bundle_kind": "groundrecall_graph_bundle",
        "query_type": "graph",
        "root_concept": {"concept_id": nodes[0]["node_id"]},
        "nodes": nodes,
        "edges": edges,
        "projection_summary": {"fixture": "sanitized", "scale": scale},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a sanitized GroundRecall-shaped profiling fixture.")
    parser.add_argument("--scale", type=int, default=1)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(build_fixture(args.scale), indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
