import unittest
import warnings
import random
import tempfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from freight_intelligence_dashboard.data import (
    build_base_dataframe,
    build_hourly_simulation,
    prepare_dataframe,
    _validate_remote_data_url,
    validate_dataframe,
)
from freight_intelligence_dashboard.app import _inject_html_title, _validate_cli_options
from freight_intelligence_dashboard.visualization import create_map_figure


class DataBehaviorTests(unittest.TestCase):
    def test_build_hourly_simulation_shape_and_bounds(self) -> None:
        base_df = build_base_dataframe(seed=42)
        simulated_df = build_hourly_simulation(base_df, seed=42)

        self.assertEqual(len(simulated_df), len(base_df) * 24)
        self.assertEqual(int(simulated_df["Hour"].min()), 0)
        self.assertEqual(int(simulated_df["Hour"].max()), 23)
        self.assertTrue((simulated_df["Score"] >= 50).all())
        self.assertTrue((simulated_df["Score"] <= 100).all())

        hours_per_city = simulated_df.groupby("City")["Hour"].nunique()
        self.assertTrue((hours_per_city == 24).all())

    def test_build_hourly_simulation_applies_only_seeded_deltas(self) -> None:
        base_df = pd.DataFrame(
            {
                "City": ["A", "B"],
                "Lat": [33.0, 34.0],
                "Lon": [-84.0, -85.0],
                "Score": [70, 70],
            }
        )

        simulated_df = build_hourly_simulation(base_df, seed=42)

        rng = random.Random(42 + 99)
        expected_deltas = [rng.randint(-10, 10) for _ in range(len(simulated_df))]
        repeated_base_scores = pd.Series([70] * len(simulated_df))
        expected_scores = (repeated_base_scores + pd.Series(expected_deltas)).clip(50, 100)

        self.assertTrue(simulated_df["Score"].reset_index(drop=True).equals(expected_scores))

    def test_prepare_dataframe_strips_extras_when_flag_disabled(self) -> None:
        source_df = build_base_dataframe(seed=7)
        source_df["FuelPrice"] = [3.25] * len(source_df)
        source_df["LMI"] = [60] * len(source_df)
        source_df["NewsSentiment"] = ["Neutral"] * len(source_df)

        with patch("freight_intelligence_dashboard.data._load_source_dataframe", return_value=source_df):
            result_df = prepare_dataframe(extras=False, animate=False, seed=123)

        self.assertNotIn("FuelPrice", result_df.columns)
        self.assertNotIn("LMI", result_df.columns)
        self.assertNotIn("NewsSentiment", result_df.columns)

    def test_prepare_dataframe_adds_extras_when_missing_and_enabled(self) -> None:
        source_df = build_base_dataframe(seed=9)

        with patch("freight_intelligence_dashboard.data._load_source_dataframe", return_value=source_df):
            result_df = prepare_dataframe(extras=True, animate=False, seed=123)

        self.assertIn("FuelPrice", result_df.columns)
        self.assertIn("LMI", result_df.columns)
        self.assertIn("NewsSentiment", result_df.columns)

    def test_prepare_dataframe_preserves_existing_extras_when_partial(self) -> None:
        source_df = build_base_dataframe(seed=9)
        source_df["FuelPrice"] = [3.10] * len(source_df)
        source_df["LMI"] = [62] * len(source_df)

        with patch("freight_intelligence_dashboard.data._load_source_dataframe", return_value=source_df):
            result_df = prepare_dataframe(extras=True, animate=False, seed=123)

        self.assertTrue((result_df["FuelPrice"] == 3.10).all())
        self.assertTrue((result_df["LMI"] == 62).all())
        self.assertIn("NewsSentiment", result_df.columns)

    def test_create_map_figure_warns_on_invalid_color_scale(self) -> None:
        df = build_base_dataframe(seed=42)

        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            fig = create_map_figure(
                df,
                size_max=25,
                color_scale="DefinitelyNotARealScale",
                animate=False,
            )

        self.assertIsNotNone(fig)
        warning_messages = [str(item.message) for item in captured]
        self.assertTrue(any("Unknown color scale" in message for message in warning_messages))

    def test_create_map_figure_title_reflects_animation_mode(self) -> None:
        base_df = build_base_dataframe(seed=42)
        snapshot_fig = create_map_figure(
            base_df,
            size_max=25,
            color_scale="OrRd",
            animate=False,
        )
        self.assertEqual(snapshot_fig.layout.title.text, "Georgia Freight Heat Map")

        hourly_df = build_hourly_simulation(base_df, seed=42)
        animated_fig = create_map_figure(
            hourly_df,
            size_max=25,
            color_scale="OrRd",
            animate=True,
        )
        self.assertEqual(
            animated_fig.layout.title.text,
            "Georgia Freight Heat Map (Last 24 Hours)",
        )

    def test_validate_dataframe_rejects_invalid_coordinates(self) -> None:
        bad_lat_df = pd.DataFrame(
            {"City": ["Bad"], "Lat": [999], "Lon": [0], "Score": [80]}
        )
        with self.assertRaisesRegex(ValueError, "latitude"):
            validate_dataframe(bad_lat_df)

        bad_lon_df = pd.DataFrame(
            {"City": ["Bad"], "Lat": [0], "Lon": [999], "Score": [80]}
        )
        with self.assertRaisesRegex(ValueError, "longitude"):
            validate_dataframe(bad_lon_df)

    def test_validate_cli_options_rejects_invalid_paths_and_size(self) -> None:
        with self.assertRaisesRegex(ValueError, "size-max"):
            _validate_cli_options(size_max=0, output="assets/out.html", screenshot="")

        with self.assertRaisesRegex(ValueError, "Output"):
            _validate_cli_options(size_max=10, output="assets/out.png", screenshot="")

        with self.assertRaisesRegex(ValueError, "Screenshot"):
            _validate_cli_options(size_max=10, output="assets/out.html", screenshot="assets/out.html")

    def test_inject_html_title_escapes_html_markup(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = Path(tmpdir) / "example.html"
            html_path.write_text("<html><head></head><body></body></html>", encoding="utf-8")

            _inject_html_title(str(html_path), "Dashboard <script>alert(1)</script>")

            content = html_path.read_text(encoding="utf-8")
            self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", content)
            self.assertNotIn("<script>alert(1)</script>", content)

    def test_validate_remote_data_url_rejects_private_targets(self) -> None:
        for unsafe_url in [
            "http://example.com/data.csv",
            "https://localhost/data.csv",
            "https://127.0.0.1/data.csv",
            "https://10.0.0.5/data.csv",
            "https://[::1]/data.csv",
        ]:
            with self.assertRaises(ValueError):
                _validate_remote_data_url(unsafe_url)

        self.assertEqual(
            _validate_remote_data_url("https://example.com/data.csv").hostname,
            "example.com",
        )


if __name__ == "__main__":
    unittest.main()
