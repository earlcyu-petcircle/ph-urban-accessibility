"""The single entry point: ``mma <command>``.

``mma check`` validates config.toml. ``mma collect``, ``build``, ``analyse`` and
``publish`` run one stage each, and ``mma all`` runs them in order, stopping at the first
stage that fails or is not built yet.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from types import ModuleType

from mma import __version__, s1_collect, s2_build, s3_analyse, s4_publish
from mma.shared.config import ConfigError, StudyConfig, load_config, load_homes
from mma.shared.paths import Paths
from mma.shared.stages import StageNotBuilt

STAGE_MODULES: tuple[ModuleType, ...] = (s1_collect, s2_build, s3_analyse, s4_publish)
STAGES: dict[str, Callable[[StudyConfig, Paths], None]] = {m.NAME: m.run for m in STAGE_MODULES}


def _summary(module: ModuleType) -> str:
    return (module.__doc__ or "").strip().splitlines()[0]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mma",
        description="Walking access to everyday services in three Metro Manila barangays.",
    )
    parser.add_argument("--version", action="version", version=f"mma {__version__}")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.toml"),
        help="study configuration (default: ./config.toml)",
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="command")
    commands.add_parser("check", help="validate config.toml and list the study barangays")
    for module in STAGE_MODULES:
        commands.add_parser(module.NAME, help=_summary(module))
    commands.add_parser("all", help="run every stage in order")
    return parser


def _check(config: StudyConfig, paths: Paths, n_homes: int) -> None:
    w = config.walking
    distances = ", ".join(f"{w.metres(m):,.0f}" for m in w.thresholds_min)
    minutes = ", ".join(str(m) for m in w.thresholds_min)
    print("config.toml is valid")
    print("study barangays:")
    for b in config.barangays:
        print(f"  {b.pcode}  {b.label}, {b.city}")
    print(f"walking: {w.speed_kmh} km/h; {minutes} min = {distances} m")
    print(f"services: {len(config.categories)} categories")
    home = "found" if paths.home_file.exists() else "not found, home lens skipped"
    print(f"home lens: {n_homes} private points ({paths.home_file.name} {home})")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
        paths = Paths.for_config(args.config)
        homes = load_homes(paths.home_file, config)
    except FileNotFoundError:
        print(f"mma: config not found: {args.config}", file=sys.stderr)
        return 1
    except ConfigError as err:
        print(f"mma: {err}", file=sys.stderr)
        return 1

    if args.command == "check":
        _check(config, paths, len(homes))
        return 0

    names = list(STAGES) if args.command == "all" else [args.command]
    for name in names:
        try:
            STAGES[name](config, paths)
        except StageNotBuilt as err:
            print(f"mma: {err}", file=sys.stderr)
            return 2
    return 0
