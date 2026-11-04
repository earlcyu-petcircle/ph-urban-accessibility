"""Stage 2, build: people, services and the walking network as GeoParquet in data/work/.

Arrives in PR 2. It will:

- place people: 2024 census barangay totals spread over WorldPop cells, then over
  residential building footprints, so every building in a study barangay is an origin
- build the nine-category service layer from Overture and OpenStreetMap, drop closed and
  low-confidence places, merge duplicates, and match public facilities to the registries
- build the OpenStreetMap walking network: pedestrian ways in both directions, largest
  connected component, expressways out, footbridges and stairs in
"""

from __future__ import annotations

from mma.shared.config import StudyConfig
from mma.shared.paths import Paths
from mma.shared.stages import StageNotBuilt

NUMBER, NAME, PR = 2, "build", 2


def run(config: StudyConfig, paths: Paths) -> None:
    raise StageNotBuilt(NUMBER, NAME, PR)
