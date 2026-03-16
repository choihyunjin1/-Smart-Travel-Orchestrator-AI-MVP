# Public Data Plan

이 문서는 이 MVP를 실제 `공공데이터 활용형 MVP`로 전환하기 위한 준비 현황판이다.

## 상태 기준

- `connected`: 실제 API 연결 완료
- `pending user input`: 서비스키, endpoint, 샘플 응답 등 사용자 준비물이 필요
- `mock only`: 현재는 mock 구조만 구현

## 보안 메모

- 저장소 공개본에는 실제 `PUBLIC_DATA_SERVICE_KEY`를 포함하지 않는다.
- GitHub에는 `.env.example`만 포함하며 실제 `.env`는 로컬 전용이다.
- 공개 저장소의 `.env.example`에는 현재 실제 사용 중인 변수만 남긴다. 기상은 공항 자체 API 대신 `KMA_WEATHER_URL`을 통해 기상청 초단기예보를 사용한다.

## 데이터셋 계획

| 데이터셋 | 활용 목적 | 예상 필드 | 인증 방식 | 사용자가 준비해야 할 항목 | 현재 연결 상태 |
|---|---|---|---|---|---|
| 인천국제공항공사_출국장 혼잡도 조회 | 가장 빠른 보안검색 구역 추천, 보안검색 진입 시점 계산 | `terminalId`, `gateId`, `waitTime`, `waitLength`, `occurtime` | 공공데이터포털 서비스키 | 서비스키와 실제 endpoint를 `.env`에 반영했고 실호출 확인 완료 | `connected` |
| 인천국제공항공사_주차 정보 | 권장 진입 주차장 추천, 만차 시 재안내 | `parkinglot`, `parking`, `parkingarea`, `datetm` | 공공데이터포털 서비스키 | 서비스키와 실제 endpoint를 `.env`에 반영했고 실호출 확인 완료 | `connected` |
| 인천국제공항공사_여객편 운항현황(다국어) 또는 여객편 주간 운항 현황 | 항공편별 출발 시각, 터미널, 게이트, 탑승 버퍼 계산 | `flight_id`, `scheduleDateTime`, `estimatedDateTime`, `terminalid`, `gatenumber`, `remark` | 공공데이터포털 서비스키 | 출발 현황 endpoint를 `.env`에 반영했고 실호출 확인 완료 | `connected` |
| 인천국제공항공사_상업 시설 정보 서비스 | 출국장 단계 추천 시설 표시 | `facltNm`, `facltType`, `floor`, `gateNo`, `terminalId` | 공공데이터포털 서비스키 | 실제 연결은 `StatusOfFacility/getFacilityKR` 기준으로 반영했고 실호출 확인 완료 | `connected` |
| 인천국제공항공사_출국장도보소요시간정보 | 게이트까지 소요시간, 경로 오케스트레이션, 걷기 최소화 로직 | `fromNode`, `toNode`, `walkingTime`, `terminalId`, `accessible` | 파일데이터 또는 공공데이터포털 다운로드 | 공식 파일 다운로드 URL을 `.env`에 반영했고 CSV 로더로 실연결 확인 완료 | `connected` |
| 인천국제공항공사_승객예고-출·입국장별 | 혼잡도 예측 레이어, 사전 출발 권고 시뮬레이션 강화 | `terminalId`, `departureAreaNo`, `forecastTime`, `numOfPassenger` | 공공데이터포털 서비스키 | 개발 활용신청 승인 완료. 혼잡 예측형 시나리오를 붙일 때 서비스키와 샘플 응답 필요 | `pending user input` |
| 인천국제공항공사_여객편 실시간 운항정보_공항기상정보 | 날씨 리스크 가중치 계산 | `weather`, `windSpeed`, `visibility`, `temperature`, `datetm` | 공공데이터포털 서비스키 | 현재는 공항 자체 기상 API 미연결. 공개 저장소 설정 예시에는 이 변수를 노출하지 않았고, MVP에서는 기상청 대체 데이터를 사용 | `pending user input` |
| 기상청_단기예보 조회서비스 | 공항기상 대체 데이터, fallback weather | `baseDate`, `baseTime`, `category`, `fcstValue`, `nx`, `ny` | 공공데이터포털 서비스키 | `getUltraSrtFcst` endpoint 반영 완료, 인천공항 격자(`55`,`124`) 기준 실호출 확인 완료 | `connected` |
| 국토교통부_교통소통정보 | 공항 접근도로 정체 판단, 권장 출발 시각 재계산 | `roadName`, `speed`, `travelTime`, `linkId`, `createdDate` | ITS 제공기관 API 키 | ITS 공식 샘플 키 `test`와 `trafficInfo` endpoint를 반영해 연결. 운영 시 발급 키로 교체 권장 | `connected` |
| 인천국제공항공사_전국공항 버스정보 | 공항 접근 방식 중 버스 대안 표시 | `routeNm`, `terminal`, `stTime`, `edTime` | 공공데이터포털 서비스키 또는 파일데이터 | 선택사항, 버스 경로 활용 시 샘플 응답 | `pending user input` |

