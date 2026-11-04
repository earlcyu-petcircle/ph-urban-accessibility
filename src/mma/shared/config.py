"""Load and validate config.toml, the single home of every study parameter.

Validation is deliberately strict: a typo in a threshold or a barangay code should stop
the pipeline before it downloads anything, not surface as a strange number three stages
later. Home locations are read from a separate, gitignored file (see ``load_homes``).
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Any

PCODE = re.compile(r"^PH\d{10}$")
FUNCTIONS = ("supplying", "caring", "learning", "enjoying", "moving")


class ConfigError(ValueError):
    """config.toml or home.local.toml does not match the research design."""


@dataclass(frozen=True)
class Barangay:
    pcode: str
    name: str
    city: str
    lived: str
    district: str | None = None

    @property
    def label(self) -> str:
        return f"{self.name} ({self.district})" if self.district else self.name


@dataclass(frozen=True)
class Walking:
    speed_kmh: float
    thresholds_min: tuple[int, ...]
    sufficiency_min: int
    check_walkshed_min: tuple[int, ...]

    def metres(self, minutes: float, speed_kmh: float | None = None) -> float:
        """Distance walked in ``minutes`` at ``speed_kmh`` (the study speed by default)."""
        return (speed_kmh or self.speed_kmh) * 1000 / 60 * minutes


@dataclass(frozen=True)
class Transit:
    low_capacity_m: int
    high_capacity_m: int
    jeepney_routes_count_as_stops: bool


@dataclass(frozen=True)
class StudyConfig:
    barangays: tuple[Barangay, ...]
    walking: Walking
    transit: Transit
    services: dict[str, tuple[str, ...]]
    measures: dict[str, Any]
    area: dict[str, Any]
    sources: dict[str, Any]
    sensitivity: dict[str, tuple[Any, ...]]

    @property
    def categories(self) -> tuple[str, ...]:
        """The service categories in basket order."""
        return tuple(c for f in FUNCTIONS for c in self.services[f])


def _require(table: dict[str, Any], key: str, where: str) -> Any:
    if key not in table:
        raise ConfigError(f"{where}: missing '{key}'")
    return table[key]


def _increasing(values: list[int], where: str) -> tuple[int, ...]:
    if not values or any(b <= a for a, b in pairwise(values)):
        raise ConfigError(f"{where}: must be a non-empty, strictly increasing list")
    return tuple(values)


def parse_config(data: dict[str, Any]) -> StudyConfig:
    rows = _require(data, "barangays", "config")
    barangays = []
    for i, row in enumerate(rows):
        where = f"barangays[{i}]"
        pcode = _require(row, "pcode", where)
        if not PCODE.match(pcode):
            raise ConfigError(f"{where}: pcode '{pcode}' is not a PSGC code like PH1303901136")
        barangays.append(
            Barangay(
                pcode=pcode,
                name=_require(row, "name", where),
                city=_require(row, "city", where),
                lived=_require(row, "lived", where),
                district=row.get("district"),
            )
        )
    if len({b.pcode for b in barangays}) != len(barangays):
        raise ConfigError("barangays: each pcode must appear once")

    w = _require(data, "walking", "config")
    walking = Walking(
        speed_kmh=float(_require(w, "speed_kmh", "walking")),
        thresholds_min=_increasing(_require(w, "thresholds_min", "walking"), "walking.thresholds_min"),
        sufficiency_min=int(_require(w, "sufficiency_min", "walking")),
        check_walkshed_min=_increasing(
            _require(w, "check_walkshed_min", "walking"), "walking.check_walkshed_min"
        ),
    )
    if walking.speed_kmh <= 0:
        raise ConfigError("walking.speed_kmh: must be positive")
    if walking.sufficiency_min not in walking.thresholds_min:
        raise ConfigError("walking.sufficiency_min: must be one of walking.thresholds_min")

    t = _require(data, "transit", "config")
    transit = Transit(
        low_capacity_m=int(_require(t, "low_capacity_m", "transit")),
        high_capacity_m=int(_require(t, "high_capacity_m", "transit")),
        jeepney_routes_count_as_stops=bool(_require(t, "jeepney_routes_count_as_stops", "transit")),
    )

    s = _require(data, "services", "config")
    services = {f: tuple(_require(s, f, "services")) for f in FUNCTIONS}
    extra = set(s) - set(FUNCTIONS)
    if extra:
        raise ConfigError(f"services: unknown functions {sorted(extra)}")
    flat = [c for f in FUNCTIONS for c in services[f]]
    if len(set(flat)) != len(flat):
        raise ConfigError("services: each category must appear under one function only")

    sensitivity = {k: tuple(v) for k, v in data.get("sensitivity", {}).items()}
    if "speed_kmh" in sensitivity and walking.speed_kmh not in sensitivity["speed_kmh"]:
        raise ConfigError("sensitivity.speed_kmh: must include walking.speed_kmh")

    return StudyConfig(
        barangays=tuple(barangays),
        walking=walking,
        transit=transit,
        services=services,
        measures=dict(_require(data, "measures", "config")),
        area=dict(_require(data, "area", "config")),
        sources=dict(_require(data, "sources", "config")),
        sensitivity=sensitivity,
    )


def load_config(path: Path) -> StudyConfig:
    with path.open("rb") as f:
        return parse_config(tomllib.load(f))


@dataclass(frozen=True)
class Home:
    pcode: str
    lat: float
    lon: float


def load_homes(path: Path, config: StudyConfig) -> tuple[Home, ...]:
    """Read the private home points for the home lens, if the file exists.

    The file is gitignored and holds one ``[[homes]]`` table per study barangay with
    ``pcode``, ``lat`` and ``lon``. Without it the home lens is simply skipped.
    """
    if not path.exists():
        return ()
    with path.open("rb") as f:
        rows = tomllib.load(f).get("homes", [])
    known = {b.pcode for b in config.barangays}
    homes = []
    for i, row in enumerate(rows):
        where = f"homes[{i}]"
        pcode = _require(row, "pcode", where)
        if pcode not in known:
            raise ConfigError(f"{where}: pcode '{pcode}' is not a study barangay")
        homes.append(
            Home(pcode=pcode, lat=float(_require(row, "lat", where)), lon=float(_require(row, "lon", where)))
        )
    return tuple(homes)
