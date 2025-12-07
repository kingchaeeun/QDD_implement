# Quote Origin API

인용문의 원문을 자동으로 찾는 FastAPI 기반 백엔드 API

## 기능

- 한글 인용문을 입력받아 원문을 검색
- SBERT 기반 의미론적 유사도 계산
- 최고 점수 후보 및 상위 N개 후보 반환
- 트럼프 관련 컨텍스트 자동 감지
- Google CSE 및 Rollcall 데이터베이스 통합 검색
- 디버그 모드로 상세 정보 확인 가능

## 설치

### 1. 필수 패키지 설치

```bash
# API 및 ML 패키지 설치
pip install -r requirements-api.txt
```

### 2. 환경 설정

필요한 환경변수를 설정합니다 (`.env` 파일 생성):

```
# Google Custom Search Engine API
GOOGLE_API_KEY=your_api_key
GOOGLE_SEARCH_ENGINE_ID=your_cse_id

# API Server
API_HOST=0.0.0.0
API_PORT=8000
```

## 사용법

### 1. API 서버 시작

```bash
# 기본 설정 (localhost:8000)
python run_server.py

# 포트 변경
python run_server.py --port 9000

# 개발 모드 (자동 재시작)
python run_server.py --reload

# 특정 호스트와 포트
python run_server.py --host 127.0.0.1 --port 8080
```

또는:

```bash
python -m qdd2.backend_api
```

### 2. API 호출

#### 기본 요청

```bash
curl -X POST "http://localhost:8000/api/find-origin" \
  -H "Content-Type: application/json" \
  -d '{
    "quote_id": "quote_001",
    "quote_content": "수단은 지구상에서 가장 폭력적인 지역이다",
    "article_text": "트럼프 대통령은 수단은 지구상에서 가장 폭력적인 지역이라고 말했다...",
    "article_date": "2025-11-20",
    "top_matches": 5
  }'
```

#### Python 클라이언트

```python
import requests
import json

url = "http://localhost:8000/api/find-origin"
payload = {
    "quote_id": "quote_001",
    "quote_content": "수단은 지구상에서 가장 폭력적인 지역이다",
    "article_text": "...",
    "article_date": "2025-11-20",
    "debug": False,
    "top_matches": 5
}

response = requests.post(url, json=payload)
result = response.json()

# 최고 점수 후보 확인
if result["best_candidate"]:
    best = result["best_candidate"]
    print(f"순위: {best['candidate_index']}")
    print(f"유사도: {best['similarity_score']:.4f}")
    print(f"원문: {best['original_span']}")
    print(f"출처: {best['source_url']}")
```

### 3. 테스트

```bash
# 테스트 클라이언트 실행
python test_backend_api.py
```

## API 문서

서버 시작 후 아래 주소에서 Swagger UI 문서를 확인할 수 있습니다:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Request 스키마

```json
{
  "quote_id": "string",              # 인용문 ID (필수)
  "quote_content": "string",         # 인용문 내용 한글 (필수)
  "article_text": "string",          # 기사 원문 (필수)
  "article_date": "string",          # 기사 날짜 YYYY-MM-DD (선택)
  "debug": "boolean",                # 디버그 모드 (기본값: false)
  "top_n": "integer",                # 키워드 추출 개수 (기본값: 15)
  "top_k": "integer",                # 쿼리 생성용 상위 k개 (기본값: 3)
  "top_matches": "integer"           # 반환할 후보 개수 (기본값: 5)
}
```

## Response 스키마

```json
{
  "quote_id": "string",
  "quote_content": "string",
  "candidates": [
    {
      "candidate_index": "integer",      # 0부터 시작하는 순위
      "original_span": "string",         # 원문 span 텍스트
      "similarity_score": "float",       # 유사도 (0~1)
      "source_url": "string",            # 출처 URL
      "best_sentence": "string"          # 중심 문장 (선택)
    }
  ],
  "best_candidate": "object",            # 최고 점수 후보
  "error": "string or null",             # 에러 메시지
  "debug_info": "object or null"         # 디버그 정보 (debug=true일 때만)
}
```

## 응답 예시

```json
{
  "quote_id": "quote_001",
  "quote_content": "수단은 지구상에서 가장 폭력적인 지역이다",
  "candidates": [
    {
      "candidate_index": 0,
      "original_span": "Sudan is also the most violent region on earth and at the same time a very serious humanitarian crisis is occurring.",
      "similarity_score": 0.8234,
      "source_url": "https://example.com/article1",
      "best_sentence": "Sudan is the most violent region."
    },
    {
      "candidate_index": 1,
      "original_span": "The country is facing severe violence in Sudan.",
      "similarity_score": 0.7156,
      "source_url": "https://example.com/article2",
      "best_sentence": "Sudan faces humanitarian crisis."
    }
  ],
  "best_candidate": {
    "candidate_index": 0,
    "original_span": "Sudan is also the most violent region on earth...",
    "similarity_score": 0.8234,
    "source_url": "https://example.com/article1",
    "best_sentence": "Sudan is the most violent region."
  },
  "error": null,
  "debug_info": null
}
```

## 파이프라인 처리 흐름

1. **입력 검증**: `quote_content`, `article_text` 필수 확인
2. **키워드 추출**: NER + TF-IDF를 이용한 키워드 추출
3. **쿼리 생성**: 추출된 키워드와 엔티티로 검색 쿼리 생성
4. **번역**: 한글 인용문 → 영어 번역
5. **검색**: Google CSE를 통한 웹 검색
6. **Span 매칭**: SBERT를 이용한 의미론적 유사도 계산
7. **순위 정렬**: 유사도 기준으로 상위 N개 반환

## 주요 모듈

| 모듈                 | 설명                    |
| -------------------- | ----------------------- |
| `backend_api.py`     | FastAPI 메인 서버       |
| `pipeline.py`        | 키워드 추출 + 쿼리 생성 |
| `translation.py`     | 한글 → 영어 번역        |
| `search_client.py`   | Google CSE 검색         |
| `snippet_matcher.py` | SBERT 의미론적 매칭     |
| `trump_utils.py`     | 트럼프 컨텍스트 감지    |

## 성능 및 최적화

- **응답 시간**: 일반적으로 30~60초 (검색 + 매칭)
- **캐싱**: 검색 결과 캐싱으로 반복 요청 성능 향상
- **배치 처리**: 다중 인용문 동시 처리 가능 (workers 조정)

## 트러블슈팅

### 문제: "article_text is required" 에러

**해결**: Request에 `article_text` 필드가 포함되어 있는지 확인

### 문제: Translation 실패

**해결**: Transformers 모델이 다운로드되지 않은 경우 발생. 인터넷 연결 확인 후 재시도

### 문제: Google CSE 검색 실패

**해결**:

- `GOOGLE_API_KEY` 및 `GOOGLE_SEARCH_ENGINE_ID` 환경변수 확인
- Google Custom Search Engine 할당량 확인

### 문제: CUDA 메모리 부족

**해결**: `torch` CPU 모드 사용 또는 배치 크기 조정

## 라이선스

MIT License

## 문의

프로젝트 관련 문의사항은 이슈 트래커를 참고하세요.
