"""Quick look at one pressure recording (exploration script, not part of the app).

Run from the project root:

    pip install matplotlib
    python research/inspect_pressure.py                       # default recording
    python research/inspect_pressure.py P15/M3.I/M3.I_Preassure_L.csv --frame 100

The path is relative to the dataset folder, so it works on any computer.
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend import config  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("csv", nargs="?", default="P1/M1/M1_Preassure_L.csv",
                    help="path relative to the dataset folder")
parser.add_argument("--frame", type=int, default=50)
parser.add_argument("--no-plots", action="store_true")
args = parser.parse_args()

df = pd.read_csv(config.DATASET_DIR / args.csv)
pressure = df[config.SENSOR_COLUMNS]
frame = min(args.frame, len(df) - 1)

print("Dataset shape:", df.shape)
print("Number of pressure sensors:", len(config.SENSOR_COLUMNS))
print("Missing values:", int(df.isnull().sum().sum()))

calculated = pressure.sum(axis=1)
print("\nAverage calculated sum:", round(calculated.mean(), 2))
print("Maximum individual sensor value:", int(pressure.max().max()))

print("\n--- sumP validation ---")
if config.SUMP_COLUMN in df.columns:
    diff = (df[config.SUMP_COLUMN] - calculated).abs()
    print("Largest difference between sumP and calculated sum:", diff.max())
else:
    print("sumP column not found.")

values = pressure.iloc[frame]
above = values[values > values.mean()].sort_values(ascending=False)
print(f"\nFrame {frame}: mean {values.mean():.2f}")
print("Sensors above this frame's average (relative comparison only):")
print(above.to_string())

if not args.no_plots:
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 1, figsize=(12, 7))
    axes[0].plot(calculated.values)
    axes[0].set(title="Total sensor reading per frame", xlabel="Frame", ylabel="Sum of sensor values")
    axes[1].bar(range(32), values.values)
    axes[1].set(title=f"Sensor readings, frame {frame}", xlabel="Sensor (CSV index)", ylabel="Recorded sensor value")
    plt.tight_layout()
    plt.show()