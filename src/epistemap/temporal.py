from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Iterable, Mapping

from .models import Edge, GraphBundle, Node, ProvenanceRef

SUPPORT_EDGE_TYPES = {"supports", "supports_claim", "about_concept", "supports_concept", "teaches_concept"}
CHALLENGE_EDGE_TYPES = {"contradicts", "challenges", "disputes"}
REVISION_EDGE_TYPES = {"supersedes", "corrects", "retracts", "qualifies"}

DEFAULT_AVAILABILITY_KEYS = (
    "available_at",
    "validated_at",
    "published_at",
    "observed_at",
    "introduced_at",
    "created_at",
    "timestep",
)
DEFAULT_EVENT_KEYS = (
    "introduced_at",
    "available_at",
    "observed_at",
    "published_at",
    "validated_at",
    "challenged_at",
    "superseded_at",
    "rejected_at",
    "created_at",
    "timestep",
)


def graph_at(
    bundle: GraphBundle,
    when: Any,
    *,
    include_undated: bool = True,
    date_keys: Iterable[str] = DEFAULT_AVAILABILITY_KEYS,
) -> GraphBundle:
    """Return the graph containing only nodes/edges available by `when`."""

    cutoff = _time_key(when)
    selected_nodes = {
        node.id
        for node in bundle.nodes
        if _is_available_by(node, cutoff, include_undated=include_undated, date_keys=tuple(date_keys))
    }
    selected_edges = [
        edge
        for edge in bundle.edges
        if edge.source in selected_nodes
        and edge.target in selected_nodes
        and _is_available_by(edge, cutoff, include_undated=include_undated, date_keys=tuple(date_keys))
    ]
    return GraphBundle(
        graph_id=f"{bundle.graph_id}:at:{when}" if bundle.graph_id else f"graph:at:{when}",
        title=bundle.title,
        description=f"Temporal graph slice available by {when}",
        nodes=[node for node in bundle.nodes if node.id in selected_nodes],
        edges=selected_edges,
        metadata={**bundle.metadata, "temporal_slice_at": str(when), "include_undated": include_undated},
    )


def evidence_available_at(bundle: GraphBundle, node_id: str, when: Any) -> dict[str, Any]:
    """Summarize support/challenge/revision evidence available for a node by time."""

    sliced = graph_at(bundle, when)
    support = [
        edge
        for edge in sliced.edges
        if edge.target == node_id and edge.type in SUPPORT_EDGE_TYPES
    ]
    challenge = [
        edge
        for edge in sliced.edges
        if (edge.source == node_id or edge.target == node_id) and edge.type in CHALLENGE_EDGE_TYPES
    ]
    revision = [
        edge
        for edge in sliced.edges
        if (edge.source == node_id or edge.target == node_id) and edge.type in REVISION_EDGE_TYPES
    ]
    return {
        "node_id": node_id,
        "at": str(when),
        "support_edges": [_edge_ref(edge) for edge in support],
        "challenge_edges": [_edge_ref(edge) for edge in challenge],
        "revision_edges": [_edge_ref(edge) for edge in revision],
        "summary": {
            "support_count": len(support),
            "challenge_count": len(challenge),
            "revision_count": len(revision),
        },
    }


def claim_status_at(bundle: GraphBundle, claim_id: str, when: Any) -> dict[str, Any]:
    """Classify a claim's temporal status from evidence available by `when`."""

    nodes = bundle.node_index()
    node = nodes.get(claim_id)
    if node is None:
        return {"claim_id": claim_id, "at": str(when), "status": "missing"}
    cutoff = _time_key(when)
    if not _is_available_by(node, cutoff, include_undated=True, date_keys=DEFAULT_AVAILABILITY_KEYS):
        return {"claim_id": claim_id, "at": str(when), "status": "not_yet_available"}

    evidence = evidence_available_at(bundle, claim_id, when)
    if evidence["summary"]["revision_count"]:
        status = "revised_or_superseded"
    elif evidence["summary"]["challenge_count"]:
        status = "contradicted"
    elif evidence["summary"]["support_count"]:
        status = "supported"
    else:
        status = "unresolved"
    return {
        "claim_id": claim_id,
        "at": str(when),
        "status": status,
        "evidence": evidence,
    }


def first_contradiction_time(bundle: GraphBundle, claim_id: str) -> dict[str, Any] | None:
    """Return the earliest available challenge edge involving a claim."""

    candidates = [
        (time_value, edge)
        for edge in bundle.edges
        if edge.type in CHALLENGE_EDGE_TYPES
        and (edge.source == claim_id or edge.target == claim_id)
        for time_value in [_item_time_with_display(edge, DEFAULT_AVAILABILITY_KEYS)]
        if time_value is not None
    ]
    if not candidates:
        return None
    time_value, edge = min(candidates, key=lambda item: item[0][0])
    return {"claim_id": claim_id, "time": time_value[1], "edge": _edge_ref(edge)}


