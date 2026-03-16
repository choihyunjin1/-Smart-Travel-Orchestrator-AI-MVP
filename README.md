# Smart Travel Orchestrator AI MVP

인천공항 AI-PORT 제안서의 핵심 아이디어를 `공공데이터 활용형 MVP`로 구현한 Streamlit 앱이다.  
목표는 단순한 정보 조회가 아니라 `출발 전 -> 공항 이동 -> 체크인 -> 보안검색 -> 출국장 -> 탑승` 전 여정을 하나의 계획으로 재구성해, 사용자가 언제 출발하고 어디로 이동해야 하는지 즉시 판단할 수 있게 하는 것이다.

## 프로젝트 목적

- 기존 공항 정보 서비스는 `항공편`, `주차`, `혼잡도`, `시설` 정보를 각각 따로 보여주는 경우가 많다.
- 이 MVP는 공공데이터를 결합해 `권장 출발 시각`, `권장 공항 도착 시각`, `권장 보안검색 구역`, `권장 이동 경로`, `탑승 전 여유시간`, `리스크 알림`을 한 번에 계산한다.
- 심사위원이 3분 안에 `왜 단순 조회가 아니라 AI 오케스트레이션인가`를 이해할 수 있도록 설계했다.

## 구현 범위

이 앱에는 아래 5개 기능이 포함된다.

- `A. 여행 오케스트레이션 대시보드`
- `B. 실시간 동선 재조정 시뮬레이터`
- `C. 여정 단계별 화면`
- `D. AI 어시스턴트 UI`
- `E. KPI 시뮬레이션 화면`

추가로 아래 핵심 엔진이 구현되어 있다.

- `Personal Timeline Generator`
- `Risk Scoring`
- `Re-routing Engine`
- `Recommendation Engine`

## 현재 연결 상태

현재 앱은 `mock 전용 데모`가 아니라, 실제 공공데이터와 mock fallback을 함께 지원한다.

실호출 확인 완료:

- 인천국제공항공사 `출국장 혼잡도 조회`
- 인천국제공항공사 `주차 정보`
- 인천국제공항공사 `여객편 운항현황(다국어)` 출발편
- 인천국제공항공사 `상업 시설 정보 서비스`
- 인천국제공항공사 `출국장도보소요시간정보` 파일데이터
- 인천국제공항공사 `기상 정보` 출발편 상대공항 기상정보
- 기상청 `초단기예보`
- ITS `교통소통정보`

아직 mock 성격으로 남는 부분:

- KPI 수치 자체
- 단계별 절감효과 문구
- AI 어시스턴트의 응답 템플릿

세부 연결 계획은 [docs/public_data_plan.md](docs/public_data_plan.md)에 정리되어 있다.

## 기술 스택

- Python 3.11
- Streamlit
- pandas
- numpy
- plotly
- networkx
- requests
- python-dotenv

## 폴더 구조

```text
streamlit_app.py
requirements.txt
src/
  config.py
  models.py
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
  flights_mock.csv
  security_wait_mock.csv
  parking_mock.csv
  traffic_mock.csv
  amenities_mock.csv
  passenger_profiles_mock.csv
  weather_mock.csv
  walking_times_mock.csv
docs/
  architecture.md
  public_data_plan.md
  scenarios.md
```

## 설치와 실행

### 1. 권장 환경

- Windows 기준 확인
- Python `3.11.x` 권장
- 가상환경 사용 권장

### 2. 가상환경 생성

```bash
python -m venv .venv
```

### 3. 가상환경 활성화

```bash
.venv\Scripts\activate
```

### 4. 의존성 설치

```bash
pip install -r requirements.txt
```

### 5. 앱 실행

```bash
streamlit run streamlit_app.py
```

실행 후 브라우저에서 아래 주소로 접속한다.

- `http://localhost:8501`

## 환경 변수 설정

