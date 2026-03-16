from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import networkx as nx
import numpy as np
import pandas as pd

from src.models import RiskFactor, RerouteResult, TimelineItem, TravelPlan, TravelRequest


PREFERENCE_SETTINGS = {
    "가장 빠른 이동": {"extra_buffer": -10, "parking_weight": 0.6, "risk_bias": 0.15},
    "가장 안정적인 일정": {"extra_buffer": 18, "parking_weight": 0.4, "risk_bias": 0.3},
    "면세점/식음 이용 선호": {"extra_buffer": 12, "parking_weight": 0.3, "risk_bias": 0.2},
    "걷기 최소화": {"extra_buffer": 14, "parking_weight": 1.0, "risk_bias": 0.35},
}


SCENARIO_PRESETS: dict[str, dict[str, Any]] = {
    "출장객": {
        "flight_number": "KE623",
        "traveler_type": "business",
        "preference": "가장 빠른 이동",
        "current_location": "서울역",
        "approach_mode": "car",
        "ui_language": "한국어",
    },
    "외국인 관광객": {
        "flight_number": "SQ607",
        "traveler_type": "tourist",
        "preference": "면세점/식음 이용 선호",
        "current_location": "홍대입구",
        "approach_mode": "rail",
        "ui_language": "English",
    },
    "교통약자/고령자": {
        "flight_number": "OZ501",
        "traveler_type": "accessibility",
        "preference": "걷기 최소화",
        "current_location": "송도",
        "approach_mode": "car",
        "ui_language": "한국어",
    },
    "직접 입력": {},
}


def _t(language: str, ko: str, en: str) -> str:
    return en if language == "English" else ko


def normalize_terminal_name(value: Any) -> str:
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
    return mapping.get(raw, str(value).strip() if value else "Terminal 1")


def build_graph(walking_times: pd.DataFrame, terminal: str, needs_accessible: bool) -> nx.Graph:
    graph = nx.Graph()
    normalized_terminal = normalize_terminal_name(terminal)
    filtered = walking_times[walking_times["terminal"].map(normalize_terminal_name) == normalized_terminal]
    for row in filtered.to_dict(orient="records"):
        if needs_accessible and not bool(row["accessible"]):
            continue
        graph.add_edge(row["from_node"], row["to_node"], weight=float(row["minutes"]))
    return graph


def choose_flight(flights: pd.DataFrame, flight_number: str, departure_time: datetime, terminal: str) -> dict[str, Any]:
    flight_rows = flights[flights["flight_number"] == flight_number]
    if flight_rows.empty:
        flight_rows = flights[flights["terminal"].map(normalize_terminal_name) == normalize_terminal_name(terminal)]
    if flight_rows.empty:
        flight_rows = flights
    ranked = flight_rows.copy()
    ranked["distance_to_requested"] = (ranked["scheduled_departure"] - departure_time).abs()
    selected = ranked.sort_values("distance_to_requested").iloc[0].to_dict()
    selected["scheduled_departure"] = pd.to_datetime(selected["scheduled_departure"]).to_pydatetime()
    selected["estimated_departure"] = pd.to_datetime(selected["estimated_departure"]).to_pydatetime()
    return selected


def choose_profile(profiles: pd.DataFrame, traveler_type: str) -> dict[str, Any]:
    selected = profiles[profiles["traveler_type"] == traveler_type]
    if selected.empty:
        selected = profiles.iloc[[0]]
    row = selected.iloc[0].to_dict()
    row["needs_accessible_route"] = bool(row["needs_accessible_route"])
    return row


def choose_traffic_route(traffic: pd.DataFrame, current_location: str, approach_mode: str, override_duration: int | None = None) -> dict[str, Any]:
    options = traffic[(traffic["origin_name"] == current_location) & (traffic["mode"] == approach_mode)]
    if options.empty:
        options = traffic[traffic["mode"] == approach_mode]
    if options.empty:
        options = traffic
    route = options.sort_values(["incident_flag", "predicted_duration_min"]).iloc[0].to_dict()
    if override_duration is not None:
        route["predicted_duration_min"] = int(override_duration)
    route["incident_flag"] = bool(route["incident_flag"])
    return route


