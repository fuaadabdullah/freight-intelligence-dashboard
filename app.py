"""Backward-compatible entry module forwarding to package implementation."""

from freight_intelligence_dashboard.app import build_figure, main

__all__ = ["build_figure", "main"]


if __name__ == "__main__":
    main()
