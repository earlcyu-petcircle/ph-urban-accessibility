#!/usr/bin/env python3
"""
Write docs/map/palette.js, the web map's classes and colours, from src/shared/map_layers.py, so
the map page and the static charts share one palette (the Atlas data palette, Riso, in
src/shared/atlas.py). The tiles carry values, not colours, so a palette change needs only this
file. Run by 04_build_map.sh; also runs on its own:
  .venv/bin/python src/04_build_map/write_web_palette.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))

import map_layers as ml

OUT = Path(__file__).resolve().parents[2] / "docs" / "map" / "palette.js"

PALETTE = {
    "CODES": ml.CODES,
    "UNSCORED": ml.UNSCORED,
    "SCORE_BREAKS": ml.SCORE_BREAKS,
    "SCORE": ml.SCORE,
    "MINUTE_BREAKS": ml.MINUTE_BREAKS,
    "MINUTES": ml.MINUTES,
    "SLOTS": ml.SLOTS,
    "SERVICE": ml.SERVICE,
    "TRANSIT": ml.TRANSIT,
    "NO_PEOPLE": ml.NO_PEOPLE,
}

lines = ["// Written by src/04_build_map/write_web_palette.py from src/shared/map_layers.py; do not edit."]
lines += [f"const {name} = {json.dumps(value)};" for name, value in PALETTE.items()]
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(lines) + "\n")
print(f"wrote {OUT.relative_to(OUT.parents[2])}")
