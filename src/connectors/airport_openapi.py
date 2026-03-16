from __future__ import annotations

from datetime import datetime
import io
from pathlib import Path
import time
from typing import Any
import xml.etree.ElementTree as ET

import pandas as pd
import requests

from src.config import AppConfig, DATA_DIR


class AirportOpenApiConnector:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.walking_cache_path = DATA_DIR / "walking_times_public_cache.csv"

    def _normalize_terminal(self, value: Any, default: str = "Terminal 1") -> str:
        raw = str(value or "").strip().upper()
        mapping = {
            "P01": "Terminal 1",
            "P02": "Terminal 1",
            "P03": "Terminal 2",
            "T1": "Terminal 1",
            "T2": "Terminal 2",
            "TERMINAL 1": "Terminal 1",
            "TERMINAL 2": "Terminal 2",
            "탑승동": "Terminal 1",
        }
        return mapping.get(raw, str(value).strip() if value else default)

    def _derive_gate_zone(self, gate_value: Any) -> str:
        text = str(gate_value or "").strip()
        digits = "".join(ch for ch in text if ch.isdigit())
        if not digits:
            return "A"
        gate_number = int(digits)
        if gate_number < 50:
            return "A"
        if gate_number < 200:
            return "B"
        return "C"

    def _derive_checkin_area(self, checkin_range: Any) -> str:
        text = str(checkin_range or "").strip().upper()
        if not text:
            return "Center"
        first_char = text[0]
        if first_char in {"A", "B", "C", "D"}:
            return "East"
        if first_char in {"E", "F", "G", "H"}:
            return "Center"
        return "West"

    def _derive_security_zone(self, gate_id: Any) -> tuple[str, str]:
        text = str(gate_id or "").strip().upper()
        if text.endswith("_E"):
            return "East", "Security-East"
        if text.endswith("_W"):
            return "West", "Security-West"
        return "Center", "Security-Center"

    def _derive_crowd_level(self, wait_minutes: int) -> str:
        if wait_minutes >= 25:
            return "high"
        if wait_minutes >= 12:
            return "moderate"
        return "low"

    def _parse_terminal_from_text(self, value: Any, default: str = "Terminal 1") -> str:
        text = str(value or "")
        if "제2여객터미널" in text or "T2" in text.upper():
            return "Terminal 2"
        if "제1여객터미널" in text or "T1" in text.upper() or "탑승동" in text:
            return "Terminal 1"
        return default

    def _request_items(self, url: str, extra_params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        params = {
            "serviceKey": self.config.service_key,
            "pageNo": 1,
            "numOfRows": 200,
            "_type": "json",
        }
        params.update(extra_params or {})
        response = requests.get(url, params=params, timeout=12)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "json" in content_type.lower():
            return self._extract_json_items(response.json())
        return self._extract_xml_items(response.text)

    def _extract_json_items(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if not isinstance(payload, dict):
            return []
        queue: list[Any] = [payload]
        while queue:
            current = queue.pop(0)
            if isinstance(current, list) and current and all(isinstance(item, dict) for item in current):
                return current
            if isinstance(current, dict):
                queue.extend(current.values())
        return []

    def _extract_xml_items(self, text: str) -> list[dict[str, Any]]:
        root = ET.fromstring(text)
        items = root.findall(".//item")
        return [{child.tag: child.text for child in item} for item in items]

    def _pick(self, record: dict[str, Any], *keys: str, default: Any = None) -> Any:
        normalized = {str(key).lower(): value for key, value in record.items()}
        for key in keys:
            value = normalized.get(key.lower())
            if value not in (None, ""):
                return value
        return default

    def _decode_csv_items(self, content: bytes) -> list[dict[str, Any]]:
        last_error: Exception | None = None
        for encoding in ("utf-8-sig", "cp949", "euc-kr"):
            try:
                frame = pd.read_csv(io.BytesIO(content), encoding=encoding)
                return frame.to_dict(orient="records")
            except Exception as exc:
                last_error = exc
        if last_error:
            raise last_error
        return []

    def _read_csv_items(self, url: str) -> list[dict[str, Any]]:
        local_path = Path(url)
        if local_path.exists():
            return self._decode_csv_items(local_path.read_bytes())

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.data.go.kr/",
        }
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                self.walking_cache_path.write_bytes(response.content)
                return self._decode_csv_items(response.content)
            except Exception as exc:
                last_error = exc
                time.sleep(1 + attempt)

        if self.walking_cache_path.exists():
            return self._decode_csv_items(self.walking_cache_path.read_bytes())
        if last_error:
            raise last_error
        return []

    def _normalize_datetime(self, value: Any, fallback: str = "1970-01-01T00:00:00") -> pd.Timestamp:
        if value in (None, ""):
            return pd.Timestamp(fallback)
        try:
            return pd.to_datetime(value)
        except (ValueError, TypeError):
            return pd.Timestamp(fallback)

    def _normalize_clock_datetime(self, value: Any, reference: pd.Timestamp | None = None) -> pd.Timestamp:
        if value in (None, ""):
            base = reference or pd.Timestamp.now().normalize()
            return pd.Timestamp(base)
        text = str(value).strip()
        if text.isdigit() and len(text) == 4:
            base = (reference or pd.Timestamp.now()).normalize()
            normalized = base + pd.Timedelta(hours=int(text[:2]), minutes=int(text[2:]))
            if reference is not None:
                delta = normalized - reference
                if delta > pd.Timedelta(hours=12):
                    normalized -= pd.Timedelta(days=1)
                elif delta < -pd.Timedelta(hours=12):
                    normalized += pd.Timedelta(days=1)
            return normalized
        if text.isdigit() and len(text) == 12:
            return pd.to_datetime(text, format="%Y%m%d%H%M")
        if text.isdigit() and len(text) == 8:
            return pd.to_datetime(text, format="%Y%m%d")
        return self._normalize_datetime(text)

    def get_security_waits(self) -> pd.DataFrame:
        items = self._request_items(self.config.airport_congestion_url or "")
        rows = []
        for item in items:
            wait_min = int(float(self._pick(item, "estimatedwaittime", "waittime", "waitMinute", default=18)))
            queue_length = int(float(self._pick(item, "waitLength", "expectedpassenger", "passengerCount", default=90)))
            zone_name, route_node = self._derive_security_zone(self._pick(item, "gateId", "sgtareaid", "checkpointId", "securityId"))
            rows.append(
                {
                    "snapshot_at": self._normalize_datetime(
                        self._pick(item, "occurtime", "datetm", "snapshotAt", "baseDateTime", "dataTime", default=datetime.utcnow().isoformat())
                    ),
                    "terminal": self._normalize_terminal(self._pick(item, "terminalid", "terminal", "term", default="Terminal 1")),
                    "checkpoint_id": self._pick(item, "gateId", "sgtareaid", "checkpointId", "securityId", default="T1-Center"),
                    "zone_name": self._pick(item, "sgtareanm", "zoneName", "securityAreaName", default=zone_name),
                    "route_node": self._pick(item, "routeNode", default=route_node),
                    "predicted_wait_min": wait_min,
                    "crowd_level": str(self._pick(item, "congestion", "crowdLevel", default=self._derive_crowd_level(wait_min))).lower(),
                    "passenger_count": queue_length,
                    "max_capacity": int(float(self._pick(item, "maxcapacity", "capacity", default=max(queue_length + 40, 120)))),
                    "walk_from_checkin_min": int(float(self._pick(item, "walkFromCheckinMin", default=6))),
                    "gate_zone_a_min": int(float(self._pick(item, "gateZoneAMin", default=11 if zone_name == "Center" else 13))),
                    "gate_zone_b_min": int(float(self._pick(item, "gateZoneBMin", default=14 if zone_name == "Center" else 12))),
                    "gate_zone_c_min": int(float(self._pick(item, "gateZoneCMin", default=17 if zone_name == "Center" else 15))),
                    "accessible_route": str(self._pick(item, "accessibleRoute", default="true")).lower() == "true",
                }
            )
        return pd.DataFrame(rows)

    def get_parking(self) -> pd.DataFrame:
        items = self._request_items(self.config.airport_parking_url or "")
        rows = []
        for item in items:
            floor = self._pick(item, "floor", "parkinglot", default="")
            total_spaces = int(float(self._pick(item, "parkingarea", "totalSpace", default=1000)))
            used_spaces = int(float(self._pick(item, "parking", "usedSpace", default=700)))
            rows.append(
                {
                    "snapshot_at": self._normalize_datetime(self._pick(item, "datetm", "snapshotAt", default=datetime.utcnow().isoformat())),
                    "terminal": self._normalize_terminal(self._pick(item, "terminalid", "terminal", "term", default=self._parse_terminal_from_text(floor))),
                    "lot_id": self._pick(item, "parkinglotid", "lotId", default=floor or "T1-ST-A"),
                    "lot_name": self._pick(item, "parkinglot", "parkingnam", "lotName", default=floor or "Short-Term A"),
                    "parking_type": self._pick(
                        item,
                        "parkingtype",
                        "parkingType",
                        default="short_term" if "단기" in floor else "long_term" if "장기" in floor else "short_term",
                    ),
                    "available_spaces": max(total_spaces - used_spaces, 0),
                    "total_spaces": total_spaces,
                    "occupancy_rate": round(used_spaces / total_spaces, 3) if total_spaces else 0,
                    "walk_to_terminal_min": int(float(self._pick(item, "walkToTerminalMin", default=8 if "단기" in floor else 14))),
                    "accessible_spaces": int(float(self._pick(item, "accessibleSpaces", default=20))),
                    "status": self._pick(item, "parkingstatus", "status", default="available" if total_spaces - used_spaces > 0 else "full"),
                    "entry_node": self._pick(
                        item,
                        "entryNode",
                        default="Parking-East" if "동" in floor else "Parking-West" if "서" in floor else "Parking-Center",
                    ),
                    "priority_zone": self._pick(
                        item,
                        "priorityZone",
                        default="East" if "동" in floor else "West" if "서" in floor else "Center",
                    ),
                }
            )
        return pd.DataFrame(rows)

    def get_flights(self) -> pd.DataFrame:
        items = self._request_items(self.config.airport_flights_url or "")
        rows = []
        for item in items:
            scheduled = self._normalize_clock_datetime(
                self._pick(item, "scheduleDateTime", "std", "scheduleddeparturetime", default=datetime.utcnow().isoformat())
            )
            estimated = self._normalize_clock_datetime(
                self._pick(item, "estimatedDateTime", "etd", "estimateddeparturetime", default=scheduled.strftime("%H%M")),
                scheduled,
            )
            gate = self._pick(item, "gatenumber", "gate", default="101")
            gate_zone = self._pick(item, "gatezone", default=self._derive_gate_zone(gate))
            checkin_area = self._pick(item, "checkinArea", default=self._derive_checkin_area(self._pick(item, "chkinrange", default="F")))
            rows.append(
                {
                    "flight_id": self._pick(item, "flightid", "flightId", default="REAL-001"),
                    "airline": self._pick(item, "airline", "airlineNm", default="Unknown Airline"),
                    "flight_number": self._pick(item, "flightid", "flightNumber", "fnum", default="ICN000"),
                    "destination": self._pick(item, "airport", "destination", "city", default="Unknown"),
                    "terminal": self._normalize_terminal(self._pick(item, "terminalid", "terminal", default="Terminal 1")),
                    "scheduled_departure": scheduled,
                    "estimated_departure": estimated,
                    "gate": gate,
                    "gate_zone": gate_zone,
                    "checkin_area": checkin_area,
                    "checkin_open_min": int(float(self._pick(item, "checkinOpenMin", default=180))),
                    "checkin_duration_min": int(float(self._pick(item, "checkinDurationMin", default=18))),
                    "boarding_buffer_min": int(float(self._pick(item, "boardingBufferMin", default=25))),
                    "gate_walk_min": int(float(self._pick(item, "gateWalkMin", default=12 if gate_zone == "A" else 16 if gate_zone == "B" else 20))),
                    "status": self._pick(item, "status", "remark", default="ON_TIME"),
                    "delay_min": int((estimated - scheduled).total_seconds() // 60),
                }
            )
        return pd.DataFrame(rows)

    def get_amenities(self) -> pd.DataFrame:
        items = self._request_items(self.config.airport_amenities_url or "")
        rows = []
        for item in items:
            location_text = self._pick(item, "lckoreannm", "loc", "zone", default="")
            terminal = self._normalize_terminal(self._pick(item, "terminalid", "terminal", default=self._parse_terminal_from_text(location_text)))
            gate_zone = self._derive_gate_zone(location_text)
            category = self._pick(item, "cate", "category")
            if not category:
                category = "food" if any(word in str(item).lower() for word in ["커피", "베이커리", "샌드위치", "food"]) else "service"
            rows.append(
                {
                    "amenity_id": self._pick(item, "shopid", "amenityId", default="SHOP-001"),
                    "terminal": terminal,
                    "zone": self._pick(item, "loc", "zone", default=gate_zone if gate_zone in {"A", "B", "C"} else "Center"),
                    "category": category,
                    "name": self._pick(item, "entrpskoreannm", "shopnm", "name", default="Amenity"),
                    "name_en": self._pick(item, "shopnmeng", "nameEn", default=self._pick(item, "entrpskoreannm", "shopnm", "name", default="Amenity")),
                    "walk_from_security_min": int(float(self._pick(item, "walkFromSecurityMin", default=4 if "게이트" in location_text else 7))),
                    "walk_to_gate_min": int(float(self._pick(item, "walkToGateMin", default=6 if "게이트" in location_text else 10))),
                    "accessible": str(self._pick(item, "accessible", default="true")).lower() == "true",
                    "open_now": str(self._pick(item, "openNow", default="true")).lower() == "true",
                    "recommended_for": self._pick(item, "recommendedFor", default="general"),
                    "description": self._pick(item, "description", "trtmntprdlstkoreannm", default=location_text or "Public-data-powered amenity suggestion."),
                }
            )
        return pd.DataFrame(rows)

    def get_walking_times(self) -> pd.DataFrame:
        walking_url = self.config.airport_walking_url or ""
        if "filedownload.do" in walking_url.lower() or walking_url.lower().endswith(".csv"):
            items = self._read_csv_items(walking_url)
        else:
            items = self._request_items(walking_url)
        rows = []
        for item in items:
            rows.append(
                {
                    "terminal": self._normalize_terminal(self._pick(item, "terminalid", "terminal", "터미널", default="Terminal 1")),
                    "from_node": self._pick(item, "fromNode", "출발노드", "출발지", "출발시설", default="Transit-Hub"),
                    "to_node": self._pick(item, "toNode", "도착노드", "도착지", "도착시설", default="CheckIn-Center"),
                    "minutes": int(float(self._pick(item, "walkingtime", "minutes", "도보소요시간", "소요시간", default=4))),
                    "accessible": str(self._pick(item, "accessible", "교통약자경로", "엘리베이터경로", default="true")).lower() == "true",
                }
            )
        return pd.DataFrame(rows)

    def get_weather(self) -> pd.DataFrame:
        items = self._request_items(self.config.airport_weather_url or "")
        rows = []
        for item in items:
            wind_speed = float(self._pick(item, "windSpeed", "wind", "wsd", default=4))
            temperature = float(self._pick(item, "temperature", "temp", "tmp", default=12))
            precipitation = float(self._pick(item, "precipitation", "rn1", default=0))
            schedule_time = self._normalize_clock_datetime(self._pick(item, "scheduleDateTime", default=datetime.utcnow().isoformat()))
            estimated_time = self._normalize_clock_datetime(
                self._pick(item, "estimatedDateTime", default=schedule_time.strftime("%H%M")),
                schedule_time,
            )
            rows.append(
                {
                    "snapshot_at": estimated_time,
                    "flight_id": self._pick(item, "flightId", "flightid", default="UNKNOWN"),
                    "terminal": self._normalize_terminal(self._pick(item, "terminalid", "terminal", default="Terminal 1")),
                    "gate": self._pick(item, "gatenumber", "gate", default=""),
                    "station_name": self._pick(item, "airport", "stationName", "city", default="Incheon International Airport"),
                    "condition": self._pick(item, "weather", "sky", "status", default="Clear"),
                    "precipitation_mm": precipitation,
                    "wind_speed_mps": wind_speed,
                    "visibility_km": float(self._pick(item, "visibility", "vis", default=10)),
                    "temperature_c": temperature,
                    "humidity_pct": float(self._pick(item, "himidity", "humidity", default=55)),
                    "remark": self._pick(item, "remark", default=""),
                    "advisory_level": self._pick(
                        item,
                        "advisoryLevel",
                        default="caution" if wind_speed >= 8 or precipitation >= 3 else "normal",
                    ),
                }
            )
        return pd.DataFrame(rows)
