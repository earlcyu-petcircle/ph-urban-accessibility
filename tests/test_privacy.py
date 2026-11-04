"""Home locations are private: they must never be committed or required."""

from __future__ import annotations

import shutil

import pytest

from mma.shared.config import ConfigError, load_config, load_homes


def test_home_file_is_gitignored(repo):
    ignored = (repo / ".gitignore").read_text().splitlines()
    assert "home.local.toml" in ignored


def test_home_lens_is_optional(repo, tmp_path):
    config = load_config(repo / "config.toml")
    assert load_homes(tmp_path / "home.local.toml", config) == ()


def test_home_points_must_sit_in_a_study_barangay(repo, tmp_path):
    shutil.copy(repo / "config.toml", tmp_path / "config.toml")
    config = load_config(tmp_path / "config.toml")
    home = tmp_path / "home.local.toml"
    home.write_text('[[homes]]\npcode = "PH1307404055"\nlat = 0.0\nlon = 0.0\n')
    assert [h.pcode for h in load_homes(home, config)] == ["PH1307404055"]
    home.write_text('[[homes]]\npcode = "PH1376000000"\nlat = 0.0\nlon = 0.0\n')
    with pytest.raises(ConfigError, match="not a study barangay"):
        load_homes(home, config)