def choose_parking(
    parking: pd.DataFrame,
    terminal: str,
    preference: str,
    needs_accessible_route: bool,
    checkin_area: str,
) -> dict[str, Any] | None:
    if parking.empty:
        return None
    candidates = parking[parking["terminal"].map(normalize_terminal_name) == normalize_terminal_name(terminal)].copy()
    if candidates.empty:
        candidates = parking.copy()
    candidates["zone_match"] = (candidates["priority_zone"].str.lower() == str(checkin_area).lower()).astype(int)
    if needs_accessible_route:
        candidates = candidates.sort_values(["zone_match", "accessible_spaces", "walk_to_terminal_min"], ascending=[False, False, True])
    else:
        setting = PREFERENCE_SETTINGS[preference]
        candidates["rank_score"] = (
            candidates["zone_match"] * 22
            + (candidates["parking_type"] == "short_term").astype(int) * 10
            + (1 - candidates["occupancy_rate"]) * 60 * setting["parking_weight"]
            - candidates["walk_to_terminal_min"] * (0.8 if preference == "걷기 최소화" else 0.4)
            - (candidates["occupancy_rate"] >= 0.9).astype(int) * 20
        )
        candidates = candidates.sort_values("rank_score", ascending=False)
    return candidates.iloc[0].to_dict()


def choose_checkpoint(security_waits: pd.DataFrame, terminal: str, gate_zone: str, preference: str, profile: dict[str, Any]) -> dict[str, Any]:
    candidates = security_waits[security_waits["terminal"].map(normalize_terminal_name) == normalize_terminal_name(terminal)].copy()
    if candidates.empty:
        candidates = security_waits.copy()
    walk_column = f"gate_zone_{str(gate_zone).lower()}_min"
    walk_penalty = candidates.get(walk_column, pd.Series([12] * len(candidates)))
    preference_factor = 0.7 if preference == "가장 빠른 이동" else 0.5
    stability_factor = 0.8 if preference == "가장 안정적인 일정" else 0.4
    accessibility_penalty = np.where(
        profile["needs_accessible_route"] & (~candidates["accessible_route"]),
        25,
        0,
    )
    candidates["selection_score"] = (
        candidates["predicted_wait_min"] * (1.2 - preference_factor)
        + walk_penalty * (1.0 if preference == "걷기 최소화" else 0.6)
        + candidates["passenger_count"] / candidates["max_capacity"] * 25 * stability_factor
        + accessibility_penalty
    )
    return candidates.sort_values("selection_score").iloc[0].to_dict()


def choose_amenities(amenities: pd.DataFrame, terminal: str, gate_zone: str, spare_minutes: int, preference: str) -> list[dict[str, Any]]:
    if preference != "면세점/식음 이용 선호" or spare_minutes < 18:
        return []
    normalized_terminal = normalize_terminal_name(terminal)
    candidates = amenities[
        (amenities["terminal"].map(normalize_terminal_name) == normalized_terminal) & (amenities["zone"].isin([gate_zone, "Center"]))
    ].copy()
    if candidates.empty:
        candidates = amenities[amenities["terminal"].map(normalize_terminal_name) == normalized_terminal].copy()
    candidates["amenity_score"] = (
        candidates["open_now"].astype(int) * 20
        + candidates["accessible"].astype(int) * 10
        - candidates["walk_to_gate_min"] * 1.5
    )
    return candidates.sort_values("amenity_score", ascending=False).head(3).to_dict(orient="records")


