"""Stage 3, analyse: walking times, the five measures and the sensitivity checks.

Arrives in PR 3. It will:

- run one multi-source shortest-path pass per category for the nearest service, and a
  second pass for counts within each threshold
- compute M1 (nearest walk), M2 (choice), M3 (E2SFCA), M4 (15-minute coverage) and
  M5 (SDG 11.2.1 transit) per origin, then summarise per barangay over residents
- run the ten sensitivity checks and the service, registry and street-imagery audits,
  including the sari-sari count per kilometre of sampled route
"""

from __future__ import annotations

from mma.shared.config import StudyConfig
from mma.shared.paths import Paths
from mma.shared.stages import StageNotBuilt

NUMBER, NAME, PR = 3, "analyse", 3


def run(config: StudyConfig, paths: Paths) -> None:
    raise StageNotBuilt(NUMBER, NAME, PR)
