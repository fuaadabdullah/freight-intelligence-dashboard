# Georgia Freight Heat Map — Talking Points

## Problem

Shippers and dispatch teams need fast visibility into where freight demand is rising so they can route trucks and capacity efficiently.

## Solution

An interactive Georgia heat map using Plotly that visualizes freight demand hotspots across Atlanta, Savannah, Augusta, Macon, and Columbus.

## Value

- Spot demand spikes quickly
- Reduce empty miles and routing delays
- Improve resource allocation and decision speed

## Tech Stack

Python, Pandas, Plotly Express (`scatter_mapbox`), HTML export for easy sharing.

## 2–3 Minute Pitch

This demo shows how freight demand can be monitored geographically in near real time. Each city marker grows and changes color as demand score increases, making hotspots obvious at a glance. With optional overlays like fuel price, LMI, and sentiment, operators can combine demand and market context in one view. The approach is lightweight today and can scale to live APIs tomorrow for production dispatch intelligence.
