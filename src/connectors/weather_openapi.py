from __future__ import annotations

from datetime import datetime, timedelta
import re
import xml.etree.ElementTree as ET

import pandas as pd
import requests

from src.config import AppConfig


class WeatherOpenApiConnector:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def get_weather(self) -> pd.DataFrame:
        if not self.config.kma_weather_url:
            raise ValueError("KMA_WEATHER_URL is not configured")
        items = self._fetch_latest_items()
        if not items:
            raise ValueError("KMA weather returned no items")

        frame = pd.DataFrame(items)
        frame["forecast_at"] = pd.to_datetime(frame["fcstDate"] + frame["fcstTime"], format="%Y%m%d%H%M")
        target_time = frame["forecast_at"].sort_values().iloc[0]
        target = frame[frame["forecast_at"] == target_time]
        by_category = {row["category"]: row["fcstValue"] for _, row in target.iterrows()}

        precipitation = self._parse_precipitation(by_category.get("RN1"))
        wind_speed = self._safe_float(by_category.get("WSD"), 4.0)
        temperature = self._safe_float(by_category.get("T1H"), 12.0)
        sky = by_category.get("SKY")
        pty = by_category.get("PTY")
        condition = self._derive_condition(sky, pty)
        advisory_level = self._derive_advisory(precipitation, wind_speed, pty)

        return pd.DataFrame(
            [
                {
                    "snapshot_at": target_time,
                    "station_name": "Incheon International Airport (KMA grid)",
                    "condition": condition,
                    "precipitation_mm": precipitation,
                    "wind_speed_mps": wind_speed,
                    "visibility_km": 10.0,
                    "temperature_c": temperature,
                    "advisory_level": advisory_level,
                }
            ]
        )

    def _fetch_latest_items(self) -> list[dict]:
        for base_date, base_time in self._candidate_base_times():
            params = {
                "serviceKey": self.config.service_key,
                "pageNo": 1,
                "numOfRows": 1000,
                "dataType": "JSON",
                "base_date": base_date,
                "base_time": base_time,
                "nx": 55,
                "ny": 124,
            }
            response = requests.get(self.config.kma_weather_url, params=params, timeout=12)
            response.raise_for_status()
            if "json" in response.headers.get("content-type", "").lower():
                items = self._extract_json_items(response.json())
            else:
                items = self._extract_xml_items(response.text)
            if items:
                return items
        return []

    def _candidate_base_times(self) -> list[tuple[str, str]]:
        now = datetime.now()
        base = now.replace(minute=30 if now.minute >= 30 else 0, second=0, microsecond=0)
        return [
            ((base - timedelta(minutes=30 * step)).strftime("%Y%m%d"), (base - timedelta(minutes=30 * step)).strftime("%H%M"))
            for step in range(0, 6)
        ]

    def _derive_condition(self, sky: str | None, pty: str | None) -> str:
        precipitation_type = str(pty or "0")
        if precipitation_type == "1":
            return "Rain"
        if precipitation_type == "2":
            return "Rain/Snow"
        if precipitation_type == "3":
            return "Snow"
        if precipitation_type == "4":
            return "Shower"
        return {
            "1": "Clear",
            "3": "Mostly Cloudy",
            "4": "Cloudy",
        }.get(str(sky or "1"), "Clear")

    def _derive_advisory(self, precipitation: float, wind_speed: float, pty: str | None) -> str:
        if str(pty or "0") in {"2", "3"} or wind_speed >= 12:
            return "alert"
        if precipitation >= 5 or wind_speed >= 8:
            return "caution"
        return "normal"

    def _parse_precipitation(self, value: str | None) -> float:
        if not value:
            return 0.0
        if "강수없음" in value:
            return 0.0
        match = re.search(r"(\d+(\.\d+)?)", value)
        return float(match.group(1)) if match else 0.0

    def _safe_float(self, value: str | None, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _extract_json_items(self, payload: object) -> list[dict]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if not isinstance(payload, dict):
            return []
        queue = [payload]
        while queue:
            current = queue.pop(0)
            if isinstance(current, list) and current and all(isinstance(item, dict) for item in current):
                return current
            if isinstance(current, dict):
                queue.extend(current.values())
        return []

    def _extract_xml_items(self, text: str) -> list[dict]:
        root = ET.fromstring(text)
        items = root.findall(".//item")
        return [{child.tag: child.text for child in item} for item in items]