def tenability_window(bundle: GraphBundle, claim_id: str) -> dict[str, Any]:
    """Describe when a claim becomes available and when it stops being tenable."""

    node = bundle.node_index().get(claim_id)
    introduced = _item_time_with_display(node, DEFAULT_AVAILABILITY_KEYS) if node is not None else None
    contradiction = first_contradiction_time(bundle, claim_id)
    revision = _first_edge_time(bundle, claim_id, REVISION_EDGE_TYPES)
    terminal_events = [item for item in (contradiction, revision) if item is not None]
    terminal = min(terminal_events, key=lambda item: _time_key(item["time"])) if terminal_events else None
    return {
        "claim_id": claim_id,
        "introduced_at": introduced[1] if introduced else "",
        "tenable_until": terminal["time"] if terminal else "",
        "terminal_event": terminal or {},
        "status": "bounded" if terminal else "open",
    }


def stale_claims_after(bundle: GraphBundle, when: Any, *, node_types: set[str] | None = None) -> list[dict[str, Any]]:
    """Find claims that remain active after contradiction/revision is available."""

    node_types = node_types or {"claim"}
    cutoff = _time_key(when)
    stale: list[dict[str, Any]] = []
    for node in bundle.nodes:
        if node.type not in node_types or node.status in {"rejected", "superseded", "archived"}:
            continue
        window = tenability_window(bundle, node.id)
        terminal_time = window.get("tenable_until")
        if terminal_time and _time_key(terminal_time) <= cutoff:
            stale.append(
                {
                    "claim_id": node.id,
                    "title": node.title,
                    "status": node.status,
                    "tenable_until": terminal_time,
                    "terminal_event": window.get("terminal_event", {}),
                }
            )
    return sorted(stale, key=lambda item: (str(item["tenable_until"]), item["claim_id"]))


def timeline_events(
    bundle: GraphBundle,
    *,
    event_keys: Iterable[str] = DEFAULT_EVENT_KEYS,
) -> list[dict[str, Any]]:
    """Return dated graph events sorted by time."""

    keys = tuple(event_keys)
    events: list[dict[str, Any]] = []
    for node in bundle.nodes:
        for event in _metadata_events(node.metadata, keys):
            events.append({"component": "node", "component_id": node.id, "component_type": node.type, **event})
        for provenance in node.provenance:
            for event in _metadata_events(provenance.metadata, keys):
                events.append({"component": "node_provenance", "component_id": node.id, "component_type": node.type, **event})
    for edge in bundle.edges:
        edge_id = edge.id or _edge_compound_id(edge)
        for event in _metadata_events(edge.metadata, keys):
            events.append({"component": "edge", "component_id": edge_id, "component_type": edge.type, **event})
        for provenance in edge.provenance:
            for event in _metadata_events(provenance.metadata, keys):
                events.append({"component": "edge_provenance", "component_id": edge_id, "component_type": edge.type, **event})
    return sorted(events, key=lambda item: (_time_key(item["time"]), item["component_id"], item["event"]))


def availability_lag(claim_time: Any, contradiction_time: Any, persistence_time: Any) -> dict[str, Any]:
    """Compute elapsed availability intervals when values are comparable."""

    claim_key = _time_key(claim_time)
    contradiction_key = _time_key(contradiction_time)
    persistence_key = _time_key(persistence_time)
    if not (claim_key[0] == contradiction_key[0] == persistence_key[0]):
        return {
            "claim_time": str(claim_time),
            "contradiction_time": str(contradiction_time),
            "persistence_time": str(persistence_time),
            "comparable": False,
        }
    return {
        "claim_time": str(claim_time),
        "contradiction_time": str(contradiction_time),
        "persistence_time": str(persistence_time),
        "comparable": True,
        "time_to_contradiction": contradiction_key[1] - claim_key[1],
        "post_contradiction_persistence": persistence_key[1] - contradiction_key[1],
    }


def recognition_window(bundle: GraphBundle, claim_id: str, recognized_at: Any | None = None) -> dict[str, Any]:
    """Compare first available contradiction with optional recognition time."""

    contradiction = first_contradiction_time(bundle, claim_id)
    if contradiction is None:
        return {
            "claim_id": claim_id,
            "contradiction_available_at": "",
            "recognized_at": str(recognized_at) if recognized_at is not None else "",
            "recognition_lag": None,
            "status": "no_available_contradiction",
        }
    if recognized_at is None:
        return {
            "claim_id": claim_id,
            "contradiction_available_at": contradiction["time"],
            "recognized_at": "",
            "recognition_lag": None,
            "status": "not_measured",
            "contradiction": contradiction,
        }
    lag = _comparable_lag(contradiction["time"], recognized_at)
    return {
        "claim_id": claim_id,
        "contradiction_available_at": contradiction["time"],
        "recognized_at": str(recognized_at),
        "recognition_lag": lag,
        "status": "recognized" if lag is not None else "recognized_uncomparable_time",
        "contradiction": contradiction,
    }


