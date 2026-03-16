from __future__ import annotations

from src.models import TravelPlan


def _t(language: str, ko: str, en: str) -> str:
    return en if language == "English" else ko


def generate_assistant_response(question: str, plan: TravelPlan) -> str:
    q = question.lower().strip()
    lang = plan.request.ui_language
    checkpoint = plan.selected_checkpoint["zone_name"]
    gate = plan.selected_flight["gate"]
    parking_name = plan.selected_parking["lot_name"] if plan.selected_parking else "Transit Hub"
    amenity_text = ", ".join(
        amenity["name_en"] if lang == "English" else amenity["name"]
        for amenity in plan.amenities[:2]
    ) or _t(lang, "현재는 바로 게이트 이동이 더 안전합니다.", "Going straight to the gate is safer right now.")

    if any(keyword in q for keyword in ["언제", "when", "출발", "leave"]):
        return _t(
            lang,
            f"현재 기준 권장 출발 시각은 {plan.recommended_departure_time.strftime('%H:%M')}입니다. 공항에는 "
            f"{plan.recommended_airport_arrival_time.strftime('%H:%M')} 도착, 보안검색 진입은 "
            f"{plan.recommended_security_entry_time.strftime('%H:%M')}가 적정합니다.",
            f"Your recommended leave time is {plan.recommended_departure_time.strftime('%H:%M')}. "
            f"You should reach the airport at {plan.recommended_airport_arrival_time.strftime('%H:%M')} "
            f"and enter security by {plan.recommended_security_entry_time.strftime('%H:%M')}.",
        )

    if any(keyword in q for keyword in ["보안", "검색", "security", "lane"]):
        return _t(
            lang,
            f"지금은 {checkpoint} 보안검색 구역이 가장 유리합니다. 예상 대기 {plan.selected_checkpoint['predicted_wait_min']}분이며 "
            f"게이트까지 이어지는 내부 동선은 {plan.route_minutes}분입니다.",
            f"The best option now is the {checkpoint} security zone. Estimated wait is "
            f"{plan.selected_checkpoint['predicted_wait_min']} minutes and the internal route to the gate is {plan.route_minutes} minutes.",
        )

    if any(keyword in q for keyword in ["게이트", "gate", "얼마나", "how long"]):
        return _t(
            lang,
            f"{gate} 게이트까지 공항 내부 이동은 약 {plan.route_minutes}분입니다. 현재 계획상 탑승 전 여유시간은 {plan.spare_minutes}분입니다.",
            f"It takes about {plan.route_minutes} minutes to move through the airport to gate {gate}. "
            f"Your current boarding buffer is {plan.spare_minutes} minutes.",
        )

    if any(keyword in q for keyword in ["면세", "식음", "duty", "shop", "food"]):
        return _t(
            lang,
            f"현재 여유시간이면 {amenity_text} 순으로 들를 수 있습니다. 게이트 버퍼를 지키려면 10~15분 이내 체류를 권장합니다.",
            f"With your current buffer, you can stop by {amenity_text}. Keep the visit within 10 to 15 minutes to preserve the gate buffer.",
        )

    if any(keyword in q for keyword in ["엘리베이터", "약자", "accessible", "walk"]):
        return _t(
            lang,
            f"현재 경로는 접근성 우선 동선으로 구성되어 있으며 출발 지점 {parking_name}에서 엘리베이터 허브를 포함해 {checkpoint} 구역으로 이동합니다.",
            f"The route is accessibility-first. It starts from {parking_name}, includes the elevator hub, and guides you to {checkpoint}.",
        )

    if any(keyword in q for keyword in ["지연", "delay", "늦", "late"]):
        return _t(
            lang,
            "항공편 지연이 발생하면 체크인과 보안검색 진입 시점을 자동으로 늦추되, 혼잡이 커지면 더 빠른 검색 구역으로 재배치합니다.",
            "If the flight gets delayed, check-in and security shift later automatically, while the engine still re-routes you to a faster checkpoint if congestion rises.",
        )

    return _t(
        lang,
        f"현재 계획의 핵심은 {checkpoint} 보안검색 구역과 {gate} 게이트 기준 {plan.spare_minutes}분 버퍼를 지키는 것입니다. "
        "질문을 더 구체적으로 입력하면 출발 시각, 동선, 지연 대응, 쇼핑 가능 시간을 바로 답변하겠습니다.",
        f"The current plan is centered on preserving a {plan.spare_minutes}-minute buffer through {checkpoint} security toward gate {gate}. "
        "Ask more specifically about departure timing, routing, delay handling, or shopping time.",
    )
