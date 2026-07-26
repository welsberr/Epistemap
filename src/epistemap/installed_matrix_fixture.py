from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .confidence import AssessmentMethodRef, ConfidenceAssessment
from .evidence import deterministic_hash, graph_to_evidence_ledger
from .models import Edge, GraphBundle, Node


def _assessment(subject_id: str, value: float, *, dimension: str = "identity_resolution") -> ConfidenceAssessment:
    return ConfidenceAssessment(
        assessment_id=f"asm::{subject_id}::{dimension}",
        subject_id=subject_id,
        dimension=dimension,
        value=value,
        band="high" if value >= 0.7 else "low",
        method=AssessmentMethodRef(name="installed_matrix_fixture", version="1.0", policy_id="installed_matrix_fixture_v1"),
        basis_record_ids=[subject_id, "fixture::source"],
        basis_hash=deterministic_hash({"basis": [subject_id, "fixture::source"]}),
        rationale="Synthetic installed compatibility fixture.",
        recorded_at="2026-07-25T00:00:00Z",
    )


def _graph_bundle(fixture_id: str, *, typed: bool = True, legacy_confidence: float | None = None) -> GraphBundle:
    claim_assessments = [_assessment("claim::main", 0.82, dimension="evidential_support")] if typed else []
    return GraphBundle(
        graph_id=f"installed-matrix::{fixture_id}",
        title=f"Installed matrix fixture {fixture_id}",
        nodes=[
            Node(id="concept::fixture", type="concept", title="Fixture concept"),
            Node(
                id="claim::main",
                type="claim",
                title="Fixture claim",
                description="Synthetic claim for installed compatibility checks.",
                confidence=legacy_confidence,
                assessments=claim_assessments,
                metadata={"fixture_id": fixture_id},
            ),
            Node(id="obs::source", type="observation", title="Fixture source observation"),
        ],
        edges=[
            Edge(
                id="edge::support",
                source="obs::source",
                target="claim::main",
                type="supports_claim",
                evidence_ids=["obs::source"],
                confidence=legacy_confidence,
            ),
            Edge(id="edge::about", source="claim::main", target="concept::fixture", type="about_concept"),
        ],
        metadata={"fixture_id": fixture_id, "schema_version": "epistemap_graph_bundle.v1"},
    )


def _import_optional(package_name: str) -> str:
    module = __import__(package_name)
    return str(getattr(module, "__version__", "unknown"))


def run_fixture(row_id: str) -> dict[str, Any]:
    optional_imports: dict[str, str] = {}
    if "citegeist" in row_id:
        optional_imports["citegeist"] = _import_optional("citegeist")
    if "groundrecall" in row_id:
        optional_imports["groundrecall"] = _import_optional("groundrecall")
    if "didactopus" in row_id:
        optional_imports["didactopus"] = _import_optional("didactopus")

    legacy = row_id == "epistemap_legacy_to_current"
    graph = _graph_bundle(row_id, typed=not legacy, legacy_confidence=0.0 if legacy else None)
    ledger = graph_to_evidence_ledger(graph, "claim::main")
    artifact = {
        "row_id": row_id,
        "graph": graph.model_dump_legacy(),
        "ledger": ledger.model_dump(),
        "optional_imports": optional_imports,
    }
    return {
        "row_id": row_id,
        "status": "pass",
        "artifact_hash": deterministic_hash(artifact),
        "artifact": artifact,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an installed cross-repository matrix fixture row.")
    parser.add_argument("--row-id", required=True)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    payload = run_fixture(args.row_id)
    if args.out:
        Path(args.out).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
