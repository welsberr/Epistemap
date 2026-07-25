from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Iterable

from .ids import node_id, slugify
from .models import Edge, GraphBundle, Node, ProvenanceRef


PERSON_NODE = "person_candidate"
EVENT_NODE = "event_claim"
RELATIONSHIP_NODE = "relationship_claim"
SOURCE_NODE = "source_record"

EVENT_TAGS = {
    "BIRT": "birth",
    "CHR": "christening",
    "DEAT": "death",
    "BURI": "burial",
    "MARR": "marriage",
    "DIV": "divorce",
    "RESI": "residence",
    "OCCU": "occupation",
    "EMIG": "emigration",
    "IMMI": "immigration",
    "CENS": "census",
    "EDUC": "education",
    "EVEN": "event",
}


@dataclass
class GedcomLine:
    level: int
    tag: str
    value: str = ""
    xref: str = ""
    children: list["GedcomLine"] = field(default_factory=list)


def parse_gedcom_lines(lines: Iterable[str]) -> list[GedcomLine]:
    roots: list[GedcomLine] = []
    stack: list[GedcomLine] = []
    for raw_line in lines:
        line = raw_line.rstrip("\r\n")
        if not line.strip():
            continue
        parsed = _parse_gedcom_line(line)
        while stack and stack[-1].level >= parsed.level:
            stack.pop()
        if stack:
            stack[-1].children.append(parsed)
        else:
            roots.append(parsed)
        stack.append(parsed)
    return roots


def read_gedcom(path: str | Path) -> list[GedcomLine]:
    return parse_gedcom_lines(Path(path).read_text(encoding="utf-8", errors="replace").splitlines())


def gedcom_to_graph_bundle(
    path: str | Path,
    *,
    graph_id: str | None = None,
    title: str | None = None,
) -> GraphBundle:
    source_path = Path(path)
    records = read_gedcom(source_path)
    graph = graph_id or slugify(source_path.stem)
    provenance = ProvenanceRef(
        source_id=f"gedcom:{graph}",
        artifact_id=source_path.name,
        origin_path=str(source_path),
        support_kind="genealogy_import",
        grounding_status="imported_unreviewed",
    )
    bundle = GraphBundle(
        graph_id=graph,
        title=title or f"Genealogy graph from {source_path.name}",
        description="GEDCOM-derived genealogy claim graph. Imported records are unreviewed candidate claims.",
        metadata={
            "domain": "genealogy",
            "source_format": "GEDCOM",
            "source_path": str(source_path),
            "publication_status": "private_unreviewed",
        },
    )

    source_nodes = _source_nodes(records, graph, provenance)
    person_nodes = _person_nodes(records, graph, provenance)
    event_nodes, event_edges = _event_nodes_and_edges(records, graph, provenance, source_nodes)
    relationship_nodes, relationship_edges = _family_relationships(records, graph, provenance)

    bundle.nodes.extend(source_nodes.values())
    bundle.nodes.extend(person_nodes.values())
    bundle.nodes.extend(event_nodes)
    bundle.nodes.extend(relationship_nodes)
    bundle.edges.extend(event_edges)
    bundle.edges.extend(relationship_edges)
    bundle.metadata["summary"] = genealogy_graph_summary(bundle)
    return bundle


def genealogy_graph_summary(bundle: GraphBundle) -> dict[str, int]:
    node_counts: dict[str, int] = {}
    edge_counts: dict[str, int] = {}
    for node in bundle.nodes:
        node_counts[node.type] = node_counts.get(node.type, 0) + 1
    for edge in bundle.edges:
        edge_counts[edge.type] = edge_counts.get(edge.type, 0) + 1
    return {
        "node_count": len(bundle.nodes),
        "edge_count": len(bundle.edges),
        **{f"nodes_{key}": value for key, value in sorted(node_counts.items())},
        **{f"edges_{key}": value for key, value in sorted(edge_counts.items())},
    }


def write_genealogy_graph_bundle(
    path: str | Path,
    out: str | Path,
    *,
    graph_id: str | None = None,
    title: str | None = None,
) -> dict[str, object]:
    bundle = gedcom_to_graph_bundle(path, graph_id=graph_id, title=title)
    target = Path(out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(bundle.model_dump_legacy(), indent=2) + "\n", encoding="utf-8")
    return {
        "report_kind": "epistemap_genealogy_gedcom_import",
        "graph_path": str(target),
        "graph_id": bundle.graph_id,
        "summary": genealogy_graph_summary(bundle),
    }


