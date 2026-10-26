"""Medicare Physician Fee Schedule (PFS) data: GPCI/GAF by locality and procedure payments.

Source: CMS PFS Relative Value Files (https://www.cms.gov/medicare/payment/fee-schedules/physician/pfs-relative-value-files).
Each yearly zip contains the GPCI addendum (Addendum E) and the national RVU file with the conversion factor.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd
import requests

YEARS = [2022, 2023, 2024, 2025, 2026]

# Final (latest) RVU release zip for each calendar year.
CMS_ZIP_URLS = {
    2022: "https://www.cms.gov/files/zip/rvu22d.zip",
    2023: "https://www.cms.gov/files/zip/rvu23d.zip",
    2024: "https://www.cms.gov/files/zip/rvu24d.zip",
    2025: "https://www.cms.gov/files/zip/rvu25d-updated-09/11/2025.zip",
    2026: "https://www.cms.gov/files/zip/rvu26d-updated-08-26-2026.zip",
}

# Fixed national cost-share weights so GAF changes reflect GPCI changes only.
GAF_WEIGHTS = {"pw": 0.50866, "pe": 0.44839, "mp": 0.04295}

# Procedure -> (description, payment setting used for the dashboard).
PROCEDURES = {
    "99213": ("Office visit, established, low", "non-facility"),
    "99214": ("Office visit, established, moderate", "non-facility"),
    "99203": ("Office visit, new, low", "non-facility"),
    "93000": ("Electrocardiogram, complete", "non-facility"),
    "71046": ("Chest X-ray, 2 views", "non-facility"),
    "73721": ("MRI lower extremity joint w/o contrast", "non-facility"),
    "90837": ("Psychotherapy, 60 min", "non-facility"),
    "97110": ("Therapeutic exercise, 15 min", "non-facility"),
    "99285": ("Emergency visit, high severity", "facility"),
    "45378": ("Diagnostic colonoscopy", "facility"),
    "66984": ("Cataract surgery with IOL", "facility"),
    "29881": ("Knee arthroscopy, meniscectomy", "facility"),
    "27447": ("Total knee replacement", "facility"),
}

_UA = {"User-Agent": "Mozilla/5.0"}


def download_year(year: int, raw_dir: Path) -> Path:
    """Download and extract one year's RVU zip (cached); returns the extraction directory."""
    target = raw_dir / f"rvu{year}"
    if target.exists() and any(target.glob("*GPCI*.csv")):
        return target
    raw_dir.mkdir(parents=True, exist_ok=True)
    resp = requests.get(CMS_ZIP_URLS[year], headers=_UA, timeout=120)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        zf.extractall(target)
    return target


