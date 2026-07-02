from __future__ import annotations

import json
from pathlib import Path

from .models import GraphBundle


def load_graph_bundle(path: str | Path) -> GraphBundle:
    return GraphBundle.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_graph_bundle(bundle: GraphBundle, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(bundle.model_dump_legacy(), indent=2), encoding="utf-8")

