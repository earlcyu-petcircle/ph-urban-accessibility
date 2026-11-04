"""Where each stage reads and writes, relative to the folder holding config.toml."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Paths:
    root: Path

    @classmethod
    def for_config(cls, config_path: Path) -> Paths:
        return cls(root=config_path.resolve().parent)

    @property
    def raw(self) -> Path:
        """Downloads from stage 1 (gitignored)."""
        return self.root / "data" / "raw"

    @property
    def work(self) -> Path:
        """Intermediate tables from stages 2 and 3 (gitignored)."""
        return self.root / "data" / "work"

    @property
    def derived(self) -> Path:
        """Small analysis tables that are committed."""
        return self.root / "data" / "derived"

    @property
    def results(self) -> Path:
        """Tables and figures from stage 3."""
        return self.root / "results"

    @property
    def docs(self) -> Path:
        """The story site and web map served by GitHub Pages."""
        return self.root / "docs"

    @property
    def home_file(self) -> Path:
        """Private home locations for the home lens (gitignored, never committed)."""
        return self.root / "home.local.toml"