def _parse_gedcom_line(line: str) -> GedcomLine:
    parts = line.split(" ", 2)
    if not parts or not parts[0].isdigit():
        raise ValueError(f"invalid GEDCOM line: {line!r}")
    level = int(parts[0])
    rest = parts[1:] if len(parts) > 1 else []
    xref = ""
    tag = ""
    value = ""
    if rest and rest[0].startswith("@") and rest[0].endswith("@"):
        xref = rest[0]
        tag_value = rest[1] if len(rest) > 1 else ""
        tag, value = _split_tag_value(tag_value)
    else:
        tag_value = " ".join(rest)
        tag, value = _split_tag_value(tag_value)
    return GedcomLine(level=level, xref=xref, tag=tag, value=value)


def _split_tag_value(text: str) -> tuple[str, str]:
    tag, _, value = text.partition(" ")
    return tag, value


def _records_by_tag(records: list[GedcomLine], tag: str) -> list[GedcomLine]:
    return [record for record in records if record.level == 0 and record.tag == tag]


def _first_child(record: GedcomLine, tag: str) -> GedcomLine | None:
    return next((child for child in record.children if child.tag == tag), None)


def _child_values(record: GedcomLine, tag: str) -> list[str]:
    return [child.value for child in record.children if child.tag == tag and child.value]


def _clean_xref(value: str) -> str:
    return value.strip().strip("@")


def _source_id(graph: str, xref: str) -> str:
    return node_id(SOURCE_NODE, graph, _clean_xref(xref))


def _person_id(graph: str, xref: str) -> str:
    return node_id(PERSON_NODE, graph, _clean_xref(xref))


def _event_id(graph: str, owner_xref: str, tag: str, index: int) -> str:
    return node_id(EVENT_NODE, graph, _clean_xref(owner_xref), tag.lower(), str(index))


def _relationship_id(graph: str, family_xref: str, relation: str, *xrefs: str) -> str:
    return node_id(RELATIONSHIP_NODE, graph, _clean_xref(family_xref), relation, *[_clean_xref(xref) for xref in xrefs])


def _source_nodes(records: list[GedcomLine], graph: str, provenance: ProvenanceRef) -> dict[str, Node]:
    nodes: dict[str, Node] = {}
    for record in _records_by_tag(records, "SOUR"):
        if not record.xref:
            continue
        title = _first_child(record, "TITL")
        author = _first_child(record, "AUTH")
        node = Node(
            id=_source_id(graph, record.xref),
            type=SOURCE_NODE,
            title=(title.value if title and title.value else record.value or record.xref),
            status="imported_unreviewed",
            provenance=[_record_provenance(provenance, record)],
            metadata={
                "gedcom_xref": record.xref,
                "author": author.value if author else "",
            },
        )
        nodes[node.id] = node
    return nodes


def _person_nodes(records: list[GedcomLine], graph: str, provenance: ProvenanceRef) -> dict[str, Node]:
    nodes: dict[str, Node] = {}
    for record in _records_by_tag(records, "INDI"):
        if not record.xref:
            continue
        name = _first_child(record, "NAME")
        sex = _first_child(record, "SEX")
        title = _display_name(name.value if name else "") or record.xref
        node = Node(
            id=_person_id(graph, record.xref),
            type=PERSON_NODE,
            title=title,
            aliases=[name.value] if name and name.value and name.value != title else [],
            status="imported_unreviewed",
            provenance=[_record_provenance(provenance, record)],
            metadata={
                "gedcom_xref": record.xref,
                "sex": sex.value if sex else "",
                "publication_status": "private_unreviewed",
            },
        )
        nodes[node.id] = node
    return nodes


def _event_nodes_and_edges(
    records: list[GedcomLine],
    graph: str,
    provenance: ProvenanceRef,
    source_nodes: dict[str, Node],
) -> tuple[list[Node], list[Edge]]:
    nodes: list[Node] = []
    edges: list[Edge] = []
    for record in _records_by_tag(records, "INDI"):
        person_id = _person_id(graph, record.xref)
        event_index = 0
        for child in record.children:
            if child.tag not in EVENT_TAGS:
                continue
            event_index += 1
            event_node = _event_node(graph, record.xref, child, event_index, provenance)
            nodes.append(event_node)
            edges.append(
                Edge(
                    id=node_id("edge", event_node.id, "about", person_id),
                    source=event_node.id,
                    target=person_id,
                    type="about_person",
                    status="imported_unreviewed",
                    provenance=[_record_provenance(provenance, child)],
                )
            )
            edges.extend(_source_support_edges(graph, child, event_node.id, source_nodes, provenance))
        edges.extend(_source_support_edges(graph, record, person_id, source_nodes, provenance))
    return nodes, edges


