# pyright: reportMissingTypeStubs=false

import warnings
from typing import Any

import pandas as pd

try:
    import plotly.express as px  # type: ignore[import-untyped]
except ModuleNotFoundError as exc:
    raise RuntimeError(
        "Plotly is not installed in the active Python environment. "
        "Run: pip install -r requirements.txt"
    ) from exc


def create_map_figure(
    df: pd.DataFrame,
    *,
    size_max: int,
    color_scale: str,
    animate: bool,
) -> Any:
    selected_scale = getattr(px.colors.sequential, color_scale, px.colors.sequential.OrRd)

    custom_columns = ["City", "Score"]
    for col in ["FuelPrice", "LMI", "NewsSentiment"]:
        if col in df.columns:
            custom_columns.append(col)

    # Plotly may emit a deprecation warning for scatter_mapbox in newer versions.
    # Keep behavior stable for the demo; migrate to scatter_map after the interview.
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            category=DeprecationWarning,
            message=r".*scatter_mapbox.*",
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
            animation_frame="Hour" if animate and "Hour" in df.columns else None,
            custom_data=custom_columns,
        )

    hover_parts = [
        "<b>%{customdata[0]}</b>",
        "Freight Score: %{customdata[1]}",
    ]
    if "FuelPrice" in df.columns:
        hover_parts.append("Fuel Price: $%{customdata[2]}")
    if "LMI" in df.columns:
        hover_parts.append("LMI: %{customdata[3]}")
    if "NewsSentiment" in df.columns:
        hover_parts.append("Sentiment: %{customdata[4]}")

    fig.update_traces(hovertemplate="<br>".join(hover_parts) + "<extra></extra>")
    fig.update_layout(
        title="Georgia Freight Heat Map (Last 24 Hours)",
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
    )
    return fig
