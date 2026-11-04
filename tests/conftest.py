from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def repo() -> Path:
    return REPO


@pytest.fixture
def config_data() -> dict:
    with (REPO / "config.toml").open("rb") as f:
        return tomllib.load(f)
