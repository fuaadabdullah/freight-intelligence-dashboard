# freight-intelligence-dashboard

Freight Intelligence Dashboard for visualizing freight-demand hotspots across Georgia using Python, Pandas, and Plotly.

## Creator

**Fuaad Abdullah**  
Email: [fuaadabdullah@gmail.com](mailto:fuaadabdullah@gmail.com)  
GitHub: [fuaadabdullah](https://github.com/fuaadabdullah)

## Ownership

© 2026 Fuaad Abdullah. All rights reserved.

This project and all source files in this repository are created and owned by Fuaad Abdullah unless explicitly stated otherwise.

## Project Outputs

- Interactive HTML map export in `assets/freight_heatmap.html`
- Screenshot export in `assets/freight_heatmap.png` (best effort; requires Kaleido)
- If PNG export fails (for example, Kaleido is missing), HTML export remains the guaranteed fallback
- Automated GitHub Pages output in `index.html` during CI deployment to `gh-pages`

## Run

Use your virtual environment Python executable:

- Base map: `python freight_heatmap.py --output assets/freight_heatmap.html`
- With extras: `python freight_heatmap.py --extras --output assets/freight_heatmap.html`
- Animated: `python freight_heatmap.py --extras --animate --output assets/freight_heatmap.html --screenshot assets/freight_heatmap.png`

## Optional API Keys

If you plan to integrate live external sources, add keys in a local `.env` file.

- Template: `.env.example`
- Local secrets file (git-ignored): `.env`

Current optional keys:

- `EIA_API_KEY`
- `OPENWEATHERMAP_API_KEY`

### GitHub Actions secrets for live deploys

To use live extras in scheduled deployments, add these repository secrets:

- `EIA_API_KEY`
- `OPENWEATHERMAP_API_KEY`

The workflow uses these secrets when generating the dashboard with `--extras`.

## Automated Daily Publish (GitHub Actions + GitHub Pages)

This repository includes a scheduled workflow that regenerates the dashboard and deploys it to the `gh-pages` branch.

- Workflow file: `.github/workflows/update_dashboard.yml`
- Schedule: daily at `06:00 UTC`
- Output artifact generated in CI: `index.html`
- Deployment target: `gh-pages` branch via direct `git` push in workflow script

### How it works

1. The workflow checks out code and installs dependencies from `requirements.txt`.
2. It runs:
   - `python freight_heatmap.py --no-show --no-screenshot --output freight_heatmap.html`
   - Then wraps it in a simple `index.html` that embeds `freight_heatmap.html`.
3. It deploys the generated site contents to the `gh-pages` branch.

### Enable GitHub Pages

In your repository settings:

1. Open **Settings → Pages**.
2. Under **Build and deployment**, choose **Deploy from a branch**.
3. Select branch **`gh-pages`** and folder **`/(root)`**.

After the first successful workflow run, your dashboard is served from your GitHub Pages URL.

### Manual run and troubleshooting

- You can run the workflow anytime from the **Actions** tab using **Run workflow**.
- If a run fails, check workflow logs for dependency install, data acquisition, or rendering errors.

## Data Source Strategy

The dashboard uses this order when loading data:

1. `freight_data.csv` in repository root (preferred when you commit data)
2. URL from environment variable `FREIGHT_DATA_URL` (optional runtime download)
3. Built-in simulated demo data fallback

### Option A: Commit CSV to the repository

Place `freight_data.csv` in the repo root with required columns:

- `City`
- `Lat`
- `Lon`
- `Score`

### Option B: Pull CSV dynamically (more professional)

Set `FREIGHT_DATA_URL` in your runtime environment (for example as a GitHub Actions secret), and the app will download data automatically when a local CSV is missing.
