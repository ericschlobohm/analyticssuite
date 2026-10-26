import pandas as pd
import pytest

from snowflake_analytics_agents import cms_medicare as cms


def _gpci(year, work, pe, mp):
    return pd.DataFrame(
        {"state": ["OR"], "locality": [0], "locality_name": ["OREGON"],
         "gpci_work": [work], "gpci_pe": [pe], "gpci_mp": [mp], "year": [year]}
    )


def test_gaf_weights_sum_to_one():
    assert sum(cms.GAF_WEIGHTS.values()) == pytest.approx(1.0, abs=1e-4)
    assert cms.compute_gaf(_gpci(2022, 1, 1, 1))["gaf"].iloc[0] == pytest.approx(1.0, abs=1e-4)


def test_payment_formula():
    rvu = pd.DataFrame(
        {"hcpcs": ["99214"], "modifier": [None], "description": ["x"], "work_rvu": [2.0],
         "pe_rvu_nonfac": [1.0], "pe_rvu_fac": [0.5], "mp_rvu": [0.1], "year": [2024],
         "conversion_factor": [30.0]}
    )
    out = cms.compute_payments(_gpci(2024, 1.1, 0.9, 0.5), rvu)
    assert out["national_payment"].iloc[0] == pytest.approx((2.0 + 1.0 + 0.1) * 30)
    assert out["payment"].iloc[0] == pytest.approx((2.0 * 1.1 + 1.0 * 0.9 + 0.1 * 0.5) * 30)


def test_common_localities_drops_retired():
    df = pd.concat([_gpci(2022, 1, 1, 1), _gpci(2023, 1, 1, 1)])
    df = pd.concat([df, _gpci(2022, 1, 1, 1).assign(locality=9)])
    out = cms.common_localities(df)
    assert set(out["locality"]) == {0}


def test_change_summary_ranks_by_pct_change():
    yearly = pd.DataFrame(
        {"state": ["A", "A", "B", "B"], "year": [2022, 2026, 2022, 2026], "gaf": [1.0, 1.1, 1.0, 0.9]}
    )
    s = cms.change_summary(yearly, "gaf")
    assert list(s["state"]) == ["A", "B"]
    assert s["pct_change"].iloc[0] == pytest.approx(10.0)
    assert s["pct_change"].iloc[1] == pytest.approx(-10.0)