def fair_play_diagnostic(
    bundle: GraphBundle,
    claim_ids: Iterable[str] | None = None,
    *,
    reveal_at: Any | None = None,
    decisive_edge_types: set[str] | None = None,
) -> dict[str, Any]:
    """Assess whether contradiction evidence is available before the reveal.

    This is an admission diagnostic for fair-play detective-story and scholarly
    timeline corpora. It checks whether claims have dated contradiction/revision
    evidence and whether that evidence is available before the supplied reveal
    or denouement time. It does not judge literary quality or scientific truth.
    """

    decisive_edge_types = decisive_edge_types or (CHALLENGE_EDGE_TYPES | REVISION_EDGE_TYPES)
    node_claim_ids = [
        node.id
        for node in bundle.nodes
        if node.type == "claim"
    ]
    active_claim_ids = list(claim_ids) if claim_ids is not None else node_claim_ids
    checks = [
        _fair_play_claim_check(bundle, claim_id, reveal_at=reveal_at, decisive_edge_types=decisive_edge_types)
        for claim_id in active_claim_ids
    ]
    failure_counts: dict[str, int] = {}
    for check in checks:
        for failure in check["failures"]:
            failure_counts[failure] = failure_counts.get(failure, 0) + 1
    if not checks:
        rating = "no_claims"
    elif all(check["rating"] == "fair" for check in checks):
        rating = "fair"
    elif any(check["rating"] == "unfair" for check in checks):
        rating = "unfair"
    else:
        rating = "partial"
    return {
        "rating": rating,
        "summary": {
            "claim_count": len(checks),
            "fair_count": sum(1 for check in checks if check["rating"] == "fair"),
            "partial_count": sum(1 for check in checks if check["rating"] == "partial"),
            "unfair_count": sum(1 for check in checks if check["rating"] == "unfair"),
            "failure_counts": dict(sorted(failure_counts.items())),
        },
        "claims": checks,
    }


def _is_available_by(item: Node | Edge, cutoff: tuple[str, float], *, include_undated: bool, date_keys: tuple[str, ...]) -> bool:
    time_value = _item_time(item, date_keys)
    if time_value is None:
        return include_undated
    if time_value[0] != cutoff[0]:
        return include_undated
    return time_value[1] <= cutoff[1]


def _fair_play_claim_check(
    bundle: GraphBundle,
    claim_id: str,
    *,
    reveal_at: Any | None,
    decisive_edge_types: set[str],
) -> dict[str, Any]:
    decisive_edges = [
        edge
        for edge in bundle.edges
        if edge.type in decisive_edge_types and (edge.source == claim_id or edge.target == claim_id)
    ]
    dated_edges = [
        (time_value, edge)
        for edge in decisive_edges
        for time_value in [_item_time_with_display(edge, DEFAULT_AVAILABILITY_KEYS)]
        if time_value is not None
    ]
    failures: list[str] = []
    if not decisive_edges:
        failures.append("no_decisive_evidence")
    if decisive_edges and not dated_edges:
        failures.append("undated_decisive_evidence")
    decisive = min(dated_edges, key=lambda item: item[0][0]) if dated_edges else None
    if reveal_at is not None and decisive is not None:
        comparison = _compare_times(decisive[0][1], reveal_at)
        if comparison is None:
            failures.append("uncomparable_reveal_time")
        elif comparison > 0:
            failures.append("late_decisive_evidence")
        elif comparison == 0:
            failures.append("decisive_evidence_at_reveal")
    if any(_hidden_evidence(edge) for edge in decisive_edges):
        failures.append("hidden_or_private_decisive_evidence")
    if not failures:
        rating = "fair"
    elif failures == ["decisive_evidence_at_reveal"] or failures == ["uncomparable_reveal_time"]:
        rating = "partial"
    else:
        rating = "unfair"
    return {
        "claim_id": claim_id,
        "rating": rating,
        "failures": failures,
        "decisive_evidence_count": len(decisive_edges),
        "first_decisive_evidence": (
            {"time": decisive[0][1], "edge": _edge_ref(decisive[1])}
            if decisive is not None
            else {}
        ),
        "reveal_at": str(reveal_at) if reveal_at is not None else "",
    }


def _hidden_evidence(edge: Edge) -> bool:
    status = str(edge.metadata.get("availability_status", "")).strip().lower()
    scope = str(edge.metadata.get("access_scope", "")).strip().lower()
    if status in {"hidden", "private", "withheld", "unavailable", "detective_only"}:
        return True
    if scope in {"private", "detective_only", "hidden", "withheld"}:
        return True
    return False


