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
    """Create the Plotly freight heat map figure with optional animation and extras."""

    if hasattr(px.colors.sequential, color_scale):
        selected_scale = getattr(px.colors.sequential, color_scale)
    else:
        warnings.warn(
            (
                f"Unknown color scale '{color_scale}'. "
                "Falling back to 'OrRd'."
            ),
            category=UserWarning,
            stacklevel=2,
        )
        selected_scale = px.colors.sequential.OrRd

    is_animated = animate and "Hour" in df.columns

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
            animation_frame="Hour" if is_animated else None,
            custom_data=custom_columns,
        )

    hover_parts = [
        "<b>%{customdata[0]}</b>",
        "Freight Score: %{customdata[1]}",
    ]
    custom_index = {col: idx for idx, col in enumerate(custom_columns)}
    if "FuelPrice" in df.columns:
        hover_parts.append(f"Fuel Price: $%{{customdata[{custom_index['FuelPrice']}]}}")
    if "LMI" in df.columns:
        hover_parts.append(f"LMI: %{{customdata[{custom_index['LMI']}]}}")
    if "NewsSentiment" in df.columns:
        hover_parts.append(
            f"Sentiment: %{{customdata[{custom_index['NewsSentiment']}]}}"
        )

    fig.update_traces(hovertemplate="<br>".join(hover_parts) + "<extra></extra>")
    title = (
        "Georgia Freight Heat Map (Last 24 Hours)"
        if is_animated
        else "Georgia Freight Heat Map"
    )
    fig.update_layout(
        title=title,
        margin={"r": 0, "t": 40, "l": 0, "b": 30},
    )
    
    # Add attribution footer
    fig.add_annotation(
        text="Built by Fuaad Abdullah, 2026",
        xref="paper",
        yref="paper",
        x=0.5,
        y=-0.02,
        showarrow=False,
        font=dict(size=10, color="#999"),
        xanchor="center",
        yanchor="top",
    )
    
    return fig