def choose_weather(weather: pd.DataFrame, flight_row: dict[str, Any]) -> dict[str, Any]:
    if weather.empty:
        return {
            "station_name": "Incheon International Airport",
            "condition": "Clear",
            "precipitation_mm": 0.0,
            "wind_speed_mps": 4.0,
            "visibility_km": 10.0,
            "temperature_c": 12.0,
            "advisory_level": "normal",
        }
    if "flight_id" in weather.columns:
        matched = weather[weather["flight_id"] == flight_row["flight_number"]]
        if not matched.empty:
            return matched.iloc[0].to_dict()
    if "terminal" in weather.columns:
        matched = weather[weather["terminal"].map(normalize_terminal_name) == normalize_terminal_name(flight_row["terminal"])]
        if not matched.empty:
            return matched.iloc[0].to_dict()
    return weather.iloc[0].to_dict()


def build_route(
    walking_times: pd.DataFrame,
    terminal: str,
    approach_mode: str,
    parking_row: dict[str, Any] | None,
    flight_row: dict[str, Any],
    checkpoint_row: dict[str, Any],
    profile: dict[str, Any],
) -> tuple[list[str], int]:
    graph = build_graph(walking_times, terminal, bool(profile["needs_accessible_route"]))
    if approach_mode == "car" and parking_row:
        start_node = parking_row["entry_node"]
    elif approach_mode == "rail":
        start_node = "Transit-Hub"
    else:
        start_node = "Dropoff-Hub"
    security_node = checkpoint_row["route_node"]
    checkin_node = f"CheckIn-{flight_row['checkin_area']}"
    gate_node = f"Gate-{flight_row['gate_zone']}"
    nodes = [start_node, checkin_node, security_node, gate_node]
    if any(node not in graph for node in nodes):
        return _fallback_route(nodes, parking_row, checkpoint_row, flight_row, profile)
    total_path: list[str] = []
    total_minutes = 0
    for source, target in zip(nodes, nodes[1:]):
        try:
            path = nx.shortest_path(graph, source, target, weight="weight")
            segment_minutes = int(nx.shortest_path_length(graph, source, target, weight="weight"))
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return _fallback_route(nodes, parking_row, checkpoint_row, flight_row, profile)
        if total_path:
            total_path.extend(path[1:])
        else:
            total_path.extend(path)
        total_minutes += segment_minutes
    return total_path, total_minutes


def _fallback_route(
    nodes: list[str],
    parking_row: dict[str, Any] | None,
    checkpoint_row: dict[str, Any],
    flight_row: dict[str, Any],
    profile: dict[str, Any],
) -> tuple[list[str], int]:
    route = list(nodes)
    extra_minutes = 0
    if profile["needs_accessible_route"] and "Elevator-Hub" not in route:
        route.insert(1, "Elevator-Hub")
        extra_minutes += 4
    parking_walk = int(parking_row["walk_to_terminal_min"]) if parking_row else 6
    total_minutes = parking_walk + int(checkpoint_row["walk_from_checkin_min"]) + int(flight_row["gate_walk_min"]) + extra_minutes
    return route, total_minutes


def score_risk(
    profile: dict[str, Any],
    checkpoint_row: dict[str, Any],
    traffic_row: dict[str, Any],
    parking_row: dict[str, Any] | None,
    weather_row: dict[str, Any],
    spare_minutes: int,
    preference: str,
) -> tuple[int, str, list[RiskFactor]]:
    factors = []
    traffic_score = min(30, int(traffic_row["congestion_level"] * 35) + (10 if traffic_row["incident_flag"] else 0))
    factors.append(RiskFactor("Road access", traffic_score, f"예상 이동 {traffic_row['predicted_duration_min']}분, 혼잡지수 {traffic_row['congestion_level']:.2f}"))
    security_score = min(25, int(checkpoint_row["predicted_wait_min"] * 0.9))
    factors.append(RiskFactor("Security queue", security_score, f"{checkpoint_row['zone_name']} 예상 대기 {checkpoint_row['predicted_wait_min']}분"))
    if parking_row:
        parking_score = min(15, int(parking_row["occupancy_rate"] * 18))
        factors.append(RiskFactor("Parking availability", parking_score, f"{parking_row['lot_name']} 점유율 {parking_row['occupancy_rate']:.0%}"))
    weather_score = min(15, int(weather_row["wind_speed_mps"] * 0.8 + weather_row["precipitation_mm"] * 1.5 + max(0, 8 - weather_row["visibility_km"])))
    factors.append(RiskFactor("Weather", weather_score, f"{weather_row['condition']}, 강수 {weather_row['precipitation_mm']}mm, 시정 {weather_row['visibility_km']}km"))
    time_buffer_score = 0 if spare_minutes >= 35 else max(0, 30 - spare_minutes)
    factors.append(RiskFactor("Boarding buffer", time_buffer_score, f"탑승 전 잔여 버퍼 {spare_minutes}분"))
    total = min(100, sum(factor.score for factor in factors) + int(PREFERENCE_SETTINGS[preference]["risk_bias"] * 10) + (8 if profile["needs_accessible_route"] else 0))
    level = "low"
    if total >= 70:
        level = "critical"
    elif total >= 50:
        level = "high"
    elif total >= 30:
        level = "medium"
    return total, level, factors