루트에 `.env` 파일을 두면 앱이 자동으로 읽는다.  
실제 제출 저장소에는 `.env`를 포함하지 않고, 공개 저장소에는 `.env.example`만 둔다.

예시:

```env
CONNECTOR_MODE=auto
PUBLIC_DATA_SERVICE_KEY=여기에_서비스키
AIRPORT_CONGESTION_URL=https://apis.data.go.kr/B551177/statusOfDepartureCongestion/getDepartureCongestion
AIRPORT_PARKING_URL=http://apis.data.go.kr/B551177/StatusOfParking/getTrackingParking
AIRPORT_FLIGHTS_URL=http://apis.data.go.kr/B551177/StatusOfPassengerFlightsOdp/getPassengerDeparturesOdp
AIRPORT_AMENITIES_URL=http://apis.data.go.kr/B551177/StatusOfFacility/getFacilityKR
AIRPORT_WALKING_URL=https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_000000002316651&fileDetailSn=1&insertDataPrcus=N
AIRPORT_WEATHER_URL=https://apis.data.go.kr/B551177/StatusOfPassengerWorldWeatherInfo/getPassengerDeparturesWorldWeather
ITS_API_KEY=발급받은_ITS_키
TRAFFIC_API_URL=https://openapi.its.go.kr:9443/trafficInfo
KMA_WEATHER_URL=http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtFcst
```

주요 옵션:

- `CONNECTOR_MODE=mock`
  실데이터를 무시하고 mock CSV만 사용한다.
- `CONNECTOR_MODE=auto`
  실데이터가 준비된 항목은 real connector를 쓰고, 실패한 항목은 mock으로 fallback한다.
- `PUBLIC_DATA_SERVICE_KEY`
  공공데이터포털 서비스키. 저장소에는 올리지 않는다.
- `ITS_API_KEY`
  ITS 제공기관 키. 현재 앱은 실키를 넣으면 real traffic feed를 사용한다.
- `AIRPORT_WEATHER_URL`
  인천국제공항공사 `출발편 상대공항 기상정보` endpoint다.
- `KMA_WEATHER_URL`
  공항 기상 API 실패 시 fallback으로 사용할 수 있는 기상청 endpoint다.

## 사용 방법

앱을 실행하면 상단에 `데이터 상태 pill`이 보인다.  
이 상태가 `connected`면 실데이터, `mock only`면 mock, `pending user input`이면 설정 부족 또는 호출 실패를 뜻한다.

### 기본 사용 흐름

1. 좌측 사이드바에서 `시연 시나리오`를 선택한다.
2. 항공편, 출발 시각, 터미널, 현재 위치, 공항까지 이동시간을 조정한다.
3. 이용자 유형과 선호 옵션을 선택한다.
4. 탭별로 결과를 확인한다.

### 탭별 사용법

#### A. 오케스트레이션 대시보드

여기서 먼저 보여줄 내용:

- 권장 출발 시각
- 권장 공항 도착 시각
- 권장 보안검색 진입 시각
- 탑승 전 여유시간
- 리스크 점수
- 추천 보안검색 구역
- 추천 진입 노드
- 추천 면세/식음 활용 가능 여부

#### B. 재조정 시뮬레이터

이벤트를 선택하면 `변경 전 계획`과 `변경 후 계획`이 즉시 비교된다.

지원 이벤트:

- 보안검색 혼잡 급증
- 게이트 변경
- 공항 접근도로 정체
- 주차구역 만차
- 탑승시간 임박

#### C. 여정 단계별 화면

단계별로 아래 4가지를 보여준다.

- 현재 상황
- AI 판단
- 사용자 행동 제안
- 예상 절감 효과

#### D. AI 어시스턴트

자유 질문을 입력하면 현재 계획 상태를 반영한 답변을 반환한다.

예시 질문:

- `지금 언제 출발해야 해?`
- `어느 보안검색 구역이 제일 빨라?`
- `게이트까지 얼마나 걸려?`
- `면세점 들를 시간 있어?`
- `엘리베이터 포함 경로는?`
- `항공편 지연 시 어떻게 바뀌어?`

