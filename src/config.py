from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = BASE_DIR / "docs"

load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class AppConfig:
    connector_mode: str = "auto"
    service_key: str | None = None
    its_api_key: str | None = None
    airport_congestion_url: str | None = None
    airport_parking_url: str | None = None
    airport_flights_url: str | None = None
    airport_amenities_url: str | None = None
    airport_walking_url: str | None = None
    airport_weather_url: str | None = None
    traffic_api_url: str | None = None
    kma_weather_url: str | None = None

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            connector_mode=os.getenv("CONNECTOR_MODE", "auto").lower(),
            service_key=os.getenv("PUBLIC_DATA_SERVICE_KEY"),
            its_api_key=os.getenv("ITS_API_KEY"),
            airport_congestion_url=os.getenv("AIRPORT_CONGESTION_URL"),
            airport_parking_url=os.getenv("AIRPORT_PARKING_URL"),
            airport_flights_url=os.getenv("AIRPORT_FLIGHTS_URL"),
            airport_amenities_url=os.getenv("AIRPORT_AMENITIES_URL"),
            airport_walking_url=os.getenv("AIRPORT_WALKING_URL"),
            airport_weather_url=os.getenv("AIRPORT_WEATHER_URL"),
            traffic_api_url=os.getenv("TRAFFIC_API_URL"),
            kma_weather_url=os.getenv("KMA_WEATHER_URL"),
        )