def generate_plan(
    request: TravelRequest,
    flights: pd.DataFrame,
    security_waits: pd.DataFrame,
    parking: pd.DataFrame,
    traffic: pd.DataFrame,
    amenities: pd.DataFrame,
    profiles: pd.DataFrame,
    weather: pd.DataFrame,
    walking_times: pd.DataFrame,
) -> TravelPlan:
    profile = choose_profile(profiles, request.traveler_type)
    flight_row = choose_flight(flights, request.flight_number, request.departure_time, request.terminal)
    flight_row["terminal"] = normalize_terminal_name(request.terminal)
    traffic_row = choose_traffic_route(traffic, request.current_location, request.approach_mode, request.current_travel_time_min)
    parking_row = (
        choose_parking(
            parking,
            request.terminal,
            request.preference,
            bool(profile["needs_accessible_route"]),
            flight_row["checkin_area"],
        )
        if request.approach_mode == "car"
        else None
    )
    checkpoint_row = choose_checkpoint(security_waits, request.terminal, flight_row["gate_zone"], request.preference, profile)
    route, route_minutes = build_route(walking_times, request.terminal, request.approach_mode, parking_row, flight_row, checkpoint_row, profile)
    weather_row = choose_weather(weather, flight_row)

    extra_buffer = int(profile["buffer_min"] + PREFERENCE_SETTINGS[request.preference]["extra_buffer"])
    recommended_airport_arrival = flight_row["estimated_departure"] - timedelta(
        minutes=int(flight_row["boarding_buffer_min"]) + int(flight_row["gate_walk_min"]) + int(checkpoint_row["predicted_wait_min"]) + extra_buffer
    )
    recommended_checkin = recommended_airport_arrival + timedelta(minutes=4)
    recommended_security_entry = recommended_checkin + timedelta(minutes=int(flight_row["checkin_duration_min"]))
    recommended_departure = recommended_airport_arrival - timedelta(minutes=int(traffic_row["predicted_duration_min"]))
    spare_minutes = int(
        (
            flight_row["estimated_departure"]
            - timedelta(minutes=int(flight_row["boarding_buffer_min"]))
            - recommended_security_entry
            - timedelta(minutes=int(checkpoint_row["predicted_wait_min"]))
            - timedelta(minutes=int(flight_row["gate_walk_min"]))
        ).total_seconds()
        // 60
    )
    spare_minutes = max(spare_minutes, 0)

    amenities_plan = choose_amenities(amenities, request.terminal, flight_row["gate_zone"], spare_minutes, request.preference)
    total_risk, risk_level, risk_factors = score_risk(profile, checkpoint_row, traffic_row, parking_row, weather_row, spare_minutes, request.preference)
    alerts = []
    if traffic_row["incident_flag"]:
        alerts.append(_t(request.ui_language, "공항 접근도로 사고/정체가 감지되었습니다.", "Road incident or severe congestion is detected on the way to the airport."))
    if checkpoint_row["predicted_wait_min"] >= 25:
        alerts.append(_t(request.ui_language, "보안검색 대기가 길어 대체 구역 검토가 필요합니다.", "Security queue is long enough to justify a checkpoint switch."))
    if parking_row and parking_row["occupancy_rate"] >= 0.9:
        alerts.append(_t(request.ui_language, "선택 주차구역이 만차 임박입니다.", "The selected parking area is close to full."))
    if total_risk >= 70:
        alerts.append(_t(request.ui_language, "탑승 지연 위험이 높아 조기 출발을 권고합니다.", "Boarding-delay risk is high. Leaving earlier is recommended."))

    explanation = [
        _t(request.ui_language, f"가장 빠른 보안검색 구역은 {checkpoint_row['zone_name']}입니다.", f"The fastest checkpoint is {checkpoint_row['zone_name']}."),
        _t(request.ui_language, f"{request.current_location} 출발 예상 이동시간 {traffic_row['predicted_duration_min']}분을 반영했습니다.", f"The plan includes {traffic_row['predicted_duration_min']} minutes of travel time from {request.current_location}."),
        _t(request.ui_language, f"프로필 버퍼 {profile['buffer_min']}분과 선호 옵션을 함께 반영했습니다.", f"The route also includes a {profile['buffer_min']}-minute profile buffer plus your preference setting."),
    ]

    timeline = [
        TimelineItem("Leave origin", recommended_departure, _t(request.ui_language, "권장 출발 시각", "Recommended leave time")),
        TimelineItem("Airport arrival", recommended_airport_arrival, _t(request.ui_language, "권장 공항 도착", "Recommended airport arrival")),
        TimelineItem("Check-in", recommended_checkin, _t(request.ui_language, "권장 체크인 시점", "Recommended check-in")),
        TimelineItem("Security", recommended_security_entry, _t(request.ui_language, "권장 보안검색 진입", "Recommended security entry")),
        TimelineItem("Boarding ready", flight_row["estimated_departure"] - timedelta(minutes=int(flight_row["boarding_buffer_min"])), _t(request.ui_language, "탑승 준비 완료", "Boarding ready")),
    ]

    return TravelPlan(
        request=request,
        selected_flight=flight_row,
        selected_checkpoint=checkpoint_row,
        selected_parking=parking_row,
        selected_route=route,
        route_minutes=route_minutes,
        recommended_departure_time=recommended_departure,
        recommended_airport_arrival_time=recommended_airport_arrival,
        recommended_checkin_time=recommended_checkin,
        recommended_security_entry_time=recommended_security_entry,
        spare_minutes=spare_minutes,
        amenities=amenities_plan,
        alerts=alerts,
        timeline=timeline,
        risk_total=total_risk,
        risk_level=risk_level,
        risk_factors=risk_factors,
        explanation=explanation,
        forecast_snapshot={
            "traffic": traffic_row,
            "weather": weather_row,
            "checkpoint_wait": checkpoint_row["predicted_wait_min"],
            "parking": parking_row,
        },
    )


