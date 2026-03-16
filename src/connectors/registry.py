from __future__ import annotations

from dataclasses import replace
import pandas as pd

from src.config import AppConfig
from src.connectors.airport_openapi import AirportOpenApiConnector
from src.connectors.base import TravelDataGateway
from src.connectors.mock_connectors import MockTravelDataGateway
from src.connectors.traffic_openapi import TrafficOpenApiConnector
from src.connectors.weather_openapi import WeatherOpenApiConnector
from src.models import ConnectorStatus


class HybridTravelDataGateway(TravelDataGateway):
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.mock = MockTravelDataGateway()
        self.airport = AirportOpenApiConnector(config)
        self.traffic = TrafficOpenApiConnector(config)
        self.kma = WeatherOpenApiConnector(config)
        self._statuses = {status.dataset_name: status for status in self.mock.get_statuses()}

    def _with_status(self, dataset_name: str, status: str, detail: str) -> None:
        base = self._statuses.get(
            dataset_name,
            ConnectorStatus(source_name="Public Data", dataset_name=dataset_name, status=status, detail=detail),
        )
        self._statuses[dataset_name] = replace(base, status=status, detail=detail)

    def _load_dataset(
        self,
        dataset_name: str,
        real_loader,
        mock_loader,
        required_urls: list[str | None] | None = None,
        missing_detail: str = "서비스키, 엔드포인트 URL 또는 활용승인 정보가 아직 없어 mock 데이터를 사용합니다.",
    ) -> pd.DataFrame:
        if self.config.connector_mode == "mock":
            self._with_status(dataset_name, "mock only", "CONNECTOR_MODE=mock 설정으로 mock 데이터만 사용합니다.")
            return mock_loader()

        if not self.config.service_key or any(not url for url in required_urls or []):
            self._with_status(dataset_name, "pending user input", missing_detail)
            return mock_loader()

        try:
            data = real_loader()
            if data.empty:
                self._with_status(dataset_name, "pending user input", "실데이터 응답이 비어 있어 mock 데이터를 대신 사용합니다.")
                return mock_loader()
            self._with_status(dataset_name, "connected", "실제 공공데이터 API 호출에 성공했습니다.")
            return data
        except Exception as exc:
            self._with_status(dataset_name, "pending user input", f"실호출 실패로 mock 데이터 사용 중: {exc}")
            return mock_loader()

    def get_flights(self) -> pd.DataFrame:
        return self._load_dataset("여객편 운항정보", self.airport.get_flights, self.mock.get_flights, [self.config.airport_flights_url])

    def get_security_waits(self) -> pd.DataFrame:
        return self._load_dataset("출국장 혼잡도", self.airport.get_security_waits, self.mock.get_security_waits, [self.config.airport_congestion_url])

    def get_parking(self) -> pd.DataFrame:
        return self._load_dataset("주차장별 주차현황", self.airport.get_parking, self.mock.get_parking, [self.config.airport_parking_url])

    def get_traffic(self) -> pd.DataFrame:
        return self._load_dataset("교통소통정보", self.traffic.get_traffic, self.mock.get_traffic, [self.config.traffic_api_url])

    def get_amenities(self) -> pd.DataFrame:
        return self._load_dataset("상업시설 정보", self.airport.get_amenities, self.mock.get_amenities, [self.config.airport_amenities_url])

    def get_profiles(self) -> pd.DataFrame:
        return self.mock.get_profiles()

    def get_weather(self) -> pd.DataFrame:
        return self._load_dataset(
            "공항기상정보",
            self.airport.get_weather if self.config.airport_weather_url else self.kma.get_weather,
            self.mock.get_weather,
            [self.config.airport_weather_url or self.config.kma_weather_url],
            missing_detail="공항기상정보 또는 기상청 단기예보 URL/서비스키가 없어 mock 날씨를 사용합니다.",
        )

    def get_walking_times(self) -> pd.DataFrame:
        return self._load_dataset(
            "여객이동시설 도보소요시간",
            self.airport.get_walking_times,
            self.mock.get_walking_times,
            [self.config.airport_walking_url],
        )

    def get_statuses(self) -> list[ConnectorStatus]:
        return list(self._statuses.values())


def build_gateway() -> HybridTravelDataGateway:
    return HybridTravelDataGateway(AppConfig.from_env())
