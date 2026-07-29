from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from epistemap import (
    GraphBundle,
    bayesian_assessment_report,
    bridge_nodes,
    connected_components,
    diagnostics,
    epistemic_report,
    shortest_path,
    validate_assessment_readiness,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Profile representative graph bundles with Epistemap operations.")
    parser.add_argument("paths", nargs="+", help="Graph bundle JSON paths.")
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()

    results = {
        "environment": {
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "processor": platform.processor(),
            "pid": os.getpid(),
        },
        "parameters": {
            "repeats": max(3, args.repeats),
            "paths": args.paths,
        },
        "results": [],
    }

    for raw_path in args.paths:
        path = Path(raw_path)
        payload = path.read_text(encoding="utf-8")
        bundle = _load_bundle(payload)
        results["results"].append(
            {
                "path": str(path),
                "graph_id": bundle.graph_id,
                "title": bundle.title,
                "shape": _shape_summary(bundle),
                "timings": _profile_bundle(bundle, payload, repeats=max(3, args.repeats)),
            }
        )

    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


def _load_bundle(payload: str) -> GraphBundle:
    data = json.loads(payload)
    normalized = _normalize_bundle_payload(data)
    return GraphBundle.model_validate(normalized)


def _normalize_bundle_payload(data: dict[str, object]) -> dict[str, object]:
    normalized = dict(data)
    normalized["nodes"] = [_normalize_component(item) for item in list(data.get("nodes", []))]
    normalized["edges"] = [_normalize_component(item) for item in list(data.get("edges", []))]
    return normalized


def _normalize_component(item: object) -> dict[str, object]:
    if not isinstance(item, dict):
        return {}
    normalized = dict(item)
    provenance = normalized.get("provenance")
    if isinstance(provenance, list):
        normalized["provenance"] = [
            value
            if isinstance(value, dict)
            else {"origin_path": str(value)}
            for value in provenance
        ]
    return normalized


def _shape_summary(bundle: GraphBundle) -> dict[str, object]:
    node_type_counts = Counter(node.type for node in bundle.nodes)
    edge_type_counts = Counter(edge.type for edge in bundle.edges)
    outgoing_counts = Counter(edge.source for edge in bundle.edges if edge.source)
    incoming_counts = Counter(edge.target for edge in bundle.edges if edge.target)
    assessed_node_count = sum(1 for node in bundle.nodes if node.type in {"claim", "concept"})
    component_sizes = [len(component) for component in connected_components(bundle)]
    return {
        "node_count": len(bundle.nodes),
        "edge_count": len(bundle.edges),
        "assessed_node_count": assessed_node_count,
        "node_type_counts": dict(sorted(node_type_counts.items())),
        "edge_type_counts": dict(sorted(edge_type_counts.items())),
        "connected_component_count": len(component_sizes),
        "largest_component_size": max(component_sizes, default=0),
        "max_out_degree": max(outgoing_counts.values(), default=0),
        "max_in_degree": max(incoming_counts.values(), default=0),
    }


def _profile_bundle(bundle: GraphBundle, payload: str, *, repeats: int) -> dict[str, dict[str, float]]:
    source = bundle.nodes[0].id if bundle.nodes else ""
    target = bundle.nodes[-1].id if bundle.nodes else ""
    operations = {
        "json_load": lambda: _load_bundle(payload),
        "connected_components": lambda: connected_components(bundle),
        "shortest_path": lambda: shortest_path(bundle, source, target) if source and target else [],
        "bridge_nodes": lambda: bridge_nodes(bundle),
        "diagnostics": lambda: diagnostics(bundle),
        "assessment_readiness": lambda: validate_assessment_readiness(bundle),
        "epistemic_report": lambda: epistemic_report(bundle),
        "bayesian_assessment_report": lambda: bayesian_assessment_report(bundle),
    }
    return {name: _measure(operation, repeats) for name, operation in operations.items()}


def _measure(operation, repeats: int) -> dict[str, float]:
    operation()
    samples: list[float] = []
    for _ in range(repeats):
        start = time.perf_counter()
        operation()
        samples.append(time.perf_counter() - start)
    return {
        "minimum_seconds": min(samples),
        "median_seconds": statistics.median(samples),
    }


if __name__ == "__main__":
    raise SystemExit(main())
