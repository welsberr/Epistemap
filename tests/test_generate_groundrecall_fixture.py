from __future__ import annotations

import runpy
from pathlib import Path


build_fixture = runpy.run_path(str(Path(__file__).parents[1] / "benchmarks" / "generate_groundrecall_fixture.py"))["build_fixture"]


def test_groundrecall_fixture_generator_scales_deterministically() -> None:
    first = build_fixture(10)
    second = build_fixture(10)
    assert first == second
    assert len(first["nodes"]) == 60
    assert len(first["edges"]) == 50