def simulate_event(
    event_key: str,
    request: TravelRequest,
    flights: pd.DataFrame,
    security_waits: pd.DataFrame,
    parking: pd.DataFrame,
    traffic: pd.DataFrame,
    amenities: pd.DataFrame,
    profiles: pd.DataFrame,
    weather: pd.DataFrame,
    walking_times: pd.DataFrame,
) -> RerouteResult:
    before = generate_plan(request, flights, security_waits, parking, traffic, amenities, profiles, weather, walking_times)
    security_after = security_waits.copy()
    parking_after = parking.copy()
    flights_after = flights.copy()
    traffic_after = traffic.copy()
    event_summary = ""
    if event_key == "security_spike":
        security_after.loc[security_after["checkpoint_id"] == before.selected_checkpoint["checkpoint_id"], "predicted_wait_min"] += 22
        security_after.loc[security_after["checkpoint_id"] == before.selected_checkpoint["checkpoint_id"], "crowd_level"] = "high"
        event_summary = "선택된 보안검색 구역의 혼잡이 급증했습니다."
    elif event_key == "gate_change":
        flights_after.loc[flights_after["flight_number"] == request.flight_number, "gate_zone"] = "C" if before.selected_flight["gate_zone"] != "C" else "A"
        flights_after.loc[flights_after["flight_number"] == request.flight_number, "gate_walk_min"] += 6
        event_summary = "게이트가 더 먼 구역으로 변경되었습니다."
    elif event_key == "road_congestion":
        mask = (traffic_after["origin_name"] == request.current_location) & (traffic_after["mode"] == request.approach_mode)
        traffic_after.loc[mask, "predicted_duration_min"] += 18
        traffic_after.loc[mask, "congestion_level"] += 0.18
        traffic_after.loc[mask, "incident_flag"] = True
        event_summary = "공항 접근도로 정체가 발생했습니다."
    elif event_key == "parking_full":
        if before.selected_parking:
            mask = parking_after["lot_id"] == before.selected_parking["lot_id"]
            parking_after.loc[mask, "occupancy_rate"] = 0.99
            parking_after.loc[mask, "available_spaces"] = 3
            parking_after.loc[mask, "status"] = "nearly_full"
        event_summary = "추천 주차구역이 만차 직전입니다."
    elif event_key == "boarding_soon":
        flights_after.loc[flights_after["flight_number"] == request.flight_number, "estimated_departure"] = pd.to_datetime(request.departure_time) + timedelta(minutes=35)
        event_summary = "탑승 마감이 임박해 여유시간이 크게 줄었습니다."
    after = generate_plan(request, flights_after, security_after, parking_after, traffic_after, amenities, profiles, weather, walking_times)
    delta_summary = [
        f"출발 시각 변화: {before.recommended_departure_time.strftime('%H:%M')} -> {after.recommended_departure_time.strftime('%H:%M')}",
        f"보안검색 변화: {before.selected_checkpoint['zone_name']} ({before.selected_checkpoint['predicted_wait_min']}분) -> {after.selected_checkpoint['zone_name']} ({after.selected_checkpoint['predicted_wait_min']}분)",
        f"탑승 전 버퍼 변화: {before.spare_minutes}분 -> {after.spare_minutes}분",
    ]
    if before.selected_parking and after.selected_parking:
        delta_summary.append(f"주차 추천 변화: {before.selected_parking['lot_name']} -> {after.selected_parking['lot_name']}")
    return RerouteResult(before_plan=before, after_plan=after, event_name=event_key, event_summary=event_summary, delta_summary=delta_summary)


