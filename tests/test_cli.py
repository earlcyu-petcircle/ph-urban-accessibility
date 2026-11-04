from __future__ import annotations

import pytest

from mma.cli import STAGES, main


def test_stages_run_in_design_order():
    assert list(STAGES) == ["collect", "build", "analyse", "publish"]


def test_check_lists_the_three_barangays(repo, capsys):
    assert main(["--config", str(repo / "config.toml"), "check"]) == 0
    out = capsys.readouterr().out
    assert "Barangay 136 (Tondo), City of Manila" in out
    assert "Loyola Heights, Quezon City" in out
    assert "Oranbo, City of Pasig" in out
    assert "5, 10, 15, 20 min = 350, 700, 1,050, 1,400 m" in out


@pytest.mark.parametrize(("command", "pr"), [("collect", 2), ("build", 2), ("analyse", 3), ("publish", 4)])
def test_unbuilt_stage_names_the_pr_that_brings_it(repo, capsys, command, pr):
    assert main(["--config", str(repo / "config.toml"), command]) == 2
    assert f"arrives in PR {pr}" in capsys.readouterr().err


def test_all_stops_at_the_first_unbuilt_stage(repo, capsys):
    assert main(["--config", str(repo / "config.toml"), "all"]) == 2
    err = capsys.readouterr().err
    assert "stage 1 (collect)" in err
    assert "stage 2" not in err


def test_missing_config_is_a_clear_error(tmp_path, capsys):
    assert main(["--config", str(tmp_path / "nope.toml"), "check"]) == 1
    assert "config not found" in capsys.readouterr().err