def _event_node(graph: str, owner_xref: str, event: GedcomLine, index: int, provenance: ProvenanceRef) -> Node:
    date = _first_child(event, "DATE")
    place = _first_child(event, "PLAC")
    kind = EVENT_TAGS[event.tag]
    title_parts = [kind]
    if date and date.value:
        title_parts.append(date.value)
    if place and place.value:
        title_parts.append(place.value)
    return Node(
        id=_event_id(graph, owner_xref, event.tag, index),
        type=EVENT_NODE,
        title=" - ".join(title_parts),
        status="imported_unreviewed",
        provenance=[_record_provenance(provenance, event)],
        metadata={
            "gedcom_tag": event.tag,
            "event_kind": kind,
            "date": date.value if date else "",
            "place": place.value if place else "",
            "raw_value": event.value,
            "publication_status": "private_unreviewed",
        },
    )


def _family_relationships(
    records: list[GedcomLine],
    graph: str,
    provenance: ProvenanceRef,
) -> tuple[list[Node], list[Edge]]:
    nodes: list[Node] = []
    edges: list[Edge] = []
    for record in _records_by_tag(records, "FAM"):
        husbands = _child_values(record, "HUSB")
        wives = _child_values(record, "WIFE")
        children = _child_values(record, "CHIL")
        for husband in husbands:
            for wife in wives:
                relationship = Node(
                    id=_relationship_id(graph, record.xref, "spouse", husband, wife),
                    type=RELATIONSHIP_NODE,
                    title="spouse relationship",
                    status="imported_unreviewed",
                    provenance=[_record_provenance(provenance, record)],
                    metadata={"gedcom_xref": record.xref, "relationship_kind": "spouse"},
                )
                nodes.append(relationship)
                edges.extend(_participant_edges(graph, relationship.id, [(husband, "spouse"), (wife, "spouse")], provenance, record))
        for parent in [*husbands, *wives]:
            for child in children:
                relationship = Node(
                    id=_relationship_id(graph, record.xref, "parent-child", parent, child),
                    type=RELATIONSHIP_NODE,
                    title="parent-child relationship",
                    status="imported_unreviewed",
                    provenance=[_record_provenance(provenance, record)],
                    metadata={"gedcom_xref": record.xref, "relationship_kind": "parent_child"},
                )
                nodes.append(relationship)
                edges.extend(
                    _participant_edges(
                        graph,
                        relationship.id,
                        [(parent, "parent"), (child, "child")],
                        provenance,
                        record,
                    )
                )
    return nodes, edges


def _participant_edges(
    graph: str,
    relationship_id: str,
    participants: list[tuple[str, str]],
    provenance: ProvenanceRef,
    record: GedcomLine,
) -> list[Edge]:
    edges: list[Edge] = []
    for xref, role in participants:
        person_id = _person_id(graph, xref)
        edges.append(
            Edge(
                id=node_id("edge", relationship_id, role, person_id),
                source=relationship_id,
                target=person_id,
                type="relationship_participant",
                status="imported_unreviewed",
                provenance=[_record_provenance(provenance, record)],
                metadata={"role": role},
            )
        )
    return edges


def _source_support_edges(
    graph: str,
    record: GedcomLine,
    target_id: str,
    source_nodes: dict[str, Node],
    provenance: ProvenanceRef,
) -> list[Edge]:
    edges: list[Edge] = []
    for index, source_xref in enumerate(_child_values(record, "SOUR"), start=1):
        source_id = _source_id(graph, source_xref)
        if source_id not in source_nodes:
            continue
        edges.append(
            Edge(
                id=node_id("edge", source_id, "supports", target_id, str(index)),
                source=source_id,
                target=target_id,
                type="supports",
                status="imported_unreviewed",
                provenance=[_record_provenance(provenance, record)],
            )
        )
    return edges


def _record_provenance(base: ProvenanceRef, record: GedcomLine) -> ProvenanceRef:
    return ProvenanceRef(
        source_id=base.source_id,
        artifact_id=base.artifact_id,
        origin_path=base.origin_path,
        support_kind=base.support_kind,
        grounding_status=base.grounding_status,
        metadata={
            "gedcom_xref": record.xref,
            "gedcom_tag": record.tag,
            "gedcom_level": record.level,
        },
    )


def _display_name(name: str) -> str:
    return " ".join(name.replace("/", "").split())
