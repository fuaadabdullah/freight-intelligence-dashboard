import argparse
from pathlib import Path
from typing import Protocol

from data import prepare_dataframe
from visualization import create_map_figure


DEFAULT_SIZE_MAX = 40
DEFAULT_COLOR_SCALE = "OrRd"
DEFAULT_OUTPUT = "assets/freight_heatmap.html"
DEFAULT_SCREENSHOT = "assets/freight_heatmap.png"
DEFAULT_SEED = 42


class SupportsWriteImage(Protocol):
    def write_image(self, *args: object, **kwargs: object) -> object: ...


def build_figure(
    *,
    size_max: int,
    color_scale: str,
    output: str,
    screenshot: str,
    extras: bool,
    animate: bool,
    show: bool,
) -> None:
    df = prepare_dataframe(extras=extras, animate=animate, seed=DEFAULT_SEED)

    print(df.head())
    print("Data loaded successfully")

    fig = create_map_figure(
        df,
        size_max=size_max,
        color_scale=color_scale,
        animate=animate,
    )

    _ensure_parent_dir(output)
    fig.write_html(output)
    if screenshot:
        _ensure_parent_dir(screenshot)
        _write_png_safely(fig, screenshot)

    # Business-friendly summary line for demos/interviews
    print("Higher intensity = higher freight demand concentration.")
    print(
        "Insight: Atlanta appears as a hub while Savannah reflects port-driven activity, "
        "highlighting coastal vs inland distribution patterns."
    )

    if show:
        fig.show()


def _write_png_safely(fig: SupportsWriteImage, screenshot: str) -> None:
    try:
        # Requires Kaleido for static image export.
        fig.write_image(screenshot)
        print(f"Screenshot saved to {screenshot}")
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        print(
            "PNG export skipped. HTML export succeeded. "
            f"Reason: {exc}"
        )


def _ensure_parent_dir(file_path: str) -> None:
    path = Path(file_path)
    if path.parent and path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Georgia freight heat map demo")
    parser.add_argument("--extras", action="store_true", help="Add FuelPrice, LMI, NewsSentiment")
    parser.add_argument("--animate", action="store_true", help="Animate 24-hour trends")
    parser.add_argument("--size-max", type=int, default=DEFAULT_SIZE_MAX, help="Max marker size")
    parser.add_argument("--color-scale", type=str, default=DEFAULT_COLOR_SCALE, help="Sequential color scale")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT, help="HTML output path")
    parser.add_argument("--screenshot", type=str, default=DEFAULT_SCREENSHOT, help="PNG output path")
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Skip opening interactive viewer (useful for automated checks)",
    )
    args = parser.parse_args()

    # Generate simulated freight demand data (replace with real API data in production).
    build_figure(
        size_max=args.size_max,
        color_scale=args.color_scale,
        output=args.output,
        screenshot=args.screenshot,
        extras=args.extras,
        animate=args.animate,
        show=not args.no_show,
    )


if __name__ == "__main__":
    main()
