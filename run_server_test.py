"""
라이트 테스트 서버 - 크롬 익스텐션 테스트용
실제 NLP 모델 없이 목 데이터로 응답
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Quote Origin API (Test Mode)",
    description="크롬 익스텐션 테스트용 가벼운 API 서버"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 데이터 모델
class QuoteRequest(BaseModel):
    quote_id: str
    quote_content: str

class QuoteResponse(BaseModel):
    quote_id: str
    candidate_index: int
    original_span: str
    similarity_score: float
    source_url: str

# 테스트 데이터
TEST_DATA = {
    "한국": {
        "candidates": [
            {
                "span": "한국은 민주주의 국가입니다",
                "url": "https://n.news.naver.com/mnews/article/001/0001234567",
                "scores": [0.82, 0.45, 0.38, 0.29]
            }
        ],
        "default_score": 0.75
    },
    "기후": {
        "candidates": [
            {
                "span": "기후 변화는 점점 심해지고 있습니다",
                "url": "https://n.news.naver.com/mnews/article/002/0002345678",
                "scores": [0.88, 0.62, 0.41, 0.35]
            }
        ],
        "default_score": 0.78
    },
    "경제": {
        "candidates": [
            {
                "span": "경제 성장률이 예상보다 높았습니다",
                "url": "https://n.news.naver.com/mnews/article/003/0003456789",
                "scores": [0.85, 0.71, 0.52, 0.38]
            }
        ],
        "default_score": 0.73
    }
}

@app.get("/health")
def health_check():
    """헬스 체크"""
    return {"status": "ok", "mode": "TEST_MODE"}

@app.post("/api/find-origin", response_model=QuoteResponse)
def find_origin(request: QuoteRequest):
    """
    직접인용문 출처 찾기 (테스트 모드)
    
    Args:
        request: QuoteRequest
            - quote_id: 인용문 ID
            - quote_content: 인용문 내용
    
    Returns:
        QuoteResponse
            - quote_id: 인용문 ID
            - candidate_index: 최고 유사도 후보 인덱스 (0-based)
            - original_span: 원문 텍스트
            - similarity_score: 유사도 점수 (0.0-1.0)
            - source_url: 출처 URL
    """
    
    logger.info(f"직접인용문 요청: {request.quote_id}")
    logger.info(f"인용문 내용: {request.quote_content}")
    
    # 키워드 추출
    keyword = None
    for key in TEST_DATA.keys():
        if key in request.quote_content:
            keyword = key
            break
    
    if not keyword:
        keyword = list(TEST_DATA.keys())[0]
    
    # 테스트 데이터 반환
    data = TEST_DATA[keyword]
    candidate = data["candidates"][0]
    score = data["default_score"]
    
    response = QuoteResponse(
        quote_id=request.quote_id,
        candidate_index=0,
        original_span=candidate["span"],
        similarity_score=score,
        source_url=candidate["url"]
    )
    
    logger.info(f"응답: {response.similarity_score:.2%} 유사도")
    return response

def main():
    """서버 시작"""
    logger.info("=" * 70)
    logger.info("Quote Origin API 테스트 서버 시작 (라이트 모드)")
    logger.info("=" * 70)
    logger.info(f"Host: 0.0.0.0")
    logger.info(f"Port: 8000")
    logger.info(f"API 문서: http://localhost:8000/docs")
    logger.info(f"테스트 키워드: {', '.join(TEST_DATA.keys())}")
    logger.info("=" * 70)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        workers=1,
        log_level="info"
    )

if __name__ == "__main__":
    main()
