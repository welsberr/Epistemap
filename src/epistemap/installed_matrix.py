from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import venv
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_MANIFEST = Path(__file__).resolve().parents[2] / "docs" / "installed-cross-repo-matrix.json"
REQUIRED_ROW_IDS = {
    "epistemap_legacy_to_current",
    "citegeist_to_epistemap",
    "citegeist_to_groundrecall",
    "citegeist_to_didactopus",
    "groundrecall_to_epistemap",
    "groundrecall_to_didactopus",
    "didactopus_to_epistemap",
    "didactopus_to_groundrecall",
}


@dataclass(frozen=True)
class MatrixRow:
    row_id: str
    producer: str
    consumer: str
    artifact: str
    fixture_id: str
    producer_schema_version: str
    consumer_schema_version: str
    producer_release: str
    consumer_release: str
    install_paths: list[str]
    expected_test_command: list[str]
    deterministic_hash: bool

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "MatrixRow":
        return cls(
            row_id=str(payload["row_id"]),
            producer=str(payload["producer"]),
            consumer=str(payload["consumer"]),
            artifact=str(payload["artifact"]),
            fixture_id=str(payload["fixture_id"]),
            producer_schema_version=str(payload["producer_schema_version"]),
            consumer_schema_version=str(payload["consumer_schema_version"]),
            producer_release=str(payload["producer_release"]),
            consumer_release=str(payload["consumer_release"]),
            install_paths=[str(item) for item in payload["install_paths"]],
            expected_test_command=[str(item) for item in payload["expected_test_command"]],
            deterministic_hash=bool(payload["deterministic_hash"]),
        )


def load_installed_matrix_manifest(path: str | Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_installed_matrix_manifest(payload)
    return payload


def validate_installed_matrix_manifest(payload: dict[str, Any]) -> None:
    rows = [MatrixRow.from_payload(item) for item in payload.get("rows", [])]
    row_ids = {row.row_id for row in rows}
    missing = REQUIRED_ROW_IDS - row_ids
    extra = row_ids - REQUIRED_ROW_IDS
    if missing or extra:
        raise ValueError(f"installed matrix row mismatch: missing={sorted(missing)} extra={sorted(extra)}")
    for row in rows:
        if not row.expected_test_command:
            raise ValueError(f"matrix row {row.row_id} has no expected_test_command")
        if not row.producer_schema_version or not row.consumer_schema_version:
            raise ValueError(f"matrix row {row.row_id} must declare schema versions")
        if not row.producer_release or not row.consumer_release:
            raise ValueError(f"matrix row {row.row_id} must declare producer/consumer releases")


def run_installed_matrix(
    manifest_path: str | Path | None = DEFAULT_MANIFEST,
    *,
    repo_root: str | Path | None = None,
    out_report: str | Path | None = None,
    row_ids: set[str] | None = None,
    dry_run: bool = False,
    keep_envs: bool = False,
) -> dict[str, Any]:
    actual_manifest_path = Path(manifest_path) if manifest_path is not None else DEFAULT_MANIFEST
    manifest = load_installed_matrix_manifest(actual_manifest_path)
    root = Path(repo_root) if repo_root is not None else actual_manifest_path.resolve().parents[1]
    selected_rows = [
        MatrixRow.from_payload(item)
        for item in manifest["rows"]
        if row_ids is None or str(item["row_id"]) in row_ids
    ]
    results = [_dry_run_row(row) if dry_run else _run_row(row, root=root, keep_env=keep_envs) for row in selected_rows]
    payload = {
        "report_kind": "epistemap_installed_cross_repo_matrix_report",
        "matrix_id": manifest["matrix_id"],
        "schema_version": manifest["schema_version"],
        "dry_run": dry_run,
        "row_count": len(results),
        "passed": all(item["status"] == "pass" for item in results),
        "rows": results,
    }
    if out_report is not None:
        target = Path(out_report)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def _dry_run_row(row: MatrixRow) -> dict[str, Any]:
    return {
        "row_id": row.row_id,
        "status": "dry_run",
        "producer": row.producer,
        "consumer": row.consumer,
        "artifact": row.artifact,
        "fixture_id": row.fixture_id,
        "producer_schema_version": row.producer_schema_version,
        "consumer_schema_version": row.consumer_schema_version,
        "producer_release": row.producer_release,
        "consumer_release": row.consumer_release,
        "expected_test_command": row.expected_test_command,
        "deterministic_hash": row.deterministic_hash,
    }


def _run_row(row: MatrixRow, *, root: Path, keep_env: bool) -> dict[str, Any]:
    env_dir = Path(tempfile.mkdtemp(prefix=f"epistemap-matrix-{row.row_id}-"))
    try:
        venv.EnvBuilder(with_pip=True, system_site_packages=True).create(env_dir)
        python = _venv_python(env_dir)
        install_results = [_install_path(python, _resolve_install_path(root, install_path)) for install_path in row.install_paths]
        command = [python, *row.expected_test_command[1:]] if row.expected_test_command and row.expected_test_command[0] == "python" else row.expected_test_command
        run = subprocess.run(
            command,
            cwd=env_dir,
            env=_clean_env(),
            text=True,
            capture_output=True,
            check=False,
        )
        installs_ok = all(item["returncode"] == 0 for item in install_results)
        status = "pass" if installs_ok and run.returncode == 0 else "fail"
        fixture_payload = _last_json_object(run.stdout) if run.stdout.strip() else {}
        return {
            "row_id": row.row_id,
            "status": status,
            "producer": row.producer,
            "consumer": row.consumer,
            "artifact": row.artifact,
            "fixture_id": row.fixture_id,
            "producer_schema_version": row.producer_schema_version,
            "consumer_schema_version": row.consumer_schema_version,
            "producer_release": row.producer_release,
            "consumer_release": row.consumer_release,
            "install_results": install_results,
            "command": command,
            "returncode": run.returncode,
            "stdout": run.stdout,
            "stderr": run.stderr,
            "artifact_hash": fixture_payload.get("artifact_hash", ""),
        }
    finally:
        if keep_env:
            pass
        else:
            shutil.rmtree(env_dir, ignore_errors=True)


def _install_path(python: str, path: Path) -> dict[str, Any]:
    command = [python, "-m", "pip", "install", "--no-build-isolation", "--no-deps", str(path)]
    run = subprocess.run(command, text=True, capture_output=True, check=False)
    return {"path": str(path), "returncode": run.returncode, "stdout": run.stdout, "stderr": run.stderr}


def _resolve_install_path(root: Path, install_path: str) -> Path:
    path = Path(install_path)
    if path.is_absolute():
        return path
    return (root / path).resolve()


def _venv_python(env_dir: Path) -> str:
    candidate = env_dir / "bin" / "python"
    if candidate.exists():
        return str(candidate)
    return str(env_dir / "Scripts" / "python.exe")


def _clean_env() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    for key in list(env):
        if key.endswith("_PYTHONPATH"):
            env.pop(key, None)
    return env


def _last_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if not stripped:
        return {}
    start = stripped.rfind("\n{")
    candidate = stripped[start + 1 :] if start >= 0 else stripped
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return {}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Epistemap installed cross-repository compatibility matrix.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--row-id", action="append", default=[])
    parser.add_argument("--out", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--keep-envs", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    payload = run_installed_matrix(
        args.manifest,
        repo_root=args.repo_root,
        out_report=args.out,
        row_ids=set(args.row_id) if args.row_id else None,
        dry_run=args.dry_run,
        keep_envs=args.keep_envs,
    )
    print(json.dumps(payload, indent=2))
    if not args.dry_run and not payload["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
