# pyright: reportMissingTypeStubs=false

import os
import random
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.error import URLError
from urllib.request import urlopen, urlretrieve

import pandas as pd


CITIES = ["Atlanta", "Savannah", "Augusta", "Macon", "Columbus"]
LAT = [33.7490, 32.0809, 33.4735, 32.8407, 32.460976]
LON = [-84.3880, -81.0912, -82.0105, -83.6324, -84.9877]
REQUIRED_COLUMNS = {"City", "Lat", "Lon", "Score"}
EXTRA_COLUMNS = ("FuelPrice", "LMI", "NewsSentiment")
DEFAULT_CSV_PATH = Path("freight_data.csv")
FREIGHT_DATA_URL_ENV = "FREIGHT_DATA_URL"
EIA_API_KEY_ENV = "EIA_API_KEY"
OPENWEATHERMAP_API_KEY_ENV = "OPENWEATHERMAP_API_KEY"


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

    if not df["Lat"].between(-90, 90).all():
        raise ValueError("Invalid latitude values detected; expected range [-90, 90]")

    if not df["Lon"].between(-180, 180).all():
        raise ValueError("Invalid longitude values detected; expected range [-180, 180]")


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

    eia_api_key = os.getenv(EIA_API_KEY_ENV, "").strip()
    if eia_api_key:
        fuel_price = _fetch_eia_fuel_price(eia_api_key)
        if fuel_price is not None:
            enriched["FuelPrice"] = [fuel_price] * len(df)

    openweathermap_api_key = os.getenv(OPENWEATHERMAP_API_KEY_ENV, "").strip()
    if openweathermap_api_key:
        live_lmi: list[int] = []
        live_sentiment: list[str] = []
        latitudes = enriched["Lat"].astype("float64").tolist()
        longitudes = enriched["Lon"].astype("float64").tolist()
        for lat, lon in zip(latitudes, longitudes):
            snapshot = _fetch_openweathermap_snapshot(
                lat=lat,
                lon=lon,
                api_key=openweathermap_api_key,
            )
            if snapshot is None:
                continue
            live_lmi.append(_lmi_from_weather(snapshot["condition"], snapshot["temp_f"]))
            live_sentiment.append(
                _sentiment_from_weather(snapshot["condition"], snapshot["temp_f"])
            )

        if len(live_lmi) == len(enriched):
            enriched["LMI"] = live_lmi
        if len(live_sentiment) == len(enriched):
            enriched["NewsSentiment"] = live_sentiment

    validate_dataframe(enriched)
    return enriched


def _fetch_json(url: str) -> dict:
    with urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _fetch_eia_fuel_price(api_key: str) -> float | None:
    query = urlencode(
        {
            "api_key": api_key,
            "series_id": "PET.EMM_EPM0_PTE_NUS_DPG.W",
        }
    )
    url = f"https://api.eia.gov/series/?{query}"
    try:
        payload = _fetch_json(url)
        latest_value = float(payload["series"][0]["data"][0][1])
        return round(latest_value, 2)
    except (KeyError, IndexError, TypeError, ValueError, URLError, OSError):
        return None


def _fetch_openweathermap_snapshot(lat: float, lon: float, api_key: str) -> dict | None:
    query = urlencode(
        {
            "lat": lat,
            "lon": lon,
            "appid": api_key,
            "units": "imperial",
        }
    )
    url = f"https://api.openweathermap.org/data/2.5/weather?{query}"
    try:
        payload = _fetch_json(url)
        condition = str(payload["weather"][0]["main"])
        temp_f = float(payload["main"]["temp"])
        return {"condition": condition, "temp_f": temp_f}
    except (KeyError, IndexError, TypeError, ValueError, URLError, OSError):
        return None


def _lmi_from_weather(condition: str, temp_f: float) -> int:
    base = 67
    if condition in {"Thunderstorm", "Snow", "Tornado", "Squall", "Ash"}:
        base -= 14
    elif condition in {"Rain", "Drizzle", "Mist", "Fog", "Haze"}:
        base -= 7
    elif condition in {"Clear", "Clouds"}:
        base += 4

    if temp_f < 32 or temp_f > 100:
        base -= 10
    elif temp_f < 45 or temp_f > 90:
        base -= 5
    elif 55 <= temp_f <= 80:
        base += 3

    return max(45, min(80, base))


def _sentiment_from_weather(condition: str, temp_f: float) -> str:
    if condition in {"Thunderstorm", "Snow", "Tornado", "Squall", "Ash"}:
        return "Negative"
    if condition in {"Rain", "Drizzle", "Mist", "Fog", "Haze"}:
        return "Neutral"
    if temp_f < 28 or temp_f > 103:
        return "Negative"
    if temp_f < 45 or temp_f > 92:
        return "Neutral"
    return "Positive"


def build_hourly_simulation(df: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed + 99)
    hours = 24
    simulated_df = df.loc[df.index.repeat(hours)].reset_index(drop=True)
    simulated_df["Hour"] = list(range(hours)) * len(df)
    deltas = [rng.randint(-10, 10) for _ in range(len(simulated_df))]
    simulated_df["Score"] = (simulated_df["Score"].astype(int) + pd.Series(deltas)).clip(50, 100)
    validate_dataframe(simulated_df)
    return simulated_df


def prepare_dataframe(extras: bool = False, animate: bool = False, seed: int = 42) -> pd.DataFrame:
    df = _load_source_dataframe(seed=seed)
    if extras:
        missing_extra_columns = [col for col in EXTRA_COLUMNS if col not in df.columns]
        if missing_extra_columns:
            generated_extras = add_extras(df, seed=seed)
            for col in missing_extra_columns:
                df[col] = generated_extras[col]
    else:
        df = df.drop(columns=[col for col in EXTRA_COLUMNS if col in df.columns])
    if animate:
        df = build_hourly_simulation(df, seed=seed)

    validate_dataframe(df)
    return df
