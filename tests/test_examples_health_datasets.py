import sys
from pathlib import Path
import pandas as pd
import pytest

EX = Path(__file__).resolve().parents[1] / "examples"
for name in ("cdc_places", "cms_care_compare", "medicaid_diabetes_a1c"):
    sys.path.insert(0, str(EX / name))

import care_compare_data as cc  # noqa: E402
import medicaid_data as md  # noqa: E402
import places_data as pl  # noqa: E402


@pytest.mark.parametrize("name", ["cms_medicare", "cdc_places", "cms_care_compare", "medicaid_diabetes_a1c"])
def test_every_example_lists_sources(name):
    text = (EX / name / "SOURCES.md").read_text(encoding="utf-8")
    assert "https://" in text


def _places(rows):
    return pl.clean(pd.DataFrame(rows, columns=["year", "stateabbr", "locationid", "locationname", "measureid",
                                                "data_value", "totalpopulation"]))


def test_places_state_yearly_weights_and_balances():
    df = _places([
        (2019, "OR", "41001", "A", "DIABETES", 10, 100), (2023, "OR", "41001", "A", "DIABETES", 12, 100),
        (2019, "OR", "41003", "B", "DIABETES", 20, 300), (2023, "OR", "41003", "B", "DIABETES", 22, 300),
        (2019, "OR", "41005", "C", "DIABETES", 99, 900),  # missing in 2023 -> excluded
    ])
    s = pl.state_yearly(df, "DIABETES").set_index("year")["value"]
    assert s[2019] == pytest.approx((10 * 100 + 20 * 300) / 400)
    assert s[2023] == pytest.approx((12 * 100 + 22 * 300) / 400)


def test_places_clean_pads_fips_and_dedupes():
    df = _places([(2019, "AL", "1001", "X", "OBESITY", "30", "10"), (2019, "AL", "01001", "X", "OBESITY", "31", "10")])
    assert len(df) == 1 and df["fips"].iloc[0] == "01001"


def test_places_county_change():
    df = _places([(2019, "OR", "41001", "A", "DIABETES", 10, 100), (2023, "OR", "41001", "A", "DIABETES", 12, 100)])
    assert pl.county_change(df, "DIABETES")["abs_change"].iloc[0] == pytest.approx(2)


def _medicaid():
    base = {"measure_name": "Hemoglobin A1c", "methodology": "Administrative"}
    rows = [
        dict(base, state="Oregon", rate_definition="HbA1c in Poor Control (>9.0%)", core_set_year="2020",
             population="Medicaid", state_rate="30"),
        dict(base, state="Oregon", rate_definition="HbA1c in Poor Control (>9.0%)", core_set_year="2020",
             population="Separate CHIP (Title XXI)", state_rate="100"),
        dict(base, state="Oregon", rate_definition="HbA1c in Control (<8.0%)", core_set_year="2020",
             population="Medicaid", state_rate="60"),
        dict(base, state="Oregon", rate_definition="HbA1c in Poor Control (>9.0%)", core_set_year="2020",
             population="Medicaid", state_rate="DS"),
        dict(base, state="Guam", rate_definition="HbA1c in Poor Control (>9.0%)", core_set_year="2020",
             population="Medicaid", state_rate="40"),
    ]
    return md.clean(pd.DataFrame(rows))


def test_medicaid_clean_filters():
    df = _medicaid()
    assert len(df) == 1 and df["state"].iloc[0] == "OR" and df["rate"].iloc[0] == 30
    assert md.state_yearly(df)["rate"].iloc[0] == 30


def test_care_compare_clean_and_state_summary():
    info = pd.DataFrame({
        "facility_id": ["1", "2", "3"], "facility_name": list("abc"), "state": ["AL", "AL", "AK"],
        "hospital_type": ["Acute"] * 3, "hospital_ownership": ["Gov"] * 3,
        "hospital_overall_rating": ["4", "2", "Not Available"]})
    readm = pd.DataFrame({"facility_id": ["1", "2"], "score": ["16", "Not Available"]})
    df = cc.clean(info, readm)
    s = cc.state_summary(df).set_index("state")
    assert s.loc["AL", "mean_stars"] == 3 and s.loc["AL", "pct_4_5_star"] == 50
    assert s.loc["AL", "mean_readmission_rate"] == 16
    assert "AK" not in s.index
