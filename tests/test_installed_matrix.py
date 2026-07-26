from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from epistemap.installed_matrix import (
    REQUIRED_ROW_IDS,
    _clean_env,
    load_installed_matrix_manifest,
    run_installed_matrix,
)
from epistemap.installed_matrix_fixture import run_fixture


MANIFEST = Path(__file__).resolve().parents[1] / "docs" / "installed-cross-repo-matrix.json"


def test_installed_matrix_manifest_covers_required_cross_repo_rows() -> None:
    payload = load_installed_matrix_manifest(MANIFEST)

    row_ids = {row["row_id"] for row in payload["rows"]}

    assert row_ids == REQUIRED_ROW_IDS
    assert all(row["producer_release"] and row["consumer_release"] for row in payload["rows"])
    assert all(row["producer_schema_version"] and row["consumer_schema_version"] for row in payload["rows"])
    assert all(row["expected_test_command"] for row in payload["rows"])


def test_installed_matrix_dry_run_reports_versions_and_commands(tmp_path: Path) -> None:
    report_path = tmp_path / "matrix-report.json"

    payload = run_installed_matrix(MANIFEST, out_report=report_path, dry_run=True)

    assert payload["dry_run"] is True
    assert payload["row_count"] == len(REQUIRED_ROW_IDS)
    assert report_path.exists()
    assert {row["status"] for row in payload["rows"]} == {"dry_run"}
    assert all("expected_test_command" in row for row in payload["rows"])
    assert all("producer_schema_version" in row for row in payload["rows"])


def test_installed_matrix_clean_env_unsets_sibling_pythonpath(monkeypatch) -> None:
    monkeypatch.setenv("PYTHONPATH", "/home/netuser/bin/CiteGeist/src")
    monkeypatch.setenv("CITEGEIST_PYTHONPATH", "/home/netuser/bin/CiteGeist/src")

    env = _clean_env()

    assert "PYTHONPATH" not in env
    assert "CITEGEIST_PYTHONPATH" not in env


def test_installed_matrix_fixture_hash_is_deterministic() -> None:
    first = run_fixture("groundrecall_to_epistemap")
    second = run_fixture("groundrecall_to_epistemap")

    assert first["status"] == "pass"
    assert first["artifact_hash"] == second["artifact_hash"]
    assert first["artifact"]["ledger"]["subject_claim_ids"] == ["claim::main"]


def test_installed_matrix_cli_dry_run_writes_report(tmp_path: Path) -> None:
    report_path = tmp_path / "matrix-report.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "epistemap.cli",
            "installed-matrix",
            "--manifest",
            str(MANIFEST),
            "--dry-run",
            "--out",
            str(report_path),
        ],
        cwd=Path(__file__).resolve().parents[1],
        env={key: value for key, value in os.environ.items() if key != "PYTHONPATH"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(report_path.read_text(encoding="utf-8"))["dry_run"] is True
