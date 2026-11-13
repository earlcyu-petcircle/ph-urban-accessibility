"""The site is one map-first page: it loads files that exist, and old /map/ links still land on it."""

import json
import re
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / "docs"
PAGE = (DOCS / "index.html").read_text()


def test_every_local_file_the_page_loads_exists():
    local = set(re.findall(r'(?:src|href)="(map/[^"#?]+)"', PAGE))
    local |= set(re.findall(r'(?:fetch|here)\("(map/[^"]+)"\)', PAGE))
    local |= set(re.findall(r'data: "(map/[^"]+)"', PAGE))
    assert {"map/palette.js", "map/data/summary.json", "map/data/barangays.json"} <= local
    assert [p for p in sorted(local) if not (DOCS / p).is_file()] == []


def test_old_map_links_forward_to_the_front_page_with_their_picks():
    forward = (DOCS / "map" / "index.html").read_text()
    assert 'location.replace("../" + location.hash)' in forward


def test_the_examples_are_explained_once_in_a_note_not_on_the_button():
    label = json.loads((DOCS / "map" / "data" / "summary.json").read_text())["featured"]["label"]
    assert "lived" not in label.lower()
    note = "The examples are three barangays I have lived in: Barangay 136, Loyola Heights and Oranbo."
    assert f'<p class="note">{note}</p>' in PAGE and PAGE.lower().count("lived") == 1


def test_pick_outlines_sit_on_a_white_halo():
    halo, outline = PAGE.index('id: "picked-halo"'), PAGE.index('id: "picked",')
    assert halo < outline


def test_jollibee_is_listed_once_as_a_service_outside_the_score():
    palette = (DOCS / "map" / "palette.js").read_text()
    assert '"jollibee": "jb"' in palette and 'const UNSCORED = ["jb"];' in palette
    assert "show-jb" not in PAGE and "jollibee.geojson" not in PAGE
    assert not (DOCS / "map" / "data" / "jollibee.geojson").exists()
    assert "not in score" in PAGE
    # picked, it is marked in neutral grey, not the yellow kept for the nine and the title
    assert "tr.on[data-unscored] td{background:var(--quiet)}" in PAGE and "--quiet:#F2F3F5" in PAGE
    records = json.loads((DOCS / "map" / "data" / "barangays.json").read_text())
    assert all("jb" in r["min"] and "jb" in r["k"] and "jb" in r["x"] and "jb" not in r for r in records)
