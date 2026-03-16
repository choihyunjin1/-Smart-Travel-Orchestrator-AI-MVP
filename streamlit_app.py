from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.connectors.registry import build_gateway
from src.models import TravelRequest
from src.services.assistant import generate_assistant_response
from src.services.orchestration import (
    SCENARIO_PRESETS,
    build_stage_cards,
    compare_plan_frame,
    generate_plan,
    normalize_terminal_name,
    plan_to_frame,
    route_to_markdown,
    simulate_event,
    simulate_kpis,
)


def t(language: str, ko: str, en: str) -> str:
    return en if language == "English" else ko


@st.cache_resource(show_spinner=False)
def get_gateway():
    return build_gateway()


def load_data():
    gateway = get_gateway()
    return gateway, {
        "flights": gateway.get_flights(),
        "security": gateway.get_security_waits(),
        "parking": gateway.get_parking(),
        "traffic": gateway.get_traffic(),
        "amenities": gateway.get_amenities(),
        "profiles": gateway.get_profiles(),
        "weather": gateway.get_weather(),
        "walking": gateway.get_walking_times(),
        "statuses": gateway.get_statuses(),
    }


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; }
        .stApp {
            background:
                radial-gradient(circle at top right, rgba(247, 200, 104, 0.18), transparent 28%),
                radial-gradient(circle at left 30%, rgba(22, 56, 98, 0.14), transparent 30%),
                linear-gradient(180deg, #f7f8fb 0%, #eef2f7 100%);
        }
        .hero {
            background: linear-gradient(135deg, #0a2342 0%, #163862 65%, #e7a93f 140%);
            border-radius: 24px;
            padding: 28px 32px;
            color: white;
            margin-bottom: 1rem;
            box-shadow: 0 18px 50px rgba(10, 35, 66, 0.18);
        }
        .hero p { margin-bottom: 0; font-size: 0.98rem; color: rgba(255,255,255,0.86); }
        .metric-card, .info-card {
            border-radius: 18px;
            padding: 18px 20px;
            background: rgba(255,255,255,0.92);
            border: 1px solid rgba(10,35,66,0.08);
            box-shadow: 0 10px 30px rgba(16, 24, 40, 0.06);
        }
        .metric-card .label {
            color: #627089;
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }
        .metric-card .value {
            font-size: 1.55rem;
            font-weight: 700;
            color: #0a2342;
            margin-top: 0.35rem;
        }
        .status-pill {
            display: inline-block;
            border-radius: 999px;
            padding: 6px 10px;
            font-size: 0.76rem;
            font-weight: 600;
            margin: 0 8px 8px 0;
        }
        .status-connected { background: #e8f7ef; color: #116b3a; }
        .status-pending { background: #fff3d6; color: #8a5b00; }
        .status-mock { background: #eaf0ff; color: #2449a7; }
        .section-caption { color: #5a6982; margin-bottom: 1rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value: str, help_text: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="label">{label}</div>
            <div class="value">{value}</div>
            <div style="color:#627089; margin-top:6px; font-size:0.9rem;">{help_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_pills(statuses) -> None:
    chunks = []
    for status in statuses:
        css_class = {
            "connected": "status-connected",
            "pending user input": "status-pending",
            "mock only": "status-mock",
        }.get(status.status, "status-mock")
        chunks.append(f"<span class='status-pill {css_class}'>{status.dataset_name}: {status.status}</span>")
    st.markdown("".join(chunks), unsafe_allow_html=True)


def render_timeline_chart(plan) -> None:
    timeline_df = plan_to_frame(plan)
    figure = go.Figure(
        go.Scatter(
            x=timeline_df["Time"],
            y=timeline_df["Step"],
            mode="lines+markers+text",
            text=timeline_df["Detail"],
            textposition="top center",
            line={"color": "#163862", "width": 4},
            marker={"size": 12, "color": "#e7a93f"},
        )
    )
    figure.update_layout(
        height=340,
        margin={"l": 20, "r": 20, "t": 40, "b": 20},
        xaxis_title="Time",
        yaxis_title="Journey",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.9)",
    )
    st.plotly_chart(figure, use_container_width=True)


def render_risk_breakdown(plan) -> None:
    risk_frame = pd.DataFrame(
        [{"Factor": factor.name, "Score": factor.score, "Detail": factor.detail} for factor in plan.risk_factors]
    )
    fig = go.Figure(
        go.Bar(
            x=risk_frame["Score"],
            y=risk_frame["Factor"],
            orientation="h",
            marker_color=["#163862", "#355c7d", "#6c8ebf", "#e7a93f", "#c95a49"],
        )
    )
    fig.update_layout(
        height=280,
        margin={"l": 20, "r": 20, "t": 20, "b": 20},
        xaxis_title="Risk score",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.9)",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(risk_frame, use_container_width=True, hide_index=True)


def main() -> None:
    st.set_page_config(page_title="Smart Travel Orchestrator AI", layout="wide", page_icon="🛫")
    inject_styles()
    _, data = load_data()

    st.markdown(
        """
        <div class="hero">
            <h1 style="margin:0;">AI 여행 오케스트레이션 동반자</h1>
            <p>공공데이터 기반으로 집에서 탑승구까지의 의사결정을 다시 계산하는 심사위원 설득용 MVP입니다.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_status_pills(data["statuses"])
    st.caption("서비스키/활용승인이 없으면 공공데이터 스키마를 반영한 mock adapter로 자동 전환됩니다.")

    scenario_name = st.sidebar.selectbox("시연 시나리오", list(SCENARIO_PRESETS.keys()))
    preset = SCENARIO_PRESETS[scenario_name]

    flights = data["flights"].sort_values("scheduled_departure").reset_index(drop=True)
    flights["terminal_normalized"] = flights["terminal"].map(normalize_terminal_name)
    flight_options = flights.to_dict(orient="records")
    default_flight = preset.get("flight_number", flight_options[0]["flight_number"])
    default_index = next((idx for idx, row in enumerate(flight_options) if row["flight_number"] == default_flight), 0)
    selected_flight_row = st.sidebar.selectbox(
        "항공편",
        flight_options,
        index=default_index,
        format_func=lambda row: f"{row['flight_number']} | {row['destination']} | {pd.to_datetime(row['scheduled_departure']).strftime('%m-%d %H:%M')} | {row['terminal_normalized']}",
    )
    selected_flight_number = selected_flight_row["flight_number"]

    ui_language = st.sidebar.selectbox("UI Language", ["한국어", "English"], index=0 if preset.get("ui_language", "한국어") == "한국어" else 1)
    departure_date = st.sidebar.date_input("출발 날짜", value=selected_flight_row["scheduled_departure"].date())
    departure_time = st.sidebar.time_input("출발 시각", value=selected_flight_row["scheduled_departure"].time())
    terminals = sorted(flights["terminal_normalized"].unique().tolist())
    default_terminal = selected_flight_row["terminal_normalized"]
    terminal = st.sidebar.selectbox("터미널", terminals, index=terminals.index(default_terminal))

    traffic_options = data["traffic"]
    origin_choices = sorted(traffic_options["origin_name"].unique().tolist())
    default_origin = preset.get("current_location", origin_choices[0])
    origin_index = origin_choices.index(default_origin) if default_origin in origin_choices else 0
    current_location = st.sidebar.selectbox("현재 위치", origin_choices, index=origin_index)
    approach_modes = ["car", "rail", "taxi"]
    default_mode = preset.get("approach_mode", "car")
    mode_index = approach_modes.index(default_mode) if default_mode in approach_modes else 0
    approach_mode = st.sidebar.selectbox("공항 접근 방식", approach_modes, index=mode_index)
    traffic_rows = traffic_options[(traffic_options["origin_name"] == current_location) & (traffic_options["mode"] == approach_mode)]
    default_travel_min = int(traffic_rows.iloc[0]["predicted_duration_min"]) if not traffic_rows.empty else 70
    current_travel_time_min = st.sidebar.slider("공항까지 예상 이동시간(분)", 30, 180, default_travel_min, 5)

    profile_options = data["profiles"]["traveler_type"].tolist()
    default_profile = preset.get("traveler_type", profile_options[0])
    profile_index = profile_options.index(default_profile) if default_profile in profile_options else 0
    traveler_type = st.sidebar.selectbox(
        "이용자 유형",
        profile_options,
        index=profile_index,
        format_func=lambda x: {
            "general": "일반 여행객",
            "business": "출장객",
            "tourist": "외국인 관광객",
            "accessibility": "교통약자/고령자",
        }.get(x, x),
    )
    preference_options = ["가장 빠른 이동", "가장 안정적인 일정", "면세점/식음 이용 선호", "걷기 최소화"]
    default_preference = preset.get("preference", preference_options[0])
    preference_index = preference_options.index(default_preference) if default_preference in preference_options else 0
    preference = st.sidebar.selectbox("선호 옵션", preference_options, index=preference_index)

    request = TravelRequest(
        flight_number=selected_flight_number,
        departure_time=datetime.combine(departure_date, departure_time),
        terminal=terminal,
        current_location=current_location,
        current_travel_time_min=current_travel_time_min,
        traveler_type=traveler_type,
        preference=preference,
        ui_language=ui_language,
        approach_mode=approach_mode,
    )

    plan = generate_plan(
        request,
        data["flights"],
        data["security"],
        data["parking"],
        data["traffic"],
        data["amenities"],
        data["profiles"],
        data["weather"],
        data["walking"],
    )

    dashboard_tab, reroute_tab, stages_tab, assistant_tab, kpi_tab = st.tabs(
        ["A. 오케스트레이션 대시보드", "B. 재조정 시뮬레이터", "C. 여정 단계별 화면", "D. AI 어시스턴트", "E. KPI 시뮬레이션"]
    )

    with dashboard_tab:
        st.subheader(t(ui_language, "여정 전체를 하나의 계획으로 합치는 AI", "AI that turns fragmented airport info into one journey plan"))
        st.markdown(
            f"<p class='section-caption'>{t(ui_language, '차별점: 단순 조회가 아니라 출발 시각, 보안검색 구역, 공항 내 동선, 상업시설 체류 가능 시간을 함께 계산합니다.', 'Differentiator: this does not just show data. It jointly calculates leave time, checkpoint choice, in-airport route, and dwell-time for shopping or dining.')}</p>",
            unsafe_allow_html=True,
        )
        metric_cols = st.columns(4)
        with metric_cols[0]:
            render_metric_card("Recommended leave", plan.recommended_departure_time.strftime("%H:%M"), t(ui_language, "현재 위치 기준", "From your origin"))
        with metric_cols[1]:
            render_metric_card("Airport arrival", plan.recommended_airport_arrival_time.strftime("%H:%M"), plan.selected_checkpoint["zone_name"])
        with metric_cols[2]:
            render_metric_card("Security entry", plan.recommended_security_entry_time.strftime("%H:%M"), t(ui_language, "체크인 이후 진입", "Enter after check-in"))
        with metric_cols[3]:
            render_metric_card("Spare buffer", f"{plan.spare_minutes} min", f"Risk {plan.risk_total}/100 ({plan.risk_level})")

        left, right = st.columns([1.25, 1])
        with left:
            st.markdown(f"### {t(ui_language, '개인화 타임라인', 'Personal timeline')}")
            render_timeline_chart(plan)
            st.markdown(route_to_markdown(plan, ui_language))
            if plan.alerts:
                st.warning("\n".join(plan.alerts))
        with right:
            st.markdown(f"### {t(ui_language, 'AI 판단 근거', 'Why the engine chose this plan')}")
            for explanation in plan.explanation:
                st.markdown(f"- {explanation}")
            st.markdown(f"### {t(ui_language, '리스크 스코어', 'Risk scoring')}")
            render_risk_breakdown(plan)

        st.markdown(f"### {t(ui_language, '추천 공항 행동', 'Recommended airport actions')}")
        action_cols = st.columns(3)
        with action_cols[0]:
            render_metric_card("Checkpoint", f"{plan.selected_checkpoint['zone_name']} / {plan.selected_checkpoint['predicted_wait_min']}분", t(ui_language, "가장 유리한 검색 구역", "Best security zone"))
        with action_cols[1]:
            parking_text = plan.selected_parking["lot_name"] if plan.selected_parking else "Transit Hub"
            render_metric_card("Arrival node", parking_text, t(ui_language, "공항 진입 지점", "Airport arrival node"))
        with action_cols[2]:
            amenity_text = ", ".join(amenity["name_en"] if ui_language == "English" else amenity["name"] for amenity in plan.amenities[:2]) or t(ui_language, "게이트 우선 이동", "Go straight to the gate")
            render_metric_card("Dwell option", amenity_text, t(ui_language, "면세/식음 가능 여부", "Duty-free / dining window"))

    with reroute_tab:
        st.subheader("실시간 동선 재조정 시뮬레이터")
        event_key = st.selectbox(
            "이벤트 시나리오",
            [("security_spike", "보안검색 혼잡 급증"), ("gate_change", "게이트 변경"), ("road_congestion", "공항 접근도로 정체"), ("parking_full", "주차구역 만차"), ("boarding_soon", "탑승시간 임박")],
            format_func=lambda item: item[1],
        )[0]
        reroute = simulate_event(
            event_key,
            request,
            data["flights"],
            data["security"],
            data["parking"],
            data["traffic"],
            data["amenities"],
            data["profiles"],
            data["weather"],
            data["walking"],
        )
        comparison_cols = st.columns(2)
        with comparison_cols[0]:
            st.markdown("### 변경 전 계획")
            st.dataframe(plan_to_frame(reroute.before_plan), use_container_width=True, hide_index=True)
        with comparison_cols[1]:
            st.markdown("### 변경 후 계획")
            st.dataframe(plan_to_frame(reroute.after_plan), use_container_width=True, hide_index=True)
        st.info(reroute.event_summary)
        st.dataframe(compare_plan_frame(reroute), use_container_width=True, hide_index=True)
        for line in reroute.delta_summary:
            st.markdown(f"- {line}")

    with stages_tab:
        st.subheader("여정 단계별 화면")
        stage_cards = build_stage_cards(plan)
        stage_columns = st.columns(len(stage_cards))
        for column, stage in zip(stage_columns, stage_cards):
            with column:
                st.markdown(
                    f"""
                    <div class="info-card">
                        <h4 style="margin-top:0;">{stage['stage']}</h4>
                        <p><strong>현재 상황</strong><br>{stage['current']}</p>
                        <p><strong>AI 판단</strong><br>{stage['decision']}</p>
                        <p><strong>행동 제안</strong><br>{stage['action']}</p>
                        <p><strong>예상 절감 효과</strong><br>{stage['impact']}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with assistant_tab:
        st.subheader("상황형 AI 어시스턴트")
        st.caption("실제 LLM 연결 없이 현재 계획과 데이터 상태를 반영하는 응답입니다.")
        suggested_questions = [
            "지금 언제 출발해야 해?",
            "어느 보안검색 구역이 제일 빨라?",
            "게이트까지 얼마나 걸려?",
            "면세점 들를 시간 있어?",
            "엘리베이터 포함 경로는?",
            "항공편 지연 시 어떻게 바뀌어?",
        ]
        st.markdown(" | ".join(f"`{question}`" for question in suggested_questions))
        question = st.text_input("질문 입력", value=suggested_questions[0] if ui_language == "한국어" else "When should I leave now?")
        if question:
            st.success(generate_assistant_response(question, plan))

    with kpi_tab:
        st.subheader("가정 기반 KPI 시뮬레이션")
        st.caption("아래 수치는 실제 실증 결과가 아니라 심사위원 설명용 시뮬레이션입니다.")
        slider_cols = st.columns(5)
        users = slider_cols[0].slider("이용자 수", 500, 12000, 3500, 250)
        congestion = slider_cols[1].slider("혼잡 수준", 0.1, 1.0, 0.55, 0.05)
        accuracy = slider_cols[2].slider("예측 정확도", 0.4, 1.0, 0.82, 0.02)
        acceptance = slider_cols[3].slider("재안내 수용률", 0.3, 1.0, 0.68, 0.02)
        field_response = slider_cols[4].slider("현장 대응 여부", 0.3, 1.0, 0.72, 0.02)
        metrics = simulate_kpis(users, congestion, accuracy, acceptance, field_response)
        metric_cards = st.columns(5)
        metric_cards[0].metric("평균 예상 대기시간 변화", f"-{metrics['wait_reduction_pct']}%", f"{metrics['baseline_wait_min']} -> {metrics['optimized_wait_min']}분")
        metric_cards[1].metric("리라우팅 성공률", f"{metrics['reroute_success_pct']}%")
        metric_cards[2].metric("탑승 지연 위험 감소율", f"{metrics['delay_risk_reduction_pct']}%")
        metric_cards[3].metric("사용자 만족도 예상 변화", f"+{metrics['satisfaction_delta_pt']}pt")
        metric_cards[4].metric("교통약자 편의 개선", f"+{metrics['accessibility_gain_pct']}%")
        kpi_fig = go.Figure()
        kpi_fig.add_bar(name="Baseline", x=["Wait"], y=[metrics["baseline_wait_min"]], marker_color="#163862")
        kpi_fig.add_bar(name="Orchestrated", x=["Wait"], y=[metrics["optimized_wait_min"]], marker_color="#e7a93f")
        kpi_fig.update_layout(barmode="group", height=320, margin={"l": 20, "r": 20, "t": 20, "b": 20}, yaxis_title="Minutes", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,0.9)")
        st.plotly_chart(kpi_fig, use_container_width=True)

    st.markdown("---")
    st.markdown(t(ui_language, "이 MVP는 공공데이터 adapter와 mock fallback 구조로 작성되어 있으며, `docs/public_data_plan.md`를 기준으로 실제 API로 교체할 수 있습니다.", "This MVP is built on public-data adapters with a mock fallback. It can be switched to real APIs by following `docs/public_data_plan.md`."))


if __name__ == "__main__":
    main()