#### E. KPI 시뮬레이션

아래 입력을 바꾸며 `가정 기반 기대효과`를 설명할 수 있다.

- 이용자 수
- 혼잡 수준
- 예측 정확도
- 재안내 수용률
- 현장 대응 여부

## 추천 시연 흐름

가장 설득력 있는 시연 순서는 아래와 같다.

1. `출장객` 시나리오로 시작한다.
2. 대시보드에서 `권장 출발 시각`과 `보안검색 구역`을 보여준다.
3. 재조정 시뮬레이터에서 `보안검색 혼잡 급증`을 넣고 계획 변경을 보여준다.
4. `외국인 관광객` 시나리오로 바꿔 영어 UI와 면세점 추천을 보여준다.
5. `교통약자/고령자` 시나리오로 바꿔 접근성 우선 경로와 조기 출발 권고를 보여준다.
6. 마지막에 KPI 탭으로 가서 정량 기대효과를 설명한다.

상세 시연 시나리오는 [docs/scenarios.md](docs/scenarios.md)에 있다.

## 공개 데이터 활용 관점에서 중요한 점

- 이 앱은 처음부터 `공공데이터 연결 가능 구조`를 전제로 설계됐다.
- mock 데이터도 실제 공공데이터 스키마에 맞춰 설계했다.
- `registry.py`가 데이터셋별로 real/mock을 자동 전환한다.
- 일부 데이터만 준비돼도 나머지 기능은 mock으로 유지되어 데모가 멈추지 않는다.

구조 설명은 [docs/architecture.md](docs/architecture.md)를 참고하면 된다.

## 압축 제출 시 권장 포함 항목

압축 제출본에는 아래 항목을 넣는 편이 안전하다.

- `streamlit_app.py`
- `src/`
- `data/`
- `docs/`
- `requirements.txt`
- `.env.example`
- `README.md`

압축 제출본에서 제외해야 할 항목:

- `.env`
- `.venv`
- `__pycache__/`
- `data/walking_times_public_cache.csv`
- `node_modules`
- `.next`
- 기타 로컬 실행 로그

## 보안과 제출 원칙

- 실제 `PUBLIC_DATA_SERVICE_KEY`는 저장소와 제출 압축본에 넣지 않는다.
- 실제 `ITS_API_KEY`도 공개 저장소에 넣지 않는다.
- 제출본에는 `.env.example`만 포함한다.
- 실데이터 호출 여부는 코드 구조와 연결 상태 표로 설명하고, 필요 시 발표 환경의 로컬 `.env`에서 실제 키를 사용한다.

## 문제 해결

### Streamlit이 실행되지 않을 때

- 가상환경이 활성화됐는지 확인한다.
- `pip install -r requirements.txt`를 다시 실행한다.
- `streamlit run streamlit_app.py`를 `.venv` 기준으로 실행한다.

### 일부 데이터가 mock으로 표시될 때

- `.env` 파일이 루트에 있는지 확인한다.
- 서비스키와 endpoint URL이 비어 있지 않은지 확인한다.
- 데이터셋 활용신청 승인 상태를 다시 확인한다.
- 상단 상태 pill의 `detail` 문구를 본다.

### 기상 또는 교통 데이터가 불안정할 때

- 네트워크 상태를 확인한다.
- 공공데이터포털 또는 ITS 제공기관 응답 지연 가능성을 고려한다.
- `CONNECTOR_MODE=mock`으로 전환하면 최소 시연은 계속할 수 있다.

## 관련 문서

- [docs/public_data_plan.md](docs/public_data_plan.md)
- [docs/architecture.md](docs/architecture.md)
- [docs/scenarios.md](docs/scenarios.md)

## 저장소

- GitHub: [choihyunjin1/-Smart-Travel-Orchestrator-AI-MVP](https://github.com/choihyunjin1/-Smart-Travel-Orchestrator-AI-MVP)
