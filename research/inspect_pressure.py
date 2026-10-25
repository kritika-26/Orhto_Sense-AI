
import pandas as pd
import matplotlib.pyplot as plt

# Replace this with the actual path to your CSV file
CSV_PATH = r"C:\Users\mradu\Desktop\Plantorix\data\raw\InsolesOpitrackDataset\P1\M1\M1_Preassure_L.csv"

df = pd.read_csv(CSV_PATH)

# Select the 32 pressure sensor columns
sensor_cols = [
    col for col in df.columns
    if col.startswith("PressureSensor ")
]

pressure = df[sensor_cols]

print("Dataset shape:", df.shape)
print("Number of pressure sensors:", len(sensor_cols))
print("Missing values:", df.isnull().sum().sum())

print("\nPressure sensor statistics:")
print(pressure.describe().round(2))

# # Plot sensor readings across the recording
# plt.figure(figsize=(14, 6))
# plt.imshow(
#     pressure.T,
#     aspect="auto",
#     cmap="inferno",
#     interpolation="nearest"
# )
# plt.colorbar(label="Recorded sensor value")
# plt.xlabel("Frame / Row")
# plt.ylabel("Pressure sensor")
# plt.title("Plantorix: Left Insole Pressure Readings")
# plt.tight_layout()
# plt.show()



# Calculate simple pressure statistics for each frame
df["calculated_sum"] = pressure.sum(axis=1)
df["max_sensor_value"] = pressure.max(axis=1)
df["active_sensors"] = (pressure > 0).sum(axis=1)

print("\nOverall pressure statistics:")
print("Average calculated sum:", round(df["calculated_sum"].mean(), 2))
print("Maximum calculated sum:", round(df["calculated_sum"].max(), 2))
print("Maximum individual sensor value:", df["max_sensor_value"].max())
print("Average active sensors:", round(df["active_sensors"].mean(), 2))

# Plot total recorded sensor values across frames
import matplotlib.pyplot as plt

plt.figure(figsize=(12, 4))
plt.plot(df["calculated_sum"])
plt.xlabel("Frame / Row")
plt.ylabel("Sum of sensor values")
plt.title("Plantorix: Total Sensor Reading Across Frames")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()




print("\n--- sumP Validation ---")

if "sumP" in df.columns:
    comparison = pd.DataFrame({
        "sumP": df["sumP"],
        "calculated_sum": pressure.sum(axis=1)
    })

    comparison["difference"] = (
        comparison["sumP"] - comparison["calculated_sum"]
    )

    print(comparison.head(10).round(2))
    print("\nMean absolute difference:",
          round(comparison["difference"].abs().mean(), 2))

    print("Correlation:",
          round(comparison["sumP"].corr(
              comparison["calculated_sum"]
          ), 4))
else:
    print("sumP column not found.")
    print("Available columns:", df.columns.tolist())




import matplotlib.pyplot as plt

# Select one frame to inspect
frame_index = 50

values = pressure.iloc[frame_index].values
labels = [f"S{i}" for i in range(32)]

plt.figure(figsize=(14, 5))
plt.bar(labels, values)
plt.xlabel("Pressure sensor index")
plt.ylabel("Recorded sensor value")
plt.title(f"Plantorix: Sensor Readings at Frame {frame_index}")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()



# Identify sensors with readings above the frame average
frame_index = 50
values = pressure.iloc[frame_index]

frame_avg = values.mean()
high_sensors = values[values > frame_avg].sort_values(
    ascending=False
)

print(f"\nFrame: {frame_index}")
print(f"Average sensor reading: {frame_avg:.2f}")
print("\nSensors above frame average:")

print(high_sensors.to_string())
