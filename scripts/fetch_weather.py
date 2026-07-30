"""
fetch_weather.py

Fetches current weather for a set of UK cities from the Open-Meteo API
(free, no API key required) and appends the results as new rows to a
growing historical dataset at data/weather_history.csv.

Designed to run on a schedule via GitHub Actions — every run adds a new
timestamped snapshot per city, so the dataset grows over time.
"""

import csv
import os
import sys
from datetime import datetime, timezone

import requests

API_URL = "https://api.open-meteo.com/v1/forecast"
HISTORY_PATH = "data/weather_history.csv"

# UK cities to track (name, latitude, longitude)
CITIES = [
    ("London", 51.5074, -0.1278),
    ("Birmingham", 52.4862, -1.8904),
    ("Manchester", 53.4808, -2.2426),
    ("Glasgow", 55.8642, -4.2518),
    ("Cardiff", 51.4816, -3.1791),
    ("Belfast", 54.5973, -5.9301),
    ("Edinburgh", 55.9533, -3.1883),
    ("Leeds", 53.8008, -1.5491),
]

# WMO weather codes -> human-readable description
WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    66: "Light freezing rain", 67: "Heavy freezing rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
}

FIELDNAMES = [
    "timestamp_utc", "city", "temperature_c", "apparent_temperature_c",
    "humidity_pct", "wind_speed_kmh", "precipitation_mm",
    "weather_code", "weather_description",
]


def fetch_city(name, lat, lon):
    """Fetch current weather for a single city; return a row dict."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ",".join([
            "temperature_2m", "apparent_temperature", "relative_humidity_2m",
            "wind_speed_10m", "precipitation", "weather_code",
        ]),
        "wind_speed_unit": "kmh",
        "timezone": "UTC",
    }
    resp = requests.get(API_URL, params=params, timeout=30)
    resp.raise_for_status()
    current = resp.json()["current"]

    code = current.get("weather_code")

    def rnd(v, n=1):
        return round(v, n) if isinstance(v, (int, float)) else v

    return {
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "city": name,
        "temperature_c": rnd(current.get("temperature_2m")),
        "apparent_temperature_c": rnd(current.get("apparent_temperature")),
        "humidity_pct": rnd(current.get("relative_humidity_2m"), 0),
        "wind_speed_kmh": rnd(current.get("wind_speed_10m")),
        "precipitation_mm": rnd(current.get("precipitation")),
        "weather_code": code,
        "weather_description": WEATHER_CODES.get(code, "Unknown"),
    }


def main():
    rows = []
    failures = []
    for name, lat, lon in CITIES:
        try:
            rows.append(fetch_city(name, lat, lon))
            print(f"Fetched {name}")
        except Exception as e:
            failures.append(name)
            print(f"Failed to fetch {name}: {e}", file=sys.stderr)

    if not rows:
        print("No data fetched for any city — aborting without writing.", file=sys.stderr)
        sys.exit(1)

    # Append to the growing history file (write header only if new)
    file_exists = os.path.exists(HISTORY_PATH)
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

    print(f"\nAppended {len(rows)} rows to {HISTORY_PATH}")
    if failures:
        print(f"Cities that failed this run: {', '.join(failures)}")


if __name__ == "__main__":
    main()