def build_stage_cards(plan: TravelPlan) -> list[dict[str, str]]:
    checkpoint = plan.selected_checkpoint["zone_name"]
    parking = plan.selected_parking["lot_name"] if plan.selected_parking else "Transit Hub"
    amenities = ", ".join(amenity["name"] for amenity in plan.amenities[:2]) or "게이트 우선 이동"
    risk_label = {"low": "낮음", "medium": "보통", "high": "높음", "critical": "매우 높음"}[plan.risk_level]
    return [
        {
            "stage": "1. 출발 전",
            "current": f"{plan.request.current_location} 기준 예상 이동 {plan.forecast_snapshot['traffic']['predicted_duration_min']}분, 위험도 {risk_label}",
            "decision": "AI가 개인 프로필 버퍼와 접근 교통 상황을 결합해 권장 출발 시각을 계산",
            "action": f"{plan.recommended_departure_time.strftime('%H:%M')} 출발 권고",
            "impact": "평균 지각 리스크 15~25% 감소 가정",
        },
        {
            "stage": "2. 공항 이동",
            "current": f"선호 접근 방식 {plan.request.approach_mode}, 추천 진입 지점 {parking}",
            "decision": "혼잡도와 접근성 요구를 반영해 주차 또는 드롭오프 지점 결정",
            "action": f"{parking} 진입 후 {checkpoint} 검색 구역으로 이동",
            "impact": "공항 진입 후 방황 시간 5~12분 절감 가정",
        },
        {
            "stage": "3. 체크인 & 보안검색",
            "current": f"{checkpoint} 예상 대기 {plan.selected_checkpoint['predicted_wait_min']}분",
            "decision": "가장 짧은 대기열과 게이트 연결성의 균형을 선택",
            "action": f"{plan.recommended_security_entry_time.strftime('%H:%M')} 보안검색 진입",
            "impact": "대기시간 20~30% 절감 가정",
        },
        {
            "stage": "4. 출국장",
            "current": f"탑승 전 여유시간 {plan.spare_minutes}분",
            "decision": "여유시간이 충분하면 면세/식음 추천, 부족하면 즉시 게이트 이동",
            "action": amenities,
            "impact": "상업시설 체류 만족도 상승 가정",
        },
        {
            "stage": "5. 탑승",
            "current": f"{plan.selected_flight['gate']} 게이트, 내부 이동 {plan.route_minutes}분",
            "decision": "게이트까지의 도보/엘리베이터 동선을 고정하고 카운트다운 제공",
            "action": f"{(plan.selected_flight['estimated_departure'] - timedelta(minutes=plan.selected_flight['boarding_buffer_min'])).strftime('%H:%M')} 이전 게이트 도착",
            "impact": "탑승 임박 스트레스 완화 가정",
        },
    ]