def _compare_times(first: Any, second: Any) -> int | None:
    first_key = _time_key(first)
    second_key = _time_key(second)
    if first_key[0] != second_key[0]:
        return None
    if first_key[1] < second_key[1]:
        return -1
    if first_key[1] > second_key[1]:
        return 1
    return 0


def _comparable_lag(start: Any, end: Any) -> float | None:
    start_key = _time_key(start)
    end_key = _time_key(end)
    if start_key[0] != end_key[0]:
        return None
    return end_key[1] - start_key[1]


def _item_time(item: Node | Edge | None, date_keys: tuple[str, ...]) -> tuple[str, float] | None:
    value = _item_time_with_display(item, date_keys)
    return value[0] if value is not None else None


def _item_time_with_display(item: Node | Edge | None, date_keys: tuple[str, ...]) -> tuple[tuple[str, float], str] | None:
    if item is None:
        return None
    values = [_metadata_time_with_display(item.metadata, date_keys)]
    values.extend(_provenance_time_with_display(provenance, date_keys) for provenance in item.provenance)
    present = [value for value in values if value is not None]
    return min(present, default=None, key=lambda value: value[0])


def _provenance_time(provenance: ProvenanceRef, date_keys: tuple[str, ...]) -> tuple[str, float] | None:
    value = _provenance_time_with_display(provenance, date_keys)
    return value[0] if value is not None else None


def _provenance_time_with_display(provenance: ProvenanceRef, date_keys: tuple[str, ...]) -> tuple[tuple[str, float], str] | None:
    value = _metadata_time_with_display(provenance.metadata, date_keys)
    if value is not None:
        return value
    if provenance.metadata.get("retrieval_date"):
        raw = provenance.metadata["retrieval_date"]
        return _time_key(raw), str(raw)
    return None


def _metadata_time(metadata: Mapping[str, Any], date_keys: tuple[str, ...]) -> tuple[str, float] | None:
    value = _metadata_time_with_display(metadata, date_keys)
    return value[0] if value is not None else None


def _metadata_time_with_display(metadata: Mapping[str, Any], date_keys: tuple[str, ...]) -> tuple[tuple[str, float], str] | None:
    for key in date_keys:
        if key in metadata and metadata[key] not in {"", None}:
            return _time_key(metadata[key]), str(metadata[key])
    return None


def _metadata_events(metadata: Mapping[str, Any], event_keys: tuple[str, ...]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for key in event_keys:
        if key not in metadata or metadata[key] in {"", None}:
            continue
        events.append({"event": key, "time": str(metadata[key])})
    return events


def _first_edge_time(bundle: GraphBundle, claim_id: str, edge_types: set[str]) -> dict[str, Any] | None:
    candidates = [
        (time_value, edge)
        for edge in bundle.edges
        if edge.type in edge_types
        and (edge.source == claim_id or edge.target == claim_id)
        for time_value in [_item_time_with_display(edge, DEFAULT_AVAILABILITY_KEYS)]
        if time_value is not None
    ]
    if not candidates:
        return None
    time_value, edge = min(candidates, key=lambda item: item[0][0])
    return {"claim_id": claim_id, "time": time_value[1], "edge": _edge_ref(edge)}


def _time_key(value: Any) -> tuple[str, float]:
    if isinstance(value, bool):
        raise ValueError("boolean values are not valid time values")
    if isinstance(value, int | float):
        return ("numeric", float(value))
    text = str(value).strip()
    if not text:
        raise ValueError("empty time value")
    parsed = _parse_datetime(text)
    if parsed is not None:
        return ("datetime", parsed)
    if text.isdigit():
        return ("numeric", float(text))
    raise ValueError(f"unsupported time value: {value!r}")


def _parse_datetime(text: str) -> float | None:
    try:
        if len(text) == 4 and text.isdigit():
            return float(date(int(text), 1, 1).toordinal())
        if len(text) == 7 and text[4] == "-":
            year, month = text.split("-", 1)
            return float(date(int(year), int(month), 1).toordinal())
        normalized = text.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed.toordinal() + _day_fraction(parsed)
    except ValueError:
        try:
            return float(date.fromisoformat(text).toordinal())
        except ValueError:
            return None


def _day_fraction(value: datetime) -> float:
    return (value.hour * 3600 + value.minute * 60 + value.second + value.microsecond / 1_000_000) / 86_400


def _edge_ref(edge: Edge) -> dict[str, Any]:
    return {
        "id": edge.id,
        "source": edge.source,
        "target": edge.target,
        "type": edge.type,
        "title": edge.title,
    }


def _edge_compound_id(edge: Edge) -> str:
    return f"{edge.source}->{edge.type}->{edge.target}"
