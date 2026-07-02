from __future__ import annotations

import re


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return cleaned or "untitled"


def typed_id(node_type: str, value: str) -> str:
    value = value.strip()
    if value.startswith(f"{node_type}::"):
        return value
    return f"{node_type}::{value}"


def node_id(node_type: str, *parts: str, slug: bool = True) -> str:
    values = [slugify(part) if slug else part.strip() for part in parts if part.strip()]
    return typed_id(node_type, "::".join(values) if values else "untitled")

