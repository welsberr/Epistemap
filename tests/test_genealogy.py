from __future__ import annotations

import json
import sys

from epistemap import gedcom_to_graph_bundle
from epistemap.cli import main


SIMPLE_GEDCOM = """0 HEAD
1 SOUR Test
0 @S1@ SOUR
1 TITL Family Bible
0 @I1@ INDI
1 NAME Robert /Blackwood/
1 SEX M
1 BIRT
2 DATE ABT 1788
2 PLAC Ireland
2 SOUR @S1@
0 @I2@ INDI
1 NAME Mary /Craig/
1 SEX F
0 @I3@ INDI
1 NAME Samuel /Blackwood/
1 SEX M
0 @F1@ FAM
1 HUSB @I1@
1 WIFE @I2@
1 CHIL @I3@
0 TRLR
"""


def test_gedcom_to_graph_bundle_imports_people_events_sources_and_relationships(tmp_path) -> None:
    gedcom_path = tmp_path / "blackwood.ged"
    gedcom_path.write_text(SIMPLE_GEDCOM, encoding="utf-8")

    bundle = gedcom_to_graph_bundle(gedcom_path, graph_id="blackwood-test")

    nodes_by_type = {}
    for node in bundle.nodes:
        nodes_by_type.setdefault(node.type, []).append(node)
    edges_by_type = {}
    for edge in bundle.edges:
        edges_by_type.setdefault(edge.type, []).append(edge)

    assert bundle.metadata["publication_status"] == "private_unreviewed"
    assert len(nodes_by_type["person_candidate"]) == 3
    assert len(nodes_by_type["source_record"]) == 1
    assert len(nodes_by_type["event_claim"]) == 1
    assert len(nodes_by_type["relationship_claim"]) == 3
    assert nodes_by_type["person_candidate"][0].status == "imported_unreviewed"
    assert any(node.title == "Robert Blackwood" for node in nodes_by_type["person_candidate"])
    assert any(edge.type == "supports" for edge in bundle.edges)
    assert len(edges_by_type["relationship_participant"]) == 6


def test_cli_genealogy_gedcom_writes_graph(tmp_path, monkeypatch, capsys) -> None:
    gedcom_path = tmp_path / "blackwood.ged"
    graph_path = tmp_path / "epistemap_graph.json"
    gedcom_path.write_text(SIMPLE_GEDCOM, encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "epistemap",
            "genealogy-gedcom",
            str(gedcom_path),
            "--graph-id",
            "blackwood-cli",
            "--out",
            str(graph_path),
        ],
    )

    main()

    payload = json.loads(capsys.readouterr().out)
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    assert payload["report_kind"] == "epistemap_genealogy_gedcom_import"
    assert payload["summary"]["nodes_person_candidate"] == 3
    assert graph["graph_id"] == "blackwood-cli"
    assert graph["metadata"]["domain"] == "genealogy"