def _find(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No file matching {pattern} in {directory}")
    return matches[0]


def load_gpci(directory: Path, year: int) -> pd.DataFrame:
    """Parse Addendum E into one row per locality with PW/PE/MP GPCIs."""
    raw = pd.read_csv(
        _find(directory, "GPCI*.csv"), skiprows=3, header=None, dtype=str, encoding="latin1"
    )
    raw = raw.iloc[:, :7]
    raw.columns = ["mac", "state", "locality", "locality_name", "gpci_work", "gpci_pe", "gpci_mp"]
    raw["state"] = raw["state"].str.strip()
    raw = raw[raw["state"].str.fullmatch(r"[A-Z]{2}", na=False)].copy()
    raw["locality"] = raw["locality"].str.strip().astype(int)
    raw["locality_name"] = raw["locality_name"].str.replace(r"\*+", "", regex=True).str.strip()
    for col in ("gpci_work", "gpci_pe", "gpci_mp"):
        raw[col] = pd.to_numeric(raw[col])
    raw["year"] = year
    return raw.drop(columns="mac").reset_index(drop=True)


def compute_gaf(df: pd.DataFrame) -> pd.DataFrame:
    """Add the weighted Geographic Adjustment Factor (GAF) column."""
    out = df.copy()
    out["gaf"] = (
        GAF_WEIGHTS["pw"] * out["gpci_work"]
        + GAF_WEIGHTS["pe"] * out["gpci_pe"]
        + GAF_WEIGHTS["mp"] * out["gpci_mp"]
    )
    return out


def load_rvu(directory: Path, year: int) -> tuple[pd.DataFrame, float]:
    """Return RVUs for the selected procedures and the year's conversion factor."""
    path = sorted(directory.glob("PPRRVU*.csv"))
    # 2026 ships QPP/non-QPP files; use the non-QPP conversion factor.
    path = [p for p in path if "nonqpp" in p.name.lower()] or path
    raw = pd.read_csv(path[0], skiprows=9, dtype=str, encoding="latin1")
    cf = float(raw["FACTOR"].dropna().iloc[0])
    rvu = raw.iloc[:, [0, 1, 2, 5, 6, 8, 10]].copy()
    rvu.columns = ["hcpcs", "modifier", "description", "work_rvu", "pe_rvu_nonfac", "pe_rvu_fac", "mp_rvu"]
    rvu = rvu[rvu["hcpcs"].isin(PROCEDURES) & rvu["modifier"].isna()].copy()
    for col in ("work_rvu", "pe_rvu_nonfac", "pe_rvu_fac", "mp_rvu"):
        rvu[col] = pd.to_numeric(rvu[col])
    rvu["year"] = year
    rvu["conversion_factor"] = cf
    return rvu.reset_index(drop=True), cf


def compute_payments(gpci: pd.DataFrame, rvu: pd.DataFrame) -> pd.DataFrame:
    """Locality-adjusted payment per procedure: (W*PW + PE*PE_GPCI + MP*MP_GPCI) * CF."""
    merged = gpci.merge(rvu, on="year")
    merged["setting"] = merged["hcpcs"].map(lambda h: PROCEDURES[h][1])
    merged["description"] = merged["hcpcs"].map(lambda h: PROCEDURES[h][0])
    pe = merged["pe_rvu_nonfac"].where(merged["setting"] == "non-facility", merged["pe_rvu_fac"])
    merged["national_payment"] = (merged["work_rvu"] + pe + merged["mp_rvu"]) * merged["conversion_factor"]
    merged["payment"] = (
        merged["work_rvu"] * merged["gpci_work"]
        + pe * merged["gpci_pe"]
        + merged["mp_rvu"] * merged["gpci_mp"]
    ) * merged["conversion_factor"]
    cols = [
        "year", "state", "locality", "locality_name", "hcpcs", "description", "setting",
        "work_rvu", "conversion_factor", "national_payment", "payment",
    ]
    return merged[cols]


def common_localities(df: pd.DataFrame) -> pd.DataFrame:
    """Restrict to localities present in every year so comparisons are like-for-like."""
    n_years = df["year"].nunique()
    counts = df.groupby(["state", "locality"])["year"].nunique()
    keep = counts[counts == n_years].index
    idx = pd.MultiIndex.from_frame(df[["state", "locality"]])
    return df[idx.isin(keep)].copy()


def latest_names(df: pd.DataFrame) -> pd.DataFrame:
    """Latest-year name per locality, to keep labels stable across years."""
    last = df[df["year"] == df["year"].max()][["state", "locality", "locality_name"]].drop_duplicates()
    return df.drop(columns="locality_name").merge(last, on=["state", "locality"])


def state_yearly(df: pd.DataFrame, value: str) -> pd.DataFrame:
    """Unweighted mean of `value` across a state's common localities, per year."""
    return df.groupby(["state", "year"], as_index=False)[value].mean()


def change_summary(yearly: pd.DataFrame, value: str, key: str = "state") -> pd.DataFrame:
    """First-to-last-year absolute and percent change per key, ranked by percent change."""
    wide = yearly.pivot(index=key, columns="year", values=value)
    first, last = wide.columns.min(), wide.columns.max()
    out = pd.DataFrame(
        {
            f"{value}_{first}": wide[first],
            f"{value}_{last}": wide[last],
            "abs_change": wide[last] - wide[first],
            "pct_change": (wide[last] / wide[first] - 1) * 100,
        }
    )
    return out.sort_values("pct_change", ascending=False).reset_index()


def build_datasets(raw_dir: Path) -> dict[str, pd.DataFrame]:
    """Download (if needed) and assemble all datasets used by the dashboard."""
    gpci_frames, payment_frames = [], []
    for year in YEARS:
        directory = download_year(year, raw_dir)
        gpci = compute_gaf(load_gpci(directory, year))
        rvu, _ = load_rvu(directory, year)
        gpci_frames.append(gpci)
        payment_frames.append(compute_payments(gpci, rvu))
    gaf = latest_names(common_localities(pd.concat(gpci_frames, ignore_index=True)))
    payments = latest_names(common_localities(pd.concat(payment_frames, ignore_index=True)))
    return {"gaf_locality": gaf, "payments_locality": payments}