## 현재 구현 상태

### 연결 완료

- 출국장 혼잡도 조회
- 주차 정보
- 여객편 운항현황(다국어) 출발편
- 상업/시설 정보
- 출국장도보소요시간정보 CSV
- 기상청 초단기예보
- ITS 교통소통정보

### 사용자 준비가 필요한 항목

- ITS 운영용 API 키
- 필요 시 버스정보/승객예고 추가 연결용 샘플 응답

### 현재 mock only로 유지한 항목

- KPI 시뮬레이션 수치
- 단계별 절감효과 문구
- AI 어시스턴트 응답 템플릿

## 사용자 준비 체크리스트

- [필수] 호출 제한 및 인증 방식
  - 어디서: 활용가이드
  - 형식: 일/분당 제한, JSON/XML 지원 여부
  - 이유: 캐시 전략과 fallback 로직 설계에 필요

- [필수] ITS 운영용 API 키
  - 어디서: [ITS 국가교통정보센터 오픈데이터](https://www.its.go.kr/opendata/opendataList?service=traffic)
  - 형식: `apiKey`
  - 이유: 현재는 공식 샘플 키 `test`로 연결되어 있어 제출/운영 단계에서는 발급 키로 교체하는 편이 안전함

- [선택] API 샘플 응답
  - 어디서: 포털 샘플 호출 또는 직접 받은 응답
  - 형식: `.json` 또는 `.xml`
  - 이유: parser와 field mapping 정확도 향상

- [선택] CSV/엑셀/문서
  - 어디서: 사용자가 이미 가진 자료
  - 형식: CSV, XLSX, PDF 등
  - 이유: 실시간 API가 없는 시설/좌표/보행 데이터 보강

- [선택] 지도/시설 좌표 참고자료
  - 어디서: 안내도, 시설 목록
  - 형식: CSV, 이미지, 문서
  - 이유: 걷기 최소화와 엘리베이터 경로 정밀화

## 교체 원칙

- mock 데이터는 이미 real connector의 표준 스키마를 따르도록 설계했다.
- 실데이터 준비 후에는 `src/connectors/*_openapi.py` 안의 field mapping만 보강하면 된다.
- 데이터셋 일부만 연결되어도 `registry.py`가 나머지는 자동으로 mock fallback 처리한다.

## 현재 승인 현황 반영 메모

2026-03-14 기준 사용자가 개발 활용신청 승인 완료를 확인한 항목:

- 인천국제공항공사_출국장도보소요시간정보
- 인천국제공항공사_버스정보
- 인천국제공항공사_승객예고-출·입국장별
- 인천국제공항공사_여객편 주간 운항 현황
- 인천국제공항공사_상업 시설 정보 서비스
- 인천국제공항공사_여객편 운항현황(다국어)
- 인천국제공항공사_주차 정보
- 인천국제공항공사_출국장 혼잡도 조회

## 2026-03-14 실연결 반영 메모

실제 `.env` 반영 및 connector 검증을 완료한 항목:

- `AIRPORT_CONGESTION_URL=https://apis.data.go.kr/B551177/statusOfDepartureCongestion/getDepartureCongestion`
- `AIRPORT_PARKING_URL=http://apis.data.go.kr/B551177/StatusOfParking/getTrackingParking`
- `AIRPORT_FLIGHTS_URL=http://apis.data.go.kr/B551177/StatusOfPassengerFlightsOdp/getPassengerDeparturesOdp`
- `AIRPORT_AMENITIES_URL=http://apis.data.go.kr/B551177/StatusOfFacility/getFacilityKR`
- `AIRPORT_WALKING_URL=https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_000000002316651&fileDetailSn=1&insertDataPrcus=N`
- `KMA_WEATHER_URL=http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtFcst`
- `TRAFFIC_API_URL=https://openapi.its.go.kr:9443/trafficInfo`
- `ITS_API_KEY=test`
