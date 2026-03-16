from __future__ import annotations

from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
import requests

from src.config import AppConfig, DATA_DIR


class TrafficOpenApiConnector:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def get_traffic(self) -> pd.DataFrame:
        if not self.config.traffic_api_url:
            raise ValueError("TRAFFIC_API_URL is not configured")
        params = {
            "apiKey": self.config.its_api_key or "test",
            "type": "all",
            "minX": 126.40,
            "maxX": 127.05,
            "minY": 37.35,
            "maxY": 37.62,
            "getType": "json",
        }
        response = requests.get(self.config.traffic_api_url, params=params, timeout=12)
        response.raise_for_status()
        if "json" in response.headers.get("content-type", "").lower():
            items = self._extract_json_items(response.json())
        else:
            items = self._extract_xml_items(response.text)
        return self._project_to_origin_routes(items)

    def _project_to_origin_routes(self, items: list[dict]) -> pd.DataFrame:
        baseline = pd.read_csv(DATA_DIR / "traffic_mock.csv", parse_dates=["snapshot_at"])
        if not items:
            return baseline

        speeds = [float(item.get("speed") or 0) for item in items if item.get("speed")]
        travel_times = [float(item.get("travelTime") or 0) for item in items if item.get("travelTime")]
        road_names = [item.get("roadName") for item in items if item.get("roadName")]
        created_dates = [item.get("createdDate") for item in items if item.get("createdDate")]

        average_speed = float(np.mean(speeds)) if speeds else 55.0
        average_travel = float(np.mean(travel_times)) if travel_times else 12.0
        congestion_level = float(np.clip(1 - (average_speed / 80), 0.15, 0.95))
        incident_flag = any(speed < 25 for speed in speeds)
        route_name = road_names[0] if road_names else "ITS Traffic Feed"
        snapshot_at = self._parse_created_date(created_dates[0]) if created_dates else pd.Timestamp.utcnow()

        origin_weights = {
            "서울역": 1.22,
            "홍대입구": 1.12,
            "송도": 0.88,
        }
        mode_weights = {
            "car": 1.0,
            "taxi": 1.05,
            "rail": 0.0,
        }

        rows = []
        for row in baseline.to_dict(orient="records"):
            updated = dict(row)
            updated["snapshot_at"] = snapshot_at
            if updated["mode"] in {"car", "taxi"}:
                factor = 1 + congestion_level * origin_weights.get(updated["origin_name"], 1.0) * mode_weights[updated["mode"]]
                sample_adjustment = 1 + min(average_travel / 25, 0.4)
                updated["predicted_duration_min"] = int(round(updated["baseline_duration_min"] * factor * sample_adjustment))
                updated["congestion_level"] = round(congestion_level, 2)
                updated["reliability_index"] = round(max(0.55, 0.9 - congestion_level * 0.35), 2)
                updated["incident_flag"] = incident_flag
                updated["route_name"] = f"{updated['route_name']} / {route_name}"
            else:
                updated["congestion_level"] = round(max(float(updated["congestion_level"]), congestion_level * 0.45), 2)
            rows.append(updated)

        return pd.DataFrame(rows)

    def _parse_created_date(self, value: str | None) -> pd.Timestamp:
        if not value:
            return pd.Timestamp.utcnow()
        try:
            return pd.to_datetime(value, format="%Y%m%d%H%M%S")
        except (ValueError, TypeError):
            return pd.Timestamp.utcnow()

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
