# Plantorix

**AI-Powered Podiatric Pressure Mapping and Diabetic Orthotic Printing Engine**

A research and educational prototype that loads plantar-pressure recordings from sensorized insoles, shows them as interactive sensor maps and charts, summarises the pressure distribution with transparent statistics, and outlines how orthotic offloading could later be designed.

> **This is not a clinically validated medical device.** It makes no diagnosis, no ulcer-risk prediction and no treatment recommendation.

## What works today

- Discovers all 310 pressure recordings (15 participants, left and right insole) in the dataset folder.
- Dashboard with: live API status, summary cards, a 32-sensor intensity grid with frame slider and playback, per-frame statistics, four charts, a data-quality panel and an orthotic-design workflow page.
- **Orthotic design demo (Phase 6):** each sensor's peak load over the whole recording (95th percentile) picks the top N% of sensors; they get circular relief pockets on a simplified insole outline, scaled from the participant's shoe size. Neighbouring pockets are grouped into zones. Download as STL or JSON.
- Two sensor views: a plain **sensor matrix** (ordered by CSV index) and an **insole diagram** view that places the sensors as on the dataset's numbering diagram. The diagram view is supported by data tests but not confirmed by the dataset authors (see below).
- Calculations are plain descriptive statistics on the real sensor values: mean, maximum, minimum, total, sensors above the frame average, and a check of the sensor sum against the recorded `sumP` column.
- Raw data is only read, never modified.
- **Branding and report (Phase 7):** Plantorix logo, app icon and icon set (`frontend/assets/`), and a printable one-page **Recording report** (summary, data quality, layout status, optional orthotic design) that can be saved as PDF from the browser. Chart.js is bundled in `frontend/vendor/` so the demo works offline.

## What it does not do (yet)

- **No machine learning.** Nothing is trained or predicted.
- **No confirmed anatomical foot map.** The dataset does not document which CSV column is which physical sensor. The matrix view is labelled *unregistered sensor layout*. The diagram view uses an arrangement that the recordings support but that the authors have not confirmed, and no foot outline is drawn.
- **`copX` / `copY` are not anatomical.** They fit exactly (R² = 1.0) to a plain 8x4 matrix position of each sensor index, so they are not a real centre of pressure on the foot and the app does not use them.
- **No pressure units.** Values are raw sensor counts (documented range 0 to 4096), shown as "Recorded sensor value", not kPa.
- **No clinical claims.** The dataset is healthy-volunteer gait data, not a diabetic or ulcer cohort, so it has no diabetic labels or ulcer outcomes. "Above average" means above the mean of the 32 sensors in the same frame, not a clinical hotspot.
- **No clinical orthotic design.** The orthotic page generates an *illustrative demonstration*: pockets under the highest-peak sensors on a simplified insole, exported as STL. Pocket depth and base thickness are values the user picks; they have no clinical basis. The design is not validated for any individual and not print-ready.

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
│   │   ├── analysis.py          frame statistics, time series, sumP check
│   │   ├── layout_service.py    sensor positions from sensor_layout.json
│   │   └── orthotic_service.py  demo relief design and STL export
│   ├── sensor_layout.json   generated by research/verify_sensor_layout.py
│   └── schemas/models.py    response models
├── frontend/
│   ├── index.html
│   ├── css/styles.css
│   └── js/ api.js, heatmap.js, charts.js, app.js
├── data/raw/                dataset (not modified by the code)
├── research/
│   ├── inspect_pressure.py       exploration script
│   └── verify_sensor_layout.py   tests the CSV-column to diagram-label mapping
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
| `GET /api/datasets/{id}/orthotic` | demo design numbers and geometry (`?top_percent=5-50&depth_mm=0.5-6&base_mm=4-12`) |
| `GET /api/datasets/{id}/orthotic.stl` | the same design as a binary STL in mm |
| `GET /api/layout/{L or R}` | sensor positions on the numbering diagram plus the evidence behind the mapping |

Recording ids look like `P15_M3.I_L` (participant, take, side). Only ids found by scanning the dataset folder are accepted, so a request can never name a file path. Errors use normal HTTP codes (404 unknown recording or frame, 422 invalid input).

## How the sensor layout was checked

The dataset names the pressure columns `PressureSensor 0-31` and supplies a numbered diagram (labels 1-32), without saying how they correspond. `research/verify_sensor_layout.py` tests the natural guess (CSV index `i` = diagram label `i+1`, left files = left diagram, right files = right diagram) on all recordings:

1. **Heel-to-toe timing:** in each step the heel loads first and the toes last. Rank correlation between a sensor's timing and its position along the diagram: about -0.98 (left) and -0.97 (right); the best of 3000 shuffled layouts reached about 0.6.
2. **Neighbours move together:** correlation between sensor load patterns vs their distance on the diagram: about -0.89; the best shuffle reached about -0.4.

This is evidence, not proof. It does not test the medial/lateral direction or the authors' intent. Regenerate with `pip install -r requirements-research.txt` then `python research/verify_sensor_layout.py`, and compare `outputs/layout_check.png` with `insoles-number.jpeg`.

## Possible next steps

1. Ask the dataset authors to confirm the sensor mapping (and the medial/lateral orientation), then draw sensors on a real foot outline.
2. For any model, first obtain a **labelled** dataset (for example plantar pressure with documented ulcer outcomes, or clinician-labelled high-risk regions), split train and test by participant, and report meaningful metrics with their limits.
3. Replace the demonstration pocket depth and thickness with parameters validated with clinical input, and a manufacturing-ready geometry (anatomical outline, materials, tolerances).

## Team

Kritika Saxena, Mradul Khandelwal
