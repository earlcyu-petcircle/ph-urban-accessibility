"""Home locations are private: the folder that holds them is never committed or published."""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src" / "shared"))

import common


def test_home_points_live_in_the_manual_folder():
    assert common.HOMES_FILE.relative_to(REPO).as_posix() == "data/manual/homes.csv"


def test_manual_folder_is_gitignored():
    assert "data/manual/" in (REPO / ".gitignore").read_text().splitlines()
    check = subprocess.run(["git", "check-ignore", "-q", "data/manual/homes.csv"], cwd=REPO)
    assert check.returncode == 0


def test_no_home_points_file_is_tracked():
    tracked = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True).stdout
    assert not [p for p in tracked.splitlines() if Path(p).name.startswith("homes")]


def test_only_barangays_are_named_as_study_places():
    assert set(common.BARANGAYS) == {"PH1303901136", "PH1307404055", "PH1307403013"}
    for place in common.BARANGAYS.values():
        assert set(place) <= {"name", "district", "city", "lived"}
