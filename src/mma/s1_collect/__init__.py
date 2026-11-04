"""Stage 1, collect: download and cache the raw sources into data/raw/.

Arrives in PR 2. It will fetch, and reuse when already present:

- OCHA COD-AB barangay boundaries (HDX)
- WorldPop constrained 100 m population for 2024 (HDX), and GHS-POP for the check
- Overture Maps places and buildings for the study box, via the ``overturemaps`` downloader
- the Geofabrik OpenStreetMap extract for the Philippines, clipped to Metro Manila plus the fringe
- the Healthsites.io and education-facility layers (HDX)

The PSA 2024 census workbooks and the DOH registry block scripted downloads; this stage
checks they have been saved by hand and says where to put them if not.
"""

from __future__ import annotations

from mma.shared.config import StudyConfig
from mma.shared.paths import Paths
from mma.shared.stages import StageNotBuilt

NUMBER, NAME, PR = 1, "collect", 2


def run(config: StudyConfig, paths: Paths) -> None:
    raise StageNotBuilt(NUMBER, NAME, PR)
