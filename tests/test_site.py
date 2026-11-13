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


def test_no_personal_wording_on_the_site():
    label = json.loads((DOCS / "map" / "data" / "summary.json").read_text())["featured"]["label"]
    for text in (PAGE, label):
        assert "lived" not in text.lower()


def test_pick_outlines_sit_on_a_white_halo():
    halo, outline = PAGE.index('id: "picked-halo"'), PAGE.index('id: "picked",')
    assert halo < outline
