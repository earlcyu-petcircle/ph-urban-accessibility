"""Stage 4, publish: tables, figures, map tiles and the story site.

Arrives in PR 4. It will write results/tables/ and results/figures/, build PMTiles with
tippecanoe for the MapLibre map in docs/map/, and refresh the numbers the story page in
docs/index.html quotes. No home location is ever written by this stage.
"""

from __future__ import annotations

from mma.shared.config import StudyConfig
from mma.shared.paths import Paths
from mma.shared.stages import StageNotBuilt

NUMBER, NAME, PR = 4, "publish", 4


def run(config: StudyConfig, paths: Paths) -> None:
    raise StageNotBuilt(NUMBER, NAME, PR)
