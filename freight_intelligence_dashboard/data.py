from json import loads
import ipaddress
import os
import random
from pathlib import Path
from urllib.parse import ParseResult, urlparse
from urllib.error import URLError
from urllib.parse import urlencode
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
ALLOWED_REMOTE_DATA_SCHEMES = {"https"}
BLOCKED_HOSTNAMES = {"localhost", "127.0.0.1", "::1"}


def _is_private_or_local_ip(hostname: str) -> bool:
    """Return True when hostname is a loopback/private/link-local IP literal."""

    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        return False

    return (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _validate_remote_data_url(data_url: str) -> ParseResult:
    """Validate a remote CSV URL and reject unsafe or malformed targets."""

    parsed = urlparse(data_url)

    if parsed.scheme.lower() not in ALLOWED_REMOTE_DATA_SCHEMES:
        raise ValueError("FREIGHT_DATA_URL must use https")

    if not parsed.netloc:
        raise ValueError("FREIGHT_DATA_URL must include a host")

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        raise ValueError("FREIGHT_DATA_URL host is missing")

    if hostname in BLOCKED_HOSTNAMES or hostname.endswith(".localhost"):
        raise ValueError("FREIGHT_DATA_URL cannot target localhost")

    if _is_private_or_local_ip(hostname):
        raise ValueError("FREIGHT_DATA_URL cannot target private or local IP addresses")

    return parsed


def validate_dataframe(df: pd.DataFrame) -> None:
    """Validate freight dataframe structure and core value constraints."""

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
    """Ensure score column has variation to avoid a single-size marker map."""

    if df["Score"].nunique() == 1:
        df = df.copy()
        df["Score"] = df["Score"] + pd.Series(range(len(df)), index=df.index)
    return df


def _load_csv_dataframe(csv_path: Path) -> pd.DataFrame:
    """Load, normalize, and validate freight data from a CSV file."""

    df = pd.read_csv(csv_path)
    df = df.rename(columns=lambda column: str(column).strip())
    validate_dataframe(df)
    return _ensure_score_variation(df)


def _download_csv_if_needed(csv_path: Path) -> Path | None:
    """Download freight CSV from configured URL when local file is missing."""

    data_url = os.getenv(FREIGHT_DATA_URL_ENV, "").strip()
    if not data_url:
        return None

    _validate_remote_data_url(data_url)

    try:
        urlretrieve(data_url, csv_path)
        print(f"Downloaded freight data from {data_url} to {csv_path}")
        return csv_path
    except (ValueError, URLError, OSError) as exc:
        raise RuntimeError(
            f"Unable to download freight data from {data_url}: {exc}"
        ) from exc


def _load_source_dataframe(seed: int = 42) -> pd.DataFrame:
    """Resolve source data from local CSV, remote CSV, or generated fallback."""

    if DEFAULT_CSV_PATH.exists():
        return _load_csv_dataframe(DEFAULT_CSV_PATH)

    downloaded_path = _download_csv_if_needed(DEFAULT_CSV_PATH)
    if downloaded_path is not None:
        return _load_csv_dataframe(downloaded_path)

    return build_base_dataframe(seed=seed)


def build_base_dataframe(seed: int = 42) -> pd.DataFrame:
    """Generate deterministic baseline freight data for demo mode."""

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
    """Add extra freight context columns using synthetic and optional live data."""

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
    """Fetch a JSON payload from a URL with a bounded request timeout."""

    with urlopen(url, timeout=10) as response:
        return loads(response.read().decode("utf-8"))


def _fetch_eia_fuel_price(api_key: str) -> float | None:
    """Fetch latest nationwide retail diesel price from EIA when available."""

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
    """Fetch weather condition and temperature for a coordinate from OpenWeatherMap."""

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
    """Approximate a logistics market index from weather severity and temperature."""

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
    """Map weather conditions to a coarse transport news sentiment signal."""

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
    """Expand base data into 24 hourly points with bounded score deltas."""

    rng = random.Random(seed + 99)
    hours = 24
    simulated_df = df.loc[df.index.repeat(hours)].reset_index(drop=True)
    simulated_df["Hour"] = list(range(hours)) * len(df)
    deltas = [rng.randint(-10, 10) for _ in range(len(simulated_df))]
    simulated_df["Score"] = (simulated_df["Score"].astype(int) + pd.Series(deltas)).clip(50, 100)
    validate_dataframe(simulated_df)
    return simulated_df


def prepare_dataframe(extras: bool = False, animate: bool = False, seed: int = 42) -> pd.DataFrame:
    """Prepare final dataframe according to extras and animation flags."""

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
