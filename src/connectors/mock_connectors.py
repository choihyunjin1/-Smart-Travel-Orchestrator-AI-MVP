from __future__ import annotations

from pathlib import Path
import pandas as pd

from src.config import DATA_DIR
from src.connectors.base import TravelDataGateway
from src.models import ConnectorStatus


class MockTravelDataGateway(TravelDataGateway):
    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self.data_dir = data_dir

    def _read_csv(self, filename: str, date_columns: list[str] | None = None) -> pd.DataFrame:
        path = self.data_dir / filename
        frame = pd.read_csv(path)
        for column in date_columns or []:
            frame[column] = pd.to_datetime(frame[column])
        return frame

    def get_flights(self) -> pd.DataFrame:
        return self._read_csv("flights_mock.csv", ["scheduled_departure", "estimated_departure"])

    def get_security_waits(self) -> pd.DataFrame:
        return self._read_csv("security_wait_mock.csv", ["snapshot_at"])

    def get_parking(self) -> pd.DataFrame:
        return self._read_csv("parking_mock.csv", ["snapshot_at"])

    def get_traffic(self) -> pd.DataFrame:
        return self._read_csv("traffic_mock.csv", ["snapshot_at"])

    def get_amenities(self) -> pd.DataFrame:
        return self._read_csv("amenities_mock.csv")

    def get_profiles(self) -> pd.DataFrame:
        return self._read_csv("passenger_profiles_mock.csv")

    def get_weather(self) -> pd.DataFrame:
        return self._read_csv("weather_mock.csv", ["snapshot_at"])

    def get_walking_times(self) -> pd.DataFrame:
        return self._read_csv("walking_times_mock.csv")

    def get_statuses(self) -> list[ConnectorStatus]:
        datasets = [
            ("Airport Public Data", "출국장 혼잡도"),
            ("Airport Public Data", "주차장별 주차현황"),
            ("Airport Public Data", "여객편 운항정보"),
            ("Airport Public Data", "상업시설 정보"),
            ("Airport Public Data", "여객이동시설 도보소요시간"),
            ("Airport Public Data", "공항기상정보"),
            ("Traffic Public Data", "교통소통정보"),
        ]
        return [
            ConnectorStatus(
                source_name=source_name,
                dataset_name=dataset_name,
                status="mock only",
                detail="실데이터 키/엔드포인트 미설정 상태. 공공데이터 필드 구조를 닮은 mock CSV로 시연 중.",
            )
            for source_name, dataset_name in datasets
        ]
