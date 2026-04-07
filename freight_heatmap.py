import argparse
import random

import pandas as pd
import plotly.express as px


DEFAULT_SIZE_MAX = 40
DEFAULT_COLOR_SCALE = "OrRd"
DEFAULT_OUTPUT = "heatmap.html"


def build_dataframe() -> pd.DataFrame:
    cities = ["Atlanta", "Savannah", "Augusta", "Macon", "Columbus"]
    lat = [33.7490, 32.0809, 33.4735, 32.8407, 32.460976]
    lon = [-84.3880, -81.0912, -82.0105, -83.6324, -84.9877]
    freight_score = [random.randint(50, 100) for _ in cities]

    df = pd.DataFrame(
        list(zip(cities, lat, lon, freight_score)),
        columns=["City", "Lat", "Lon", "Score"],
    )
    return df


def add_extras(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["FuelPrice"] = [round(random.uniform(2.90, 4.60), 2) for _ in range(len(df))]
    df["LMI"] = [random.randint(45, 80) for _ in range(len(df))]
    df["NewsSentiment"] = [
        random.choice(["Positive", "Neutral", "Negative"]) for _ in range(len(df))
    ]
    return df


def build_hourly_simulation(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in df.iterrows():
        for hour in range(24):
            simulated_row = row.copy()
            simulated_row["Hour"] = hour
            simulated_row["Score"] = max(
                50,
                min(100, int(row["Score"]) + random.randint(-10, 10)),
            )
            rows.append(simulated_row)
    return pd.DataFrame(rows)


def plot_heat_map(
    df: pd.DataFrame,
    size_max: int,
    color_scale: str,
    output: str,
    animate: bool,
    screenshot: str,
) -> None:
    hover_data: dict[str, bool] = {
        "City": True,
        "Score": True,
        "Lat": False,
        "Lon": False,
    }
    for extra_col in ["FuelPrice", "LMI", "NewsSentiment"]:
        if extra_col in df.columns:
            hover_data[extra_col] = True

    selected_scale = getattr(
        px.colors.sequential, color_scale, px.colors.sequential.OrRd
    )

    fig = px.scatter_mapbox(
        df,
        lat="Lat",
        lon="Lon",
        size="Score",
        color="Score",
        color_continuous_scale=selected_scale,
        size_max=size_max,
        zoom=6,
        mapbox_style="carto-positron",
        hover_name="City",
        hover_data=hover_data,
        animation_frame="Hour" if animate and "Hour" in df.columns else None,
    )

    fig.write_html(output)
    print(f"Saved interactive map to {output}")

    if screenshot:
        fig.write_image(screenshot)
        print(f"Saved screenshot to {screenshot}")

    fig.show()


def main() -> None:
    parser = argparse.ArgumentParser(description="Georgia freight heat map demo")
    parser.add_argument(
        "--extras",
        action="store_true",
        help="Add FuelPrice, LMI, and NewsSentiment columns",
    )
    parser.add_argument(
        "--animate",
        action="store_true",
        help="Create 24-hour simulation animation",
    )
    parser.add_argument(
        "--size-max",
        type=int,
        default=DEFAULT_SIZE_MAX,
        help="Maximum marker size",
    )
    parser.add_argument(
        "--color-scale",
        type=str,
        default=DEFAULT_COLOR_SCALE,
        help="Plotly sequential color scale name",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=DEFAULT_OUTPUT,
        help="Output HTML file path",
    )
    parser.add_argument(
        "--screenshot",
        type=str,
        default="",
        help="Optional PNG screenshot output path (requires kaleido)",
    )
    args = parser.parse_args()

    dataframe = build_dataframe()
    if args.extras:
        dataframe = add_extras(dataframe)
    if args.animate:
        dataframe = build_hourly_simulation(dataframe)

    print(dataframe.head())
    plot_heat_map(
        dataframe,
        size_max=args.size_max,
        color_scale=args.color_scale,
        output=args.output,
        animate=args.animate,
        screenshot=args.screenshot,
    )


if __name__ == "__main__":
    main()
