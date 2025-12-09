"""
FastAPI 백엔드: quote_id + quote_content → candidate_index, original_span, similarity_score
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import logging
import os
import sys

from qdd2.pipeline import build_queries_from_text
from qdd2.translation import translate_ko_to_en
from qdd2.snippet_matcher import find_best_span_from_candidates_debug
from qdd2.search_client import google_cse_search
from qdd2.trump_utils import contains_trump_entity, is_trump_like_text
from qdd2.models import (
    get_ner_pipeline,
    get_keyword_model,
    get_translation_models,
    get_sentence_model,
)
from qdd2.quote_mining import get_quote_mining_model, score_quote_pair

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# ==================== Request/Response 모델 ====================

class QuoteRequest(BaseModel):
    """사용자 요청 스키마"""
    quote_id: str
    quote_content: str
    article_text: Optional[str] = None  # 기사 원문 (선택)
    article_date: Optional[str] = None  # YYYY-MM-DD
    debug: bool = False
    top_n: int = 15  # 키워드 추출 개수
    top_k: int = 3   # 쿼리 생성용 상위 k개
    top_matches: int = 5  # 반환할 후보 개수


class CandidateResult(BaseModel):
    """개별 후보 결과"""
    candidate_index: int  # 0부터 시작하는 순위
    original_span: str  # 원문의 span 텍스트
    similarity_score: float  # 유사도 점수 (0~1)
    source_url: str  # 출처 URL
    best_sentence: Optional[str] = None  # 중심 문장
    distortion_score: Optional[float] = None  # 왜곡 확률 (1 클래스 확률)
    is_distorted: Optional[bool] = None      # 왜곡 여부 (thresholded)


class QuoteResponse(BaseModel):
    """최종 응답 스키마"""
    quote_id: str
    quote_content: str
    candidates: List[CandidateResult]
    best_candidate: Optional[CandidateResult] = None  # 최고 점수 후보
    error: Optional[str] = None
    debug_info: Optional[dict] = None  # 디버그 정보


# ==================== FastAPI 앱 ====================

app = FastAPI(
    title="Quote Origin API",
    version="1.0.0",
    description="인용문의 원문을 찾는 API"
)


@app.on_event("startup")
async def preload_models() -> None:
    """
    서버 기동 시 한 번만 주요 모델을 미리 로드해서
    첫 요청 지연(koelectra/KeyBERT/번역/SBERT 로딩)을 줄인다.
    """
    logger.info("[Startup] Preloading NER / keyword / translation / sentence / quote-mining models...")
    # Lazy-load caches; 실제로는 @lru_cache 때문에 한 번만 로드됨
    get_ner_pipeline()
    get_keyword_model()
    get_translation_models()
    get_sentence_model()
    # Quote-mining classifier (RoBERTa-base fine-tuned)
    try:
        get_quote_mining_model()
        logger.info("[Startup] Quote-mining model loaded.")
    except Exception as e:
        # 모델이 없어도 API는 동작하게 두고, 추론 시에만 경고를 띄운다.
        logger.warning(f"[Startup] Quote-mining model preload failed: {e}")
    logger.info("[Startup] Model preload complete.")


@app.post("/api/find-origin", response_model=QuoteResponse)
async def find_quote_origin(request: QuoteRequest) -> QuoteResponse:
    """
    인용문의 원문을 찾는 API 엔드포인트.
    
    Request:
        - quote_id: 인용문 ID (예: "quote_001")
        - quote_content: 인용문 내용 (한글)
        - article_text: 기사 원문 (선택사항)
        - article_date: 기사 날짜 (선택사항)
        - top_matches: 반환할 후보 개수
    
    Response:
        - quote_id, quote_content
        - candidates: [candidate_index, original_span, similarity_score, ...]
        - best_candidate: 최고 점수 후보
    """
    debug_info = {} if request.debug else None
    
    try:
        # ==================== Step 1: 입력 검증 ====================
        if not request.article_text:
            return QuoteResponse(
                quote_id=request.quote_id,
                quote_content=request.quote_content,
                candidates=[],
                error="article_text is required",
                debug_info=debug_info
            )
        
        if not request.quote_content or len(request.quote_content.strip()) == 0:
            return QuoteResponse(
                quote_id=request.quote_id,
                quote_content=request.quote_content,
                candidates=[],
                error="quote_content is empty",
                debug_info=debug_info
            )

        logger.info(f"[API] Processing quote_id={request.quote_id}, content={request.quote_content[:50]}")

        # ==================== Step 2: 파이프라인 실행 ====================
        # build_queries_from_text로 쿼리 생성
        try:
            result = build_queries_from_text(
                text=request.article_text,
                top_n_keywords=request.top_n,
                top_k_for_query=request.top_k,
                quote_sentence=request.quote_content,
                article_date=request.article_date,
                rollcall_mode=False,
                device=0,
                debug=request.debug,
            )
            if request.debug:
                debug_info['pipeline_result'] = {
                    'entities': list(result.get('entities_by_type', {}).keys()),
                    'keywords_count': len(result.get('keywords', []))
                }
        except Exception as e:
            logger.error(f"[API] Pipeline error: {e}", exc_info=True)
            return QuoteResponse(
                quote_id=request.quote_id,
                quote_content=request.quote_content,
                candidates=[],
                error=f"Pipeline failed: {str(e)}",
                debug_info=debug_info
            )

        # ==================== Step 3: 트럼프 컨텍스트 감지 ====================
        is_trump_context = (
            contains_trump_entity(result) or 
            is_trump_like_text(request.article_text) or
            is_trump_like_text(request.quote_content)
        )
        logger.info(f"[API] Trump context: {is_trump_context}")
        if request.debug:
            debug_info['trump_context'] = is_trump_context

        # ==================== Step 4: 인용문을 영어로 번역 ====================
        try:
            quote_en = translate_ko_to_en(request.quote_content)
        except Exception as e:
            logger.warning(f"[API] Translation failed: {e}, using Korean")
            quote_en = request.quote_content

        logger.info(f"[API] Quote EN: {quote_en}")
        if request.debug:
            debug_info['quote_en'] = quote_en

        # ==================== Step 5: 검색 쿼리 생성 ====================
        queries = result.get("queries") or {}
        query = queries.get("en") or queries.get("ko")

        if not query:
            logger.warning("[API] No query generated")
            return QuoteResponse(
                quote_id=request.quote_id,
                quote_content=request.quote_content,
                candidates=[],
                error="Could not generate search query",
                debug_info=debug_info
            )

        logger.info(f"[API] Generated query: {query}")
        if request.debug:
            debug_info['query'] = query

        # ==================== Step 6: Google CSE 검색 ====================
        try:
            logger.info("[API] Starting Google CSE search")
            data = google_cse_search(query, num=10, debug=request.debug)
            search_items = data.get("items", []) or []
        except Exception as e:
            logger.error(f"[API] Google CSE search failed: {e}", exc_info=True)
            return QuoteResponse(
                quote_id=request.quote_id,
                quote_content=request.quote_content,
                candidates=[],
                error=f"Search failed: {str(e)}",
                debug_info=debug_info
            )

        if not search_items:
            logger.warning("[API] No search results")
            return QuoteResponse(
                quote_id=request.quote_id,
                quote_content=request.quote_content,
                candidates=[],
                error="No search results found",
                debug_info=debug_info
            )

        logger.info(f"[API] Found {len(search_items)} search results")
        if request.debug:
            debug_info['search_items_count'] = len(search_items)

        # ==================== Step 7: Candidate 준비 ====================
        candidates_for_matching = []

        for item in search_items:
            url = item.get("link") or item.get("formattedUrl")
            snippet = item.get("snippet", "") or ""
            
            if url and snippet and len(snippet.strip()) > 0:
                candidates_for_matching.append({
                    "url": url,
                    "snippet": snippet,
                })

        if not candidates_for_matching:
            logger.warning("[API] No valid candidates for matching")
            return QuoteResponse(
                quote_id=request.quote_id,
                quote_content=request.quote_content,
                candidates=[],
                error="No valid candidates for span matching",
                debug_info=debug_info
            )

        logger.info(f"[API] Matching against {len(candidates_for_matching)} candidates")
        if request.debug:
            debug_info['candidates_for_matching'] = len(candidates_for_matching)

        # ==================== Step 8: SBERT Span 매칭 ====================
        try:
            best_span = find_best_span_from_candidates_debug(
                quote_en=quote_en,
                candidates=candidates_for_matching,
                num_before=1,
                num_after=1,
                min_score=0.0,  # 모든 후보 수집
            )
        except Exception as e:
            logger.error(f"[API] Span matching failed: {e}", exc_info=True)
            return QuoteResponse(
                quote_id=request.quote_id,
                quote_content=request.quote_content,
                candidates=[],
                error=f"Span matching failed: {str(e)}",
                debug_info=debug_info
            )

        if not best_span:
            logger.warning("[API] No spans found")
            return QuoteResponse(
                quote_id=request.quote_id,
                quote_content=request.quote_content,
                candidates=[],
                error="No matching spans found",
                debug_info=debug_info
            )

        # ==================== Step 9: 결과 변환 ====================
        top_k_candidates = best_span.get("top_k_candidates", [])

        candidate_results = []
        for idx, cand in enumerate(top_k_candidates[:request.top_matches]):
            span_text = cand.get("span_text", "") or cand.get("best_sentence", "")

            # ==================== 왜곡 점수 계산 (QuoteMiningDetection) ====================
            distortion_score = None
            is_distorted = None
            if span_text:
                try:
                    distortion = score_quote_pair(
                        quote_text=quote_en,
                        origin_span_text=span_text,
                    )
                    # 백엔드에서는 모델이 반환한 확률을 그대로 사용하고,
                    # UI에서 원하는 자리수로 포맷팅한다.
                    distortion_score = float(distortion["prob_distorted"])
                    is_distorted = distortion["is_distorted"]
                    logger.info(
                        "[API] Distortion score url=%s prob_distorted=%.8f is_distorted=%s",
                        cand.get("url", ""),
                        distortion_score,
                        is_distorted,
                    )
                except Exception as e:
                    logger.warning(
                        "[API] Distortion scoring failed for url=%s: %s",
                        cand.get("url", ""),
                        e,
                    )

            result_item = CandidateResult(
                candidate_index=idx,  # 0부터 시작
                original_span=span_text,
                similarity_score=round(cand.get("best_score", 0.0), 4),
                source_url=cand.get("url", ""),
                best_sentence=cand.get("best_sentence", None),
                distortion_score=distortion_score,
                is_distorted=is_distorted,
            )
            candidate_results.append(result_item)

        best_candidate = candidate_results[0] if candidate_results else None

        logger.info(
            f"[API] Success: found {len(candidate_results)} candidates, "
            f"best_score={best_candidate.similarity_score if best_candidate else 'N/A'}"
        )
        if request.debug:
            debug_info['total_candidates_found'] = len(candidate_results)

        return QuoteResponse(
            quote_id=request.quote_id,
            quote_content=request.quote_content,
            candidates=candidate_results,
            best_candidate=best_candidate,
            error=None,
            debug_info=debug_info,
        )

    except Exception as e:
        logger.error(f"[API] Unexpected error: {e}", exc_info=True)
        return QuoteResponse(
            quote_id=request.quote_id,
            quote_content=request.quote_content,
            candidates=[],
            error=f"Unexpected error: {str(e)}",
            debug_info=debug_info,
        )





# ==================== 실행 ====================

if __name__ == "__main__":
    import uvicorn
    
    # 포트 설정 (환경변수 또는 기본값)
    port = int(os.getenv("API_PORT", 8000))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    logger.info(f"Starting Quote Origin API on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
