# Plantorix

**AI-Powered Podiatric Pressure Mapping and Diabetic Orthotic Printing Engine**

A research and educational prototype that loads plantar-pressure recordings from sensorized insoles, shows them as interactive sensor maps and charts, summarises the pressure distribution with transparent statistics, and outlines how orthotic offloading could later be designed.

> **This is not a clinically validated medical device.** It makes no diagnosis, no ulcer-risk prediction and no treatment recommendation.

## What works today

- Discovers all 310 pressure recordings (15 participants, left and right insole) in the dataset folder.
- Dashboard with: live API status, summary cards, a 32-sensor intensity grid with frame slider and playback, per-frame statistics, four charts, a data-quality panel and an orthotic-design workflow page.
- Calculations are plain descriptive statistics on the real sensor values: mean, maximum, minimum, total, sensors above the frame average, and a check of the sensor sum against the recorded `sumP` column.
- Raw data is only read, never modified.

## What it does not do (yet)

- **No machine learning.** Nothing is trained or predicted.
- **No anatomical foot map.** The mapping from CSV columns (`PressureSensor 0-31`) to positions on the foot is not verified, so the grid is labelled *unregistered sensor layout* and is ordered by CSV index.
- **No pressure units.** Values are raw sensor counts (documented range 0 to 4096), shown as "Recorded sensor value", not kPa.
- **No clinical claims.** The dataset is healthy-volunteer gait data, not a diabetic or ulcer cohort, so it has no diabetic labels or ulcer outcomes. "Above average" means above the mean of the 32 sensors in the same frame, not a clinical hotspot.
- **No orthotic geometry.** The orthotic page shows the conceptual workflow and exports a JSON summary whose offloading depth and material are `null`.

## Run it (Windows PowerShell)

```powershell
cd Plantorix
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Then open **http://127.0.0.1:8000/** (the dashboard) or http://127.0.0.1:8000/docs (interactive API docs).
Open the dashboard through that address, not by double-clicking `index.html`: a page opened from a file cannot read the API.

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process Bypass` first.

Check the setup: `python -m backend.config` should report 310 pressure files. Run the tests with `pip install pytest httpx` then `python -m pytest -q`.

The dashboard loads Chart.js from the internet (cdnjs), so the first load needs a connection.

## Dataset

Multimodal gait dataset with synchronized sensorized-insole pressure and OptiTrack motion capture: [Zenodo record 20156243](https://zenodo.org/records/20156243), licence CC BY 4.0. Download and extract it to `data/raw/InsolesOpitrackDataset/` (or set the `PLANTORIX_DATASET_DIR` environment variable). Layout: `P<n>/<take>/<take>_Preassure_<L|R>.csv` (the dataset's own spelling). The dataset's `info.txt` flags P13 M1 (insole desynchronisation) and P3 M8 (motion-capture errors); the dashboard shows these as warnings.

## Folder structure

```text
Plantorix/
├── backend/
│   ├── main.py              API routes, serves the dashboard
│   ├── config.py            paths, sensor constants, CORS
│   ├── services/
│   │   ├── dataset_service.py   finds recordings, safe cached loading
│   │   └── analysis.py          frame statistics, time series, sumP check
│   └── schemas/models.py    response models
├── frontend/
│   ├── index.html
│   ├── css/styles.css
│   └── js/ api.js, heatmap.js, charts.js, app.js
├── data/raw/                dataset (not modified by the code)
├── research/inspect_pressure.py   exploration script
├── tests/test_api.py
└── requirements.txt
```

## API

| Endpoint | Returns |
|---|---|
| `GET /api/health` | actual API and dataset status |
| `GET /api/datasets` | all recordings (`?participant=P15&side=L` to filter) |
| `GET /api/datasets/{id}/summary` | dimensions, columns, missing values, value range |
| `GET /api/datasets/{id}/frame/{n}` | the 32 values and statistics for frame `n` |
| `GET /api/datasets/{id}/timeseries` | per-frame sums, `sumP`, max, mean (`?sensor=0-31` for one sensor) |
| `GET /api/datasets/{id}/validation` | calculated sum vs `sumP`, data-quality warnings |

Recording ids look like `P15_M3.I_L` (participant, take, side). Only ids found by scanning the dataset folder are accepted, so a request can never name a file path. Errors use normal HTTP codes (404 unknown recording or frame, 422 invalid input).

## Possible next steps

1. Verify the sensor-to-foot mapping from the dataset authors' documentation, then draw sensors on a real foot outline.
2. For any model, first obtain a **labelled** dataset (for example plantar pressure with documented ulcer outcomes, or clinician-labelled high-risk regions), split train and test by participant, and report meaningful metrics with their limits.
3. Only then derive orthotic offloading parameters, validated with clinical input.

## Team

Kritika Saxena, Mradul Khandelwal