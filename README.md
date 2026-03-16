# Smart Travel Orchestrator AI MVP

인천공항 AI-PORT 제안서의 핵심 아이디어를 심사위원이 3분 안에 이해할 수 있도록 재구성한 `공공데이터 활용형 MVP`다. 핵심은 단순 조회가 아니라 `집 -> 공항 이동 -> 체크인 -> 보안검색 -> 출국장 -> 탑승` 전 여정을 하나의 계획으로 다시 계산하는 데 있다.

## 무엇이 다른가

- 기존 공항 정보 제공은 `주차`, `혼잡도`, `항공편`을 따로 보여준다.
- 이 MVP는 공공데이터를 결합해 `권장 출발 시각`, `권장 보안검색 구역`, `권장 진입 노드`, `여유시간`, `리스크`를 한 번에 계산한다.
- 실데이터가 아직 없더라도, 실제 공공데이터 스키마를 닮은 mock CSV와 adapter 구조로 먼저 시연할 수 있다.

## 현재 상태

- `streamlit_app.py`: 실행 가능한 Streamlit 데모
- `src/connectors`: 공공데이터 real connector + mock fallback
- `src/services`: Personal Timeline / Risk Scoring / Re-routing / Recommendation 로직
- `data/*.csv`: 공공데이터 교체를 전제로 한 mock 데이터
- `docs/public_data_plan.md`: 데이터별 준비물과 연결 상태

## 보안과 공개 범위

- 저장소에는 실제 `PUBLIC_DATA_SERVICE_KEY`를 올리지 않는다.
- GitHub에는 예시 설정 파일인 `.env.example`만 포함되고, 실제 `.env`는 제외된다.
- 공개 저장소의 `.env.example`에는 실제 연결 후보 endpoint를 포함한다. 다만 실제 `PUBLIC_DATA_SERVICE_KEY`는 커밋하지 않는다.

## 실행 방법

1. Python 3.11 권장
2. 가상환경 생성
3. 의존성 설치
4. Streamlit 실행

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## 실데이터 전환 방법

루트의 `.env`를 자동으로 읽는다. 아래 값들을 넣으면 mock 대신 실제 공공데이터 호출을 시도한다.

```env
CONNECTOR_MODE=auto
PUBLIC_DATA_SERVICE_KEY=여기에_서비스키
AIRPORT_CONGESTION_URL=https://apis.data.go.kr/B551177/statusOfDepartureCongestion/getDepartureCongestion
AIRPORT_PARKING_URL=http://apis.data.go.kr/B551177/StatusOfParking/getTrackingParking
AIRPORT_FLIGHTS_URL=http://apis.data.go.kr/B551177/StatusOfPassengerFlightsOdp/getPassengerDeparturesOdp
AIRPORT_AMENITIES_URL=http://apis.data.go.kr/B551177/StatusOfFacility/getFacilityKR
AIRPORT_WALKING_URL=https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_000000002316651&fileDetailSn=1&insertDataPrcus=N
AIRPORT_WEATHER_URL=https://apis.data.go.kr/B551177/StatusOfPassengerWorldWeatherInfo/getPassengerDeparturesWorldWeather
ITS_API_KEY=test
TRAFFIC_API_URL=https://openapi.its.go.kr:9443/trafficInfo
KMA_WEATHER_URL=http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtFcst
```

- `CONNECTOR_MODE=mock`: 무조건 mock만 사용
- `CONNECTOR_MODE=auto`: 실데이터가 준비된 항목만 연결, 나머지는 mock fallback
- `ITS_API_KEY=test`: ITS 제공기관 샘플 키. 실제 운영 전환 시 발급 키로 교체 권장
- `AIRPORT_WEATHER_URL`: 인천국제공항공사 출발편 상대공항 기상정보 endpoint
- `KMA_WEATHER_URL`: 공항 기상 API 실패 시 사용하는 fallback endpoint
- `PUBLIC_DATA_SERVICE_KEY`: 저장소에는 실제 값이 없고, 로컬 `.env`에서만 관리

## 시연 포인트

- 출장객: 촉박한 일정에서 빠른 보안검색 구역과 출발 시각 재계산
- 외국인 관광객: 영어 UI, 면세/식음 추천, 게이트까지 경로와 챗 응답
- 교통약자/고령자: 걷기 최소화, 엘리베이터 우선 경로, 보수적 버퍼 반영

## 문서

- [public_data_plan.md](docs/public_data_plan.md)
- [architecture.md](docs/architecture.md)
- [scenarios.md](docs/scenarios.md)
