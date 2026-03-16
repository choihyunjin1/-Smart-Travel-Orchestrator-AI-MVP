# Architecture

## 목표

이 MVP의 핵심은 `공공데이터 식별 -> 사용자 준비 요청 -> 준비 전 mock fallback -> 준비 후 실연결` 흐름을 코드 구조 자체에 반영하는 것이다.

## 상위 구조

```text
streamlit_app.py
src/
  connectors/
    airport_openapi.py
    traffic_openapi.py
    weather_openapi.py
    mock_connectors.py
    registry.py
  services/
    orchestration.py
    assistant.py
data/
  *_mock.csv
docs/
```

## 데이터 흐름

1. `streamlit_app.py`
   사용자의 항공편, 위치, 이동시간, 이용자 유형, 선호 옵션을 입력받는다.
2. `src/connectors/registry.py`
   `CONNECTOR_MODE`와 환경변수를 보고 실데이터 연결 가능 여부를 판단한다.
3. `real connector`
   공공데이터포털 API를 호출해 표준 DataFrame 스키마로 정규화한다.
4. `mock connector`
   실데이터가 없을 때 동일한 표준 스키마를 가진 CSV를 불러온다.
5. `src/services/orchestration.py`
   Personal Timeline Generator, Risk Scoring, Re-routing Engine, Recommendation Engine을 수행한다.
6. `src/services/assistant.py`
   현재 상태를 반영한 상황형 답변을 생성한다.

## 핵심 컴포넌트

### 1. Connector Layer

- 역할: 데이터 소스 차이를 숨기고 공통 스키마로 제공
- 원칙: mock과 real이 같은 메서드와 거의 같은 필드명을 사용
- 교체 단위: 데이터셋별로 부분 전환 가능

### 2. Personal Timeline Generator

- 입력: 항공편, 현재 위치, 접근 방식, 혼잡도, 이용자 프로필
- 출력:
  - 권장 출발 시각
  - 권장 공항 도착 시각
  - 권장 체크인 시점
  - 권장 보안검색 진입 시점
  - 탑승 전 여유시간

### 3. Recommendation Engine

- 가장 빠른 보안검색 구역 선택
- 공항 접근 방식별 진입 노드 선택
- 주차장 추천
- 여유시간 기반 면세/식음 추천
- 접근성 요구 시 엘리베이터 포함 경로 우선

### 4. Risk Scoring

- 도로 혼잡
- 보안검색 대기
- 주차 점유율
- 날씨
- 탑승 전 버퍼

점수를 합산해 `low / medium / high / critical`로 표기한다.

### 5. Re-routing Engine

이벤트 발생 시 기존 계획과 변경 후 계획을 즉시 비교한다.

- 보안검색 혼잡 급증
- 게이트 변경
- 공항 접근도로 정체
- 주차구역 만차
- 탑승시간 임박

## 접근성 반영

- `passenger_profiles_mock.csv`에 교통약자 전용 프로필이 있다.
- 접근성 요구가 있으면 비접근 가능 엣지를 경로 그래프에서 제외한다.
- 버퍼 시간을 추가하고, 엘리베이터 허브 경유 경로를 우선한다.

## 실연결 시 확장 포인트

- 서비스키와 endpoint만 설정하면 `registry.py`가 자동으로 실호출을 시도한다.
- 응답 스키마가 다르면 connector 내부 `field pick` 후보만 보강하면 된다.
- 일부 데이터만 준비되어도 나머지는 mock fallback으로 데모를 유지한다.
