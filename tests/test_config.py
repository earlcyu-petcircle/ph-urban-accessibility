from __future__ import annotations

import copy

import pytest

from mma.shared.config import ConfigError, load_config, parse_config


def test_repo_config_matches_the_design(repo):
    config = load_config(repo / "config.toml")
    assert [b.pcode for b in config.barangays] == ["PH1303901136", "PH1307404055", "PH1307403013"]
    assert config.barangays[0].label == "Barangay 136 (Tondo)"
    assert len(config.categories) == 9
    assert config.walking.sufficiency_min == 10
    assert (config.transit.low_capacity_m, config.transit.high_capacity_m) == (500, 1000)


def test_thresholds_convert_to_the_documented_distances(repo):
    walking = load_config(repo / "config.toml").walking
    assert [round(walking.metres(m)) for m in walking.thresholds_min] == [350, 700, 1050, 1400]


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda d: d["barangays"][0].update(pcode="136"), "not a PSGC code"),
        (lambda d: d["barangays"][1].update(pcode="PH1303901136"), "each pcode must appear once"),
        (lambda d: d["walking"].update(thresholds_min=[5, 15, 10]), "strictly increasing"),
        (lambda d: d["walking"].update(sufficiency_min=12), "must be one of"),
        (lambda d: d["walking"].update(speed_kmh=0), "must be positive"),
        (lambda d: d["services"]["caring"].append("pharmacy"), "one function only"),
        (lambda d: d["sensitivity"].update(speed_kmh=[3.6, 4.8]), "must include"),
    ],
)
def test_invalid_config_is_refused(config_data, change, message):
    data = copy.deepcopy(config_data)
    change(data)
    with pytest.raises(ConfigError, match=message):
        parse_config(data)
