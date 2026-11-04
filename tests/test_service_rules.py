"""The rules that sort places into service categories and tell duplicates apart."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "shared"))

from service_rules import health_category, norm_name, same_place, school_level


def same(a, b):
    return same_place(norm_name(a), norm_name(b))


def test_one_school_under_two_names():
    assert same("DepEd Licerio Geronimo ES", "Licerio Geronimo Elementary School")
    assert same("Pasay City North HS - M. Dela Cruz", "Pasay City North High School")


def test_two_shops_are_not_one():
    assert not same("7-Eleven", "Ministop")
    assert not same("Mercury Drug", "Watsons")


def test_a_missing_name_never_contradicts():
    assert same(None, "Puregold")


def test_school_level_from_name_and_tag():
    names = pd.Series(["Balara Elementary School", "Camarin High School", "Kanawan Integrated School", "Ateneo"])
    assert list(school_level(names)) == ["elementary", "high", "integrated", None]
    isced = pd.Series(["", "", "", "1;2;3"])
    assert school_level(names, isced)[3] == "integrated"


def test_health_categories():
    names = pd.Series(
        [
            "Philippine General Hospital",  # a hospital in OpenStreetMap
            "ENT OPD St. Martin de Porres Hospital",  # a hospital department listed by Overture
            "Labayani Pediatric Clinic",  # a clinic filed as a hospital
            "Kamuning Health Center",
            "Happy Paws Animal Hospital",
            "Smile Dental Clinic",
        ]
    )
    hospital_tag = pd.Series([True, True, True, False, True, False])
    primary_tag = pd.Series([False, False, False, True, False, True])
    overture = health_category(names, hospital_tag, primary_tag, trust_hospital_tag=False)
    assert list(overture) == ["hospital", None, "primary_care", "primary_care", None, None]
