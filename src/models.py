from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ConnectorStatus:
    source_name: str
    dataset_name: str
    status: str
    detail: str


@dataclass(frozen=True)
class TravelRequest:
    flight_number: str
    departure_time: datetime
    terminal: str
    current_location: str
    current_travel_time_min: int
    traveler_type: str
    preference: str
    ui_language: str
    approach_mode: str


@dataclass(frozen=True)
class TimelineItem:
    label: str
    planned_time: datetime
    detail: str


@dataclass(frozen=True)
class RiskFactor:
    name: str
    score: int
    detail: str


@dataclass
class TravelPlan:
    request: TravelRequest
    selected_flight: dict
    selected_checkpoint: dict
    selected_parking: dict | None
    selected_route: list[str]
    route_minutes: int
    recommended_departure_time: datetime
    recommended_airport_arrival_time: datetime
    recommended_checkin_time: datetime
    recommended_security_entry_time: datetime
    spare_minutes: int
    amenities: list[dict] = field(default_factory=list)
    alerts: list[str] = field(default_factory=list)
    timeline: list[TimelineItem] = field(default_factory=list)
    risk_total: int = 0
    risk_level: str = "low"
    risk_factors: list[RiskFactor] = field(default_factory=list)
    explanation: list[str] = field(default_factory=list)
    forecast_snapshot: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RerouteResult:
    before_plan: TravelPlan
    after_plan: TravelPlan
    event_name: str
    event_summary: str
    delta_summary: list[str]
