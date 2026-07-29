from __future__ import annotations

import argparse
import json
import os
import platform
import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from epistemap import Edge, GraphBundle, Node, bayesian_assessment_report, connected_components, diagnostics, epistemic_report, shortest_path, bridge_nodes, validate_assessment_readiness


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark core Epistemap graph operations.")
    parser.add_argument("--sizes", nargs="+", type=int, default=[100, 1000, 3000])
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument(
        "--workloads",
        nargs="+",
        default=["path", "star", "cycle", "disconnected", "pairs", "random_sparse"],
    )
    parser.add_argument("--random-seed", type=int, default=17)
    args = parser.parse_args()

    result = {
        "environment": {
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "processor": platform.processor(),
            "pid": os.getpid(),
        },
        "parameters": {
            "sizes": args.sizes,
            "repeats": args.repeats,
            "workloads": args.workloads,
            "random_seed": args.random_seed,
        },
        "results": {},
    }

    for workload in args.workloads:
        result["results"][workload] = {}
        for size in args.sizes:
            bundle = _make_bundle(workload, size, args.random_seed)
            result["results"][workload][str(size)] = _benchmark_bundle(bundle, repeats=max(3, args.repeats))

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _benchmark_bundle(bundle: GraphBundle, *, repeats: int) -> dict[str, object]:
    construction_payload = {
        "graph_id": bundle.graph_id,
        "title": bundle.title,
        "description": bundle.description,
        "nodes": [node.model_dump() for node in bundle.nodes],
        "edges": [edge.model_dump() for edge in bundle.edges],
        "metadata": bundle.metadata,
    }
    operations = {
        "model_construction": lambda: GraphBundle.model_validate(construction_payload),
        "connected_components": lambda: connected_components(bundle),
        "shortest_path": lambda: shortest_path(bundle, bundle.nodes[0].id, bundle.nodes[-1].id) if bundle.nodes else [],
        "bridge_nodes": lambda: bridge_nodes(bundle),
        "diagnostics": lambda: diagnostics(bundle),
        "assessment_readiness": lambda: validate_assessment_readiness(bundle),
        "epistemic_report": lambda: epistemic_report(bundle),
        "bayesian_assessment_report": lambda: bayesian_assessment_report(bundle),
    }
    timings = {name: _measure(callable_, repeats) for name, callable_ in operations.items()}
    return {
        "node_count": len(bundle.nodes),
        "edge_count": len(bundle.edges),
        "timings": timings,
    }


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


def _make_bundle(workload: str, size: int, seed: int) -> GraphBundle:
    if workload == "path":
        return _path_bundle(size)
    if workload == "star":
        return _star_bundle(size)
    if workload == "cycle":
        return _cycle_bundle(size)
    if workload == "disconnected":
        return _disconnected_bundle(size)
    if workload == "pairs":
        return _pairs_bundle(size)
    if workload == "random_sparse":
        return _random_sparse_bundle(size, seed)
    raise ValueError(f"unknown workload: {workload}")


def _path_bundle(size: int) -> GraphBundle:
    nodes = [Node(id=f"node::{index:05d}", type="concept", title=f"Node {index}") for index in range(size)]
    edges = [
        Edge(source=nodes[index].id, target=nodes[index + 1].id, type="supports")
        for index in range(max(0, size - 1))
    ]
    return GraphBundle(graph_id=f"path-{size}", nodes=nodes, edges=edges)


def _star_bundle(size: int) -> GraphBundle:
    nodes = [Node(id=f"node::{index:05d}", type="concept", title=f"Node {index}") for index in range(size)]
    edges = [
        Edge(source=nodes[0].id, target=nodes[index].id, type="supports")
        for index in range(1, len(nodes))
    ]
    return GraphBundle(graph_id=f"star-{size}", nodes=nodes, edges=edges)


def _cycle_bundle(size: int) -> GraphBundle:
    nodes = [Node(id=f"node::{index:05d}", type="concept", title=f"Node {index}") for index in range(size)]
    if not nodes:
        return GraphBundle(graph_id=f"cycle-{size}", nodes=[], edges=[])
    edges = [
        Edge(source=nodes[index].id, target=nodes[(index + 1) % len(nodes)].id, type="supports")
        for index in range(len(nodes))
    ]
    return GraphBundle(graph_id=f"cycle-{size}", nodes=nodes, edges=edges)


def _disconnected_bundle(size: int) -> GraphBundle:
    nodes = [Node(id=f"node::{index:05d}", type="concept", title=f"Node {index}") for index in range(size)]
    edges: list[Edge] = []
    block = 5
    for start in range(0, len(nodes), block):
        for index in range(start, min(start + block - 1, len(nodes) - 1)):
            edges.append(Edge(source=nodes[index].id, target=nodes[index + 1].id, type="supports"))
    return GraphBundle(graph_id=f"disconnected-{size}", nodes=nodes, edges=edges)


def _pairs_bundle(size: int) -> GraphBundle:
    nodes: list[Node] = []
    edges: list[Edge] = []
    for index in range(size):
        source_id = f"source::{index:05d}"
        claim_id = f"claim::{index:05d}"
        nodes.append(Node(id=source_id, type="source", title=f"Source {index}", metadata={"available_at": "2026-01-01"}))
        nodes.append(Node(id=claim_id, type="claim", title=f"Claim {index}"))
        edges.append(Edge(source=source_id, target=claim_id, type="supports", confidence=0.8, evidence_ids=[source_id]))
    return GraphBundle(graph_id=f"pairs-{size}", nodes=nodes, edges=edges)


def _random_sparse_bundle(size: int, seed: int) -> GraphBundle:
    generator = random.Random(seed + size)
    nodes = [Node(id=f"node::{index:05d}", type="concept", title=f"Node {index}") for index in range(size)]
    edges: list[Edge] = []
    edge_count = max(0, size * 2)
    for _ in range(edge_count):
        source_index = generator.randrange(size) if size else 0
        target_index = generator.randrange(size) if size else 0
        if size and source_index == target_index and size > 1:
            target_index = (target_index + 1) % size
        if size:
            edges.append(Edge(source=nodes[source_index].id, target=nodes[target_index].id, type="supports"))
    return GraphBundle(graph_id=f"random-sparse-{size}", nodes=nodes, edges=edges)


if __name__ == "__main__":
    raise SystemExit(main())
