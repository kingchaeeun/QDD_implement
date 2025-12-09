# Quote Origin Pipeline

네이버 뉴스 기사에서 **직접 인용문을 자동으로 감지**하고,  
FastAPI 백엔드로 **원문 후보(출처 URL + 문장)** 를 찾아준 뒤,  
인용 왜곡 탐지 모델(QuoteMiningDetection 기반 RoBERTa 분류기)로 **왜곡 확률 점수**까지 계산하는 프로젝트입니다.

- 프론트엔드: 크롬 익스텐션 (React + Vite + TypeScript)
- 백엔드: FastAPI 기반 `qdd2` 패키지

---

## 1. 백엔드 서버 실행

### 1-1. 의존성 설치

```bash
cd quote-origin-pipeline
pip install -r requirements-api.txt
```

### 1-2. 서버 실행

```bash
python run_server.py --port 8000
```

- 앱: `qdd2.backend_api.app`
- 문서: `http://localhost:8000/docs`

서버 시작 시 `@app.on_event("startup")` 에서 koelectra NER, KeyBERT, 번역 모델, SBERT 등을 **한 번만 미리 로드**합니다.

---

## 2. 크롬 익스텐션 빌드 및 설치

### 2-1. 의존성 설치

```bash
cd quote-origin-pipeline/chrome_extension
npm install
```

### 2-2. 빌드

```bash
npm run build
```

- 출력: `chrome_extension/dist/`
- 엔트리: `vite.config.ts` 참조

### 2-3. 크롬에 로드

1. `chrome://extensions` 접속
2. 우측 상단 **개발자 모드** ON
3. **압축 해제된 확장 프로그램 로드** → `quote-origin-pipeline/chrome_extension` 선택
4. 코드 수정 후에는 `npm run build` → 확장 프로그램 **새로고침(↻)**

---

## 3. 전체 동작 흐름

1. 사용자가 네이버 기사 페이지 방문  
   (`https://n.news.naver.com/mnews/article/*`)
2. `content-script.ts` 가 기사/헤드라인에서 **따옴표 인용문**을 감지
   - `"..."`, `“…”`, `‘…’`, `「…」`, `『…』`, `《…》` 지원
   - 길이 필터: 10~500자
3. 각 인용문을 `<mark class="quote-highlight" data-quote-id="...">인용문</mark> 번호` 형태로 하이라이트
   - 번호는 **검출 순서 기준으로 1, 2, 3...**
4. 사용자가 인용문을 클릭하면:
   - 컨텐트 스크립트가 페이지 오른쪽에 iframe 사이드패널을 생성 (`html/side-panel.html`)
   - 선택된 인용문 전체 텍스트 + 기사 본문을 백엔드로 전송 (`find_origin` 메시지)
5. `background.ts` 가 메시지를 받아 FastAPI `/api/find-origin` 호출
   - 응답을  
     `{ quote_id, quote, original_span, similarity_score(0~1), distortion_score(0~1), is_distorted, source_url }[]`  
     형태로 매핑해 사이드패널에 전달
6. `SidePanel.tsx` 가 로딩/결과 카드를 렌더링
   - 각 카드에 원문 span, **유사도(%), 인용 왜곡 확률(%), 출처 URL** 표시

---

## 4. 주요 파일 구조

### 4-1. 크롬 익스텐션 (`chrome_extension/`)

- `manifest.json`  
  - MV3 매니페스트.  
  - `content_scripts`(네이버 기사), `background.service_worker`, `side_panel` 경로 정의.

- `vite.config.ts`  
  - Vite 빌드 설정.  
  - 엔트리: `background.ts`, `content-script.ts`, `src/side-panel.html`, `src/popup.html` 등.

- `package.json`  
  - React/Vite/Tailwind/TypeScript 의존성과 `dev`, `build`, `preview` 스크립트.

- `src/content-script.ts`  
  - 네이버 기사 페이지에 주입되는 컨텐트 스크립트.
  - 인용문 감지, DOM 하이라이트, 번호 부여, 클릭 시 백엔드 호출 및 사이드패널 열기.

- `src/background.ts`  
  - 서비스 워커.  
  - `find_origin` 메시지를 받아 `/api/find-origin` 호출 후 결과를 캐시하고 사이드패널에 전달.

- `src/side-panel.tsx` / `html/side-panel.html`  
  - 페이지 내 인라인 사이드패널 iframe의 진입점 + HTML 쉘.

- `src/components/SidePanel.tsx` (+ `QuoteCard.tsx`, `ResultsContainer.tsx`)  
  - 오른쪽 패널 UI, 로딩 상태, 결과 리스트 렌더링.

- `src/popup.tsx` / `src/popup.html`  
  - 브라우저 툴바 아이콘 클릭 시 팝업 UI.

- `src/styles/globals.css`, `tailwind.config.js`, `postcss.config.js`, `tsconfig.json`  
  - 스타일 및 빌드/TS 설정.

### 4-2. 백엔드 (`qdd2/`)

- `backend_api.py`  
  - FastAPI 앱 및 `POST /api/find-origin` 엔드포인트.  
  - 인용문 + 기사 텍스트를 받아 파이프라인을 실행하고 후보(`candidates`)를 반환.
  - `@app.on_event("startup")` 에서 모델 사전 로딩.

- `pipeline.py`  
  - `build_queries_from_text(text, ...)` 편의 함수.  
  - 엔티티/키워드 추출 + ko/en 검색 쿼리 생성.

- `keywords.py`, `entities.py`  
  - koelectra NER 실행, KeyBERT 키워드 추출 및 NER-aware 리랭킹.

- `models.py`  
  - NER, KeyBERT, 번역 모델, SBERT를 **lru_cache**로 lazy-load.

- `search_client.py`  
  - Google CSE 검색, HTML/PDF 다운로드 및 스니펫 추출.

- `snippet_matcher.py`  
  - SBERT 기반 span 매칭, `candidates` 리스트 생성.

- `translation.py`  
  - 한국어 인용문을 영어로 번역 (`translate_ko_to_en`).

- `config.py`  
  - 모델 이름, 디바이스, 검색 도메인, 타임아웃 등 공통 설정.

그 외 `name_lexicon.py`, `name_resolution.py`, `rollcall_search.py`, `text_utils.py`, `trump_utils.py` 등은  
파이프라인 세부 로직(이름 해석, 텍스트 전처리, 트럼프 특화 처리 등)을 담당합니다.

---

## 5. 스크립트 / 기타

- `scripts/main.py` 및 `scripts/*.py`  
  - 파이프라인 단독 테스트, 데이터셋 구축, 빠른 실험용 유틸 스크립트.

- `API_README.md`, `CHROME_EXTENSION_README.md`  
  - API 세부 사용법 및 확장 구조에 대한 추가 설명.
