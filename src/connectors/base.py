from __future__ import annotations

from abc import ABC, abstractmethod
import pandas as pd

from src.models import ConnectorStatus


class TravelDataGateway(ABC):
    @abstractmethod
    def get_flights(self) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def get_security_waits(self) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def get_parking(self) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def get_traffic(self) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def get_amenities(self) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def get_profiles(self) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def get_weather(self) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def get_walking_times(self) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def get_statuses(self) -> list[ConnectorStatus]:
        raise NotImplementedError
