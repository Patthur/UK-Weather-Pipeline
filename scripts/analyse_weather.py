"""
analyse_weather.py

Reads the growing weather history (data/weather_history.csv), and produces:
  - data/latest_snapshot.csv : the most recent reading per city
  - data/city_averages.csv   : running average temperature per city
  - assets/temperature_trend.png : line chart of temperature over time per city

Runs after fetch_weather.py in the pipeline, so the outputs always reflect
the latest data. Designed to be safe even when history is still small.
"""

import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # non-interactive backend (no display in CI)
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

HISTORY_PATH = "data/weather_history.csv"
SNAPSHOT_PATH = "data/latest_snapshot.csv"
AVERAGES_PATH = "data/city_averages.csv"
CHART_PATH = "assets/temperature_trend.png"


def main():
    if not os.path.exists(HISTORY_PATH):
        print(f"No history file at {HISTORY_PATH} yet — nothing to analyse.")
        return

    df = pd.read_csv(HISTORY_PATH, parse_dates=["timestamp_utc"])
    if df.empty:
        print("History file is empty — nothing to analyse.")
        return

    print(f"Loaded {len(df):,} rows across {df['city'].nunique()} cities, "
          f"{df['timestamp_utc'].nunique()} timestamps.")

    # 1. Latest snapshot: most recent row per city
    latest = (df.sort_values("timestamp_utc")
                .groupby("city", as_index=False)
                .last()
                .sort_values("temperature_c", ascending=False))
    latest.to_csv(SNAPSHOT_PATH, index=False)
    print(f"Wrote latest snapshot -> {SNAPSHOT_PATH}")

    # 2. Running averages per city
    averages = (df.groupby("city")
                  .agg(readings=("temperature_c", "size"),
                       avg_temp_c=("temperature_c", "mean"),
                       min_temp_c=("temperature_c", "min"),
                       max_temp_c=("temperature_c", "max"),
                       avg_wind_kmh=("wind_speed_kmh", "mean"))
                  .round(1)
                  .sort_values("avg_temp_c", ascending=False)
                  .reset_index())
    averages.to_csv(AVERAGES_PATH, index=False)
    print(f"Wrote city averages -> {AVERAGES_PATH}")

    # 3. Temperature trend chart (only meaningful once we have >1 timestamp)
    os.makedirs(os.path.dirname(CHART_PATH), exist_ok=True)
    n_timestamps = df["timestamp_utc"].nunique()

    fig, ax = plt.subplots(figsize=(11, 6))
    for city, sub in df.sort_values("timestamp_utc").groupby("city"):
        if n_timestamps == 1:
            ax.scatter(sub["timestamp_utc"], sub["temperature_c"], label=city, s=60)
        else:
            ax.plot(sub["timestamp_utc"], sub["temperature_c"],
                    marker="o", markersize=3, label=city, linewidth=1.5)

    ax.set_title("UK city temperatures over time (auto-updated by pipeline)",
                 fontweight="bold", fontsize=13)
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel("Temperature (°C)")
    ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=9)
    ax.grid(True, alpha=0.3)
    if n_timestamps > 1:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
        fig.autofmt_xdate()
    plt.tight_layout()
    plt.savefig(CHART_PATH, dpi=110, bbox_inches="tight")
    plt.close()
    print(f"Wrote chart -> {CHART_PATH}")


if __name__ == "__main__":
    main()
