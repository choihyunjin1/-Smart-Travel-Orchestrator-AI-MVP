# Submission Record

## 개요

이 문서는 `AI 여행 오케스트레이션 동반자 (Smart Travel Orchestrator AI)` MVP의 제출 및 보관 이력을 남기기 위한 기록 문서다.

## 제출 일자

- `2026-03-16`

## 제출 목적

- 인천공항 AI-PORT 관련 공모 제출
- 신청서와 제안서를 별도 서식화하여 메일 첨부 방식으로 제출

## 제출 구성

- 신청서
- 제안서
- 시연자료 압축본

## 시연자료 구성 기준

압축용 시연자료는 아래 파일만 포함하도록 정리했다.

- `README.md`
- `requirements.txt`
- `.env.example`
- `streamlit_app.py`
- `src/`
- `data/`
- `docs/`

제외 항목:

- 실제 `.env`
- `.venv`
- `__pycache__`
- `walking_times_public_cache.csv`
- `node_modules`
- `.next`
- 기타 로컬 로그

## GitHub 보관

- 저장소: [choihyunjin1/-Smart-Travel-Orchestrator-AI-MVP](https://github.com/choihyunjin1/-Smart-Travel-Orchestrator-AI-MVP)
- 브랜치: `main`

## 보관 목적

- 제출 이후 결과물을 재현 가능한 상태로 유지
- 실데이터 연동 구조와 문서를 장기 보관
- 향후 수정 또는 추가 실증 시 기준 버전으로 활용

## 현재 기준 핵심 상태

- 출국장 혼잡도, 주차, 항공편, 시설, 교통, 기상 데이터 실연결 확인
- 공공데이터 + mock fallback 구조 유지
- 제출용 시연자료 폴더 별도 정리 완료