def simulate_kpis(users: int, congestion: float, accuracy: float, acceptance: float, field_response: float) -> dict[str, float]:
    coordination_power = 0.28 * accuracy + 0.24 * acceptance + 0.18 * field_response
    congestion_pressure = 0.6 + congestion * 0.8
    wait_reduction = min(38.0, max(8.0, coordination_power * 48 / congestion_pressure))
    reroute_success = min(96.0, max(52.0, 48 + coordination_power * 42 - congestion * 10))
    delay_risk_reduction = min(44.0, max(10.0, 12 + accuracy * 18 + field_response * 14 - congestion * 6))
    satisfaction_delta = min(12.0, max(2.0, 2 + coordination_power * 10 - congestion * 1.2))
    accessibility_gain = min(40.0, max(8.0, 6 + field_response * 26 + acceptance * 8))
    baseline_wait = 18 + congestion * 22 + users / 900
    optimized_wait = baseline_wait * (1 - wait_reduction / 100)
    return {
        "baseline_wait_min": round(baseline_wait, 1),
        "optimized_wait_min": round(optimized_wait, 1),
        "wait_reduction_pct": round(wait_reduction, 1),
        "reroute_success_pct": round(reroute_success, 1),
        "delay_risk_reduction_pct": round(delay_risk_reduction, 1),
        "satisfaction_delta_pt": round(satisfaction_delta, 1),
        "accessibility_gain_pct": round(accessibility_gain, 1),
    }


def plan_to_frame(plan: TravelPlan) -> pd.DataFrame:
    return pd.DataFrame([{"Step": item.label, "Time": item.planned_time.strftime("%H:%M"), "Detail": item.detail} for item in plan.timeline])


def route_to_markdown(plan: TravelPlan, language: str) -> str:
    arrows = " -> ".join(plan.selected_route)
    return _t(language, f"권장 이동 경로: {arrows}", f"Recommended route: {arrows}")


def compare_plan_frame(result: RerouteResult) -> pd.DataFrame:
    rows = [
        {"항목": "권장 출발 시각", "변경 전": result.before_plan.recommended_departure_time.strftime("%H:%M"), "변경 후": result.after_plan.recommended_departure_time.strftime("%H:%M")},
        {"항목": "보안검색 구역", "변경 전": result.before_plan.selected_checkpoint["zone_name"], "변경 후": result.after_plan.selected_checkpoint["zone_name"]},
        {"항목": "탑승 전 여유시간", "변경 전": f"{result.before_plan.spare_minutes}분", "변경 후": f"{result.after_plan.spare_minutes}분"},
        {"항목": "리스크 점수", "변경 전": result.before_plan.risk_total, "변경 후": result.after_plan.risk_total},
    ]
    return pd.DataFrame(rows)
