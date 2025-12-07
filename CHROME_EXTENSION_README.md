# Quote Origin Pipeline - 크롬 익스텐션 가이드

인용문 출처를 자동으로 탐지하는 크롬 익스텐션입니다. 네이버 뉴스(https://n.news.naver.com/mnews/article/)에 들어가면 본문의 쌍따옴표 안의 직접인용문을 자동 감지하고, 백엔드 AI가 원문을 찾아줍니다.

## 프로젝트 구조

```
quote-origin-pipeline/
├── chrome_extension/          # 크롬 익스텐션
│   ├── manifest.json          # 익스텐션 설정
│   ├── css/
│   │   ├── popup.css          # 팝업 UI 스타일
│   │   └── highlight.css      # 페이지 하이라이트 스타일
│   ├── html/
│   │   └── popup.html         # 팝업 HTML
│   └── js/
│       ├── background.js      # 백그라운드 워커
│       ├── content-script.js  # 콘텐츠 스크립트 (인용문 탐지)
│       └── popup.js           # 팝업 스크립트 (결과 표시)
│
├── qdd2/                      # 백엔드 파이썬 모듈
│   ├── backend_api.py         # FastAPI 서버
│   ├── pipeline.py            # NER + 키워드 추출
│   ├── snippet_matcher.py     # SBERT 유사도 매칭
│   ├── search_client.py       # Google CSE 검색
│   ├── translation.py         # 한글→영어 번역
│   ├── trump_utils.py         # 트럼프 컨텍스트 감지
│   └── ...
│
├── scripts/                   # 임시/테스트 파일들
├── frontend_client.py         # 파이썬 클라이언트 (배치 처리용)
├── run_server.py              # FastAPI 서버 실행 스크립트
├── requirements-api.txt       # 파이썬 의존성
└── README.md                  # 이 파일
```

## 크롬 익스텐션 동작 원리

### 1. 네이버 뉴스 페이지 접속

- `https://n.news.naver.com/mnews/article/*` URL 패턴 감지
- 콘텐츠 스크립트 (`content-script.js`) 실행

### 2. 직접인용문 탐지 (`content-script.js`)

```javascript
// 정규식으로 쌍따옴표 텍스트 찾기
const quoteRegex = /"([^"]+)"/g;
```

- 페이지 제목 + 본문에서 `"..."` 형태의 텍스트 탐지
- 각 인용문을 하이라이트 처리
- 데이터 준비: `quote_id`, `quote_content`, `article_text`, `article_date`

### 3. 백엔드 API 호출

```javascript
fetch("http://localhost:8000/api/find-origin", {
  method: "POST",
  body: {
    quote_id,
    quote_content,
    article_text,
    article_date,
  },
});
```

- 각 인용문마다 백엔드에 POST 요청 (2초 간격)

### 4. 결과 표시 (`popup.html` + `popup.js`)

- 유사도별 색상 코딩:
  - 🟢 **70%+ (높음)**: 확실한 원문 발견
  - 🔵 **50-70% (중간)**: 관련 문헌 발견
  - 🟠 **50% 이하 (낮음)**: 약한 매칭

## 설정 및 실행

### 1. 백엔드 서버 시작

```bash
# 필수 패키지 설치
pip install -r requirements-api.txt

# API 서버 실행 (포트 8000)
python run_server.py

# 또는
python -m qdd2.backend_api
```

서버가 실행 중이면:

- Swagger UI: http://localhost:8000/docs
- API Endpoint: http://localhost:8000/api/find-origin

### 2. 크롬 익스텐션 설치

#### 개발 모드 설치:

1. Chrome 주소창에 `chrome://extensions/` 입력
2. **개발자 모드** 활성화 (우상단 토글)
3. **패키지되지 않은 확장 프로그램 로드** 클릭
4. `chrome_extension` 폴더 선택

#### 이후:

1. 네이버 뉴스 기사 페이지 방문: https://n.news.naver.com/mnews/article/XXX
2. 익스텐션 아이콘 클릭 → 팝업 열기
3. 자동으로 인용문 분석 시작

## 파일별 역할

### 크롬 익스텐션

#### `manifest.json`

- 익스텐션 메타데이터
- 권한 설정 (`activeTab`, `scripting`)
- 호스트 권한 (`https://n.news.naver.com/*`)
- 콘텐츠 스크립트, 백그라운드 워커, 팝업 설정

#### `js/content-script.js` (👈 **핵심**)

```javascript
class QuoteDetector {
  detectQuotes()        // 쌍따옴표 텍스트 탐지 (정규식)
  highlightQuotes()     // 페이지에서 하이라이트 처리
  sendQuotesToBackend() // 백엔드 API 호출 (배치 처리)
  run()                 // 메인 프로세스
}
```

**주요 기능:**

- `"..."` 형태의 직접인용문만 탐지
- 10자 이상 500자 이하 필터링
- 각 인용문마다 백엔드에 개별 요청
- 완료 후 Background에 메시지 전송

#### `js/background.js`

- Content Script ↔ Popup 메시지 중계
- 최신 결과 저장 및 제공

#### `js/popup.js`

- 백엔드 결과 표시
- API 상태 체크
- 유사도별 UI 렌더링

#### `css/popup.css`

- 팝업 UI 스타일 (360px × 500px)
- 반응형 디자인
- 다크모드 지원

#### `css/highlight.css`

- 페이지 내 하이라이트 스타일
- 노란색 배경 (#fff8b5)
- 호버 효과

### 백엔드 파이썬

#### `qdd2/backend_api.py` (👈 **핵심**)

```python
@app.post("/api/find-origin")
async def find_quote_origin(request: QuoteRequest):
    # 1. 입력 검증
    # 2. 키워드 + 엔티티 추출 (pipeline.py)
    # 3. 번역 (translation.py)
    # 4. Google CSE 검색 (search_client.py)
    # 5. SBERT 유사도 매칭 (snippet_matcher.py)
    # 6. 상위 N개 후보 반환

    return QuoteResponse(
        quote_id,
        quote_content,
        candidates=[
            {
                candidate_index: 0,
                original_span: "...",
                similarity_score: 0.85,
                source_url: "..."
            },
            ...
        ],
        best_candidate: {...}
    )
```

**응답 필드:**

- `candidate_index`: 0부터 시작하는 순위
- `original_span`: 실제 원문 텍스트
- `similarity_score`: 유사도 (0~1)
- `source_url`: 출처 URL

## API 요청/응답 예시

### Request

```json
{
  "quote_id": "quote_001",
  "quote_content": "한국, 위안부 문제에 집착",
  "article_text": "트럼프가 한국이 위안부 문제에 집착한다고 말했다",
  "article_date": "2025-12-05",
  "top_matches": 5
}
```

### Response

```json
{
  "quote_id": "quote_001",
  "quote_content": "한국, 위안부 문제에 집착",
  "best_candidate": {
    "candidate_index": 0,
    "original_span": "South Korea is obsessed with comfort women issues",
    "similarity_score": 0.8234,
    "source_url": "https://example.com/article"
  },
  "candidates": [
    { "candidate_index": 0, "similarity_score": 0.8234, ... },
    { "candidate_index": 1, "similarity_score": 0.5156, ... },
    ...
  ],
  "error": null
}
```

## 주요 기술 스택

### 프론트엔드 (크롬 익스텐션)

- **JavaScript (ES6+)**: 콘텐츠 스크립트, 팝업
- **HTML5**: UI 마크업
- **CSS3**: 스타일링, 애니메이션

### 백엔드

- **FastAPI**: REST API 서버
- **Pydantic**: 데이터 검증
- **PyTorch**: SBERT 모델
- **Sentence-Transformers**: 의미론적 유사도
- **Transformers**: 한글↔영어 번역
- **Google Custom Search API**: 웹 검색

## 주요 기능

### ✅ 직접인용문 자동 탐지

- 정규식 기반 `"..."` 패턴 매칭
- 10-500자 길이 필터링
- 중복 제거

### ✅ 의미론적 유사도 계산

- SBERT 기반 임베딩
- 문장 단위 매칭
- 상위 K개 후보 반환

### ✅ 다중 검색 소스

- Google Custom Search Engine
- Rollcall 데이터베이스 (트럼프 연설)

### ✅ 실시간 번역

- MarianMT 모델 (한글→영어)
- 자동 폴백 처리

## 트러블슈팅

### 문제: 익스텐션이 작동하지 않음

**해결:**

```bash
# 1. 백엔드 서버 실행 확인
curl http://localhost:8000/api/find-origin

# 2. manifest.json 확인
# - "host_permissions": "https://n.news.naver.com/*"

# 3. 개발자 콘솔에서 오류 확인
# Chrome DevTools → Extensions → 익스텐션명
```

### 문제: 인용문이 감지되지 않음

**해결:**

- 페이지 새로고침 (F5)
- 개발 콘솔에서 `[Quote Origin]` 로그 확인
- 인용문이 `"..."` 형태인지 확인

### 문제: 백엔드 연결 실패

**해결:**

```bash
# 1. 서버 상태 확인
python run_server.py

# 2. 방화벽 설정 확인
# 포트 8000 개방

# 3. 크롬 콘솔 확인
# ERR_FAILED: Unable to connect to http://localhost:8000
```

## 성능 최적화

- **배치 처리**: 인용문당 2초 간격으로 요청 (API 부하 분산)
- **캐싱**: 동일한 인용문 결과 재사용
- **비동기 처리**: `async/await` 사용
- **제한된 후보 수**: 상위 5개만 반환

## 보안 주의사항

⚠️ **주의:**

- 현재 `http://localhost:8000` 사용 (개발 환경)
- 프로덕션 배포 시 `https://` 사용
- CORS 설정 필요
- API 인증 토큰 추가 권장

## 참고 링크

- [Chrome Extension 공식 문서](https://developer.chrome.com/docs/extensions/)
- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [Sentence-Transformers 문서](https://www.sbert.net/)
- [Google Custom Search API](https://developers.google.com/custom-search)

## 라이선스

MIT License

## 문의

프로젝트 관련 문의는 GitHub Issues를 참고하세요.
