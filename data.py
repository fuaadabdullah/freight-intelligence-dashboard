# pyright: reportMissingTypeStubs=false

import os
import random
from pathlib import Path
from typing import Any, cast
from urllib.error import URLError
from urllib.request import urlretrieve

import pandas as pd


CITIES = ["Atlanta", "Savannah", "Augusta", "Macon", "Columbus"]
LAT = [33.7490, 32.0809, 33.4735, 32.8407, 32.460976]
LON = [-84.3880, -81.0912, -82.0105, -83.6324, -84.9877]
REQUIRED_COLUMNS = {"City", "Lat", "Lon", "Score"}
DEFAULT_CSV_PATH = Path("freight_data.csv")
FREIGHT_DATA_URL_ENV = "FREIGHT_DATA_URL"


def validate_dataframe(df: pd.DataFrame) -> None:
    if len(df) == 0:
        raise ValueError("Dataframe is empty")

    if df.isnull().values.any():
        raise ValueError("Data contains null values")

    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    if (df["Score"] < 0).any():
        raise ValueError("Data contains negative score values")


def _ensure_score_variation(df: pd.DataFrame) -> pd.DataFrame:
    if df["Score"].nunique() == 1:
        df = df.copy()
        df["Score"] = df["Score"] + pd.Series(range(len(df)), index=df.index)
    return df


def _load_csv_dataframe(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df = df.rename(columns=lambda column: str(column).strip())
    validate_dataframe(df)
    return _ensure_score_variation(df)


def _download_csv_if_needed(csv_path: Path) -> Path | None:
    data_url = os.getenv(FREIGHT_DATA_URL_ENV, "").strip()
    if not data_url:
        return None

    try:
        urlretrieve(data_url, csv_path)
        print(f"Downloaded freight data from {data_url} to {csv_path}")
        return csv_path
    except (URLError, OSError) as exc:
        raise RuntimeError(
            f"Unable to download freight data from {data_url}: {exc}"
        ) from exc


def _load_source_dataframe(seed: int = 42) -> pd.DataFrame:
    if DEFAULT_CSV_PATH.exists():
        return _load_csv_dataframe(DEFAULT_CSV_PATH)

    downloaded_path = _download_csv_if_needed(DEFAULT_CSV_PATH)
    if downloaded_path is not None:
        return _load_csv_dataframe(downloaded_path)

    return build_base_dataframe(seed=seed)


def build_base_dataframe(seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed)
    scores = [rng.randint(50, 100) for _ in CITIES]

    df = pd.DataFrame(
        list(zip(CITIES, LAT, LON, scores)),
        columns=["City", "Lat", "Lon", "Score"],
    )
    df = _ensure_score_variation(df)
    validate_dataframe(df)
    return df


def add_extras(df: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed + 7)
    enriched = df.copy()
    enriched["FuelPrice"] = [round(rng.uniform(2.90, 4.60), 2) for _ in range(len(df))]
    enriched["LMI"] = [rng.randint(45, 80) for _ in range(len(df))]
    enriched["NewsSentiment"] = [
        rng.choice(["Positive", "Neutral", "Negative"]) for _ in range(len(df))
    ]
    validate_dataframe(enriched)
    return enriched


def build_hourly_simulation(df: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed + 99)
    rows: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        base_score = int(row["Score"])
        for hour in range(24):
            simulated = cast(dict[str, Any], row.to_dict())
            simulated["Hour"] = hour
            simulated["Score"] = max(50, min(100, base_score + rng.randint(-10, 10)))
            rows.append(simulated)

    simulated_df = pd.DataFrame(rows)
    simulated_df = _ensure_score_variation(simulated_df)
    validate_dataframe(simulated_df)
    return simulated_df


def prepare_dataframe(extras: bool = False, animate: bool = False, seed: int = 42) -> pd.DataFrame:
    df = _load_source_dataframe(seed=seed)
    if extras:
        has_all_extra_columns = all(
            col in df.columns for col in ["FuelPrice", "LMI", "NewsSentiment"]
        )
        if not has_all_extra_columns:
            df = add_extras(df, seed=seed)
    if animate:
        df = build_hourly_simulation(df, seed=seed)

    validate_dataframe(df)
    return df
