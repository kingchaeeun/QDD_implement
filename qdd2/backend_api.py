"""
FastAPI Backend Server
(인용문 원문 추적 API 서버)

이 파일은 우리가 지금까지 만든 모든 도구(NER, 번역, 검색, 매칭, 왜곡 탐지)를
하나로 조립하여, 외부에서 접속 가능한 '웹 서비스'로 만들어주는 곳입니다.

[작동 흐름]
1. 사용자가 요청(Request)을 보냅니다.
2. 이 서버가 요청을 받아서:
   - 기사에서 인물/장소를 찾고 (Pipeline)
   - 인용문을 영어로 번역하고 (Translation)
   - 구글에 검색해서 (Search)
   - 가장 비슷한 원문을 찾은 뒤 (Matching)
   - 왜곡되었는지 판단합니다 (Distortion Detection).
3. 최종 결과를 사용자에게 응답(Response)으로 돌려줍니다.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import logging
import os
import sys

# QDD2 파이프라인 모듈들 임포트
from qdd2.pipeline import build_queries_from_text
from qdd2.translation import translate_ko_to_en
from qdd2.snippet_matcher import find_best_span_from_candidates_debug
from qdd2.search_client import google_cse_search

# 모델 로더 임포트
from qdd2.models import (
    get_ner_pipeline,
    get_translation_models,
    get_sentence_model,
)
from qdd2.quote_mining import get_quote_mining_model, score_quote_pair

# =========================================================
# [로깅 설정]
# =========================================================
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# =========================================================
# [데이터 모델 정의 (Schema)]
# 클라이언트와 주고받을 데이터의 '형식'을 미리 약속합니다.
# =========================================================

class QuoteRequest(BaseModel):
    """
    [요청 데이터]
    사용자가 보낼 데이터의 모양입니다.
    """
    quote_id: str               # 인용문 고유 ID (예: "q1001")
    quote_content: str          # 인용문 내용 (예: "트럼프가 베네수엘라 봉쇄를 언급함")
    article_text: Optional[str] = None  # 기사 원문 (문맥 파악용)
    article_date: Optional[str] = None  # 기사 날짜 (검색 시점 보정용)
    debug: bool = False         # 디버그 모드 여부
    top_matches: int = 5        # 최종적으로 반환할 원문 후보 개수


class CandidateResult(BaseModel):
    """
    [결과 아이템]
    찾아낸 원문 후보 하나하나의 정보입니다.
    """
    candidate_index: int        # 순위 (0등, 1등, ...)
    original_span: str          # 찾은 원문 텍스트 (영어)
    similarity_score: float     # SBERT 유사도 점수 (0~1)
    source_url: str             # 출처 URL
    best_sentence: Optional[str] = None  # 중심 문장
    distortion_score: Optional[float] = None  # 왜곡 확률 (0~1)
    is_distorted: Optional[bool] = None       # 왜곡 판정 결과 (True/False)


class QuoteResponse(BaseModel):
    """
    [최종 응답]
    서버가 사용자에게 돌려줄 최종 결과물입니다.
    """
    quote_id: str
    quote_content: str
    candidates: List[CandidateResult]         # 후보 리스트
    best_candidate: Optional[CandidateResult] = None  # 1등 후보 (편의용)
    error: Optional[str] = None               # 에러 메시지 (성공 시 None)
    debug_info: Optional[dict] = None         # 디버그 정보 (요청 시에만 포함)


# =========================================================
# [FastAPI 앱 생성]
# =========================================================

app = FastAPI(
    title="Quote Origin API",
    version="1.0.0",
    description="인용문의 원문을 찾아주는 AI 백엔드 서버"
)


@app.on_event("startup")
async def preload_models() -> None:
    """
    [서버 시작 시 실행]
    사용자가 요청하기 전에 무거운 AI 모델들을 미리 메모리에 올려둡니다.
    이렇게 하면 첫 번째 요청이 들어왔을 때 기다리는 시간을 확 줄일 수 있습니다.
    """
    logger.info("[Startup] Preloading models...")

    # 1. 기본 모델 로드 (NER, 번역, SBERT)
    get_ner_pipeline()
    get_translation_models()
    get_sentence_model()

    # 2. 왜곡 탐지 모델 로드
    try:
        get_quote_mining_model()
        logger.info("[Startup] Quote-mining model loaded.")
    except Exception as e:
        # 파일이 없거나 오류가 나도 서버는 켜지게 함 (해당 기능만 실패 처리
        logger.warning(f"[Startup] Quote-mining model preload failed: {e}")

    logger.info("[Startup] Model preload complete.")


@app.post("/api/find-origin", response_model=QuoteResponse)
async def find_quote_origin(request: QuoteRequest) -> QuoteResponse:
    """
    [메인 기능] 인용문 원문 찾기
    사용자가 POST 요청을 보내면 이 함수가 실행됩니다.
    """
    debug_info = {} if request.debug else None
    
    try:
        # -----------------------------------------------------
        # [Step 1] 입력값 검증 (Validation)
        # -----------------------------------------------------
        if not request.article_text:
            return QuoteResponse(
                quote_id=request.quote_id,
                quote_content=request.quote_content,
                candidates=[],
                error="article_text is required",   # 기사 본문 필수
                debug_info=debug_info
            )
        
        if not request.quote_content or len(request.quote_content.strip()) == 0:
            return QuoteResponse(
                quote_id=request.quote_id,
                quote_content=request.quote_content,
                candidates=[],
                error="quote_content is empty", # 인용문 내용 필수
                debug_info=debug_info
            )

        logger.info(f"[API] Processing quote_id={request.quote_id}, content={request.quote_content[:50]}")

        # -----------------------------------------------------
        # [Step 2] 파이프라인 실행 (엔티티 추출)
        # -----------------------------------------------------
        try:
            result = build_queries_from_text(
                text=request.article_text,
                quote_sentence=request.quote_content,
                article_date=request.article_date,
                device=0,   # 0번 GPU 사용 (없으면 알아서 CPU 씀)
                debug=request.debug,
            )

            # 디버그 정보 기록
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

        # -----------------------------------------------------
        # [Step 3] 인용문 번역 (한글 -> 영어)
        # -----------------------------------------------------
        # 구글 검색과 영어 원문 비교를 위해 번역이 필수적입니다.
        try:
            quote_en = translate_ko_to_en(request.quote_content)
        except Exception as e:
            logger.warning(f"[API] Translation failed: {e}, using Korean")
            quote_en = request.quote_content

        logger.info(f"[API] Quote EN: {quote_en}")
        if request.debug:
            debug_info['quote_en'] = quote_en

        # -----------------------------------------------------
        # [Step 4] 검색 쿼리 결정 및 실행 (Google Search)
        # -----------------------------------------------------
        queries = result.get("queries") or {}
        # 영문 쿼리를 우선으로 쓰고, 없으면 한글 쿼리 사용
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

        try:
            logger.info("[API] Starting Google CSE search")
            # 구글 검색 (최대 10개)
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

        # -----------------------------------------------------
        # [Step 5] SBERT 매칭 (원문 찾기)
        # -----------------------------------------------------
        # 검색된 결과들(Candidates) 중에서 SBERT를 이용해 진짜 원문을 찾습니다.

        # 1. 검색 결과를 매칭 가능한 형태로 변환
        candidates_for_matching = []

        for item in search_items:
            url = item.get("link") or item.get("formattedUrl")
            snippet = item.get("snippet", "") or ""
            
            if url and snippet and len(snippet.strip()) > 0:
                candidates_for_matching.append({
                    "url": url,
                    "snippet": snippet,
                })


        # 2. 매칭 함수 실행
        try:
            best_span = find_best_span_from_candidates_debug(
                quote_en=quote_en,
                candidates=candidates_for_matching,
                num_before=1,
                num_after=1,
                min_score=0.0,  # 점수가 낮아도 일단 모든 후보를 가져옵니다.
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

        # -----------------------------------------------------
        # [Step 6] 왜곡 탐지 (Distortion Scoring) 및 결과 정리
        # -----------------------------------------------------
        top_k_candidates = best_span.get("top_k_candidates", [])
        candidate_results = []

        # 상위 N개 후보에 대해 각각 왜곡 여부를 검사합니다.
        for idx, cand in enumerate(top_k_candidates[:request.top_matches]):
            span_text = cand.get("span_text", "") or cand.get("best_sentence", "")

            distortion_score = None
            is_distorted = None

            # 찾은 원문이 있다면 왜곡 모델을 돌려봅니다.
            if span_text:
                try:
                    distortion = score_quote_pair(
                        quote_text=quote_en,  # 번역된 인용문
                        origin_span_text=span_text,  # 찾은 영어 원문
                    )

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

            # 최종 결과 리스트에 추가
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

        # ==================== Step 10: 인용문 단위 왜곡 라벨 산출 ====================
        max_distortion_prob = None
        for cand in candidate_results:
            if cand.distortion_score is None:
                continue
            if max_distortion_prob is None or cand.distortion_score > max_distortion_prob:
                max_distortion_prob = cand.distortion_score

        max_distortion_score = None
        label = None
        if max_distortion_prob is not None:
            # 모델 확률(0~1)을 0~100 점수로 변환
            max_distortion_score = round(max_distortion_prob * 100.0, 2)
            # 제일 높은 왜곡 점수가 50점 이상이면 distorted, 아니면 normal
            label = "distorted" if max_distortion_score >= 50.0 else "normal"

        logger.info(
            f"[API] Success: found {len(candidate_results)} candidates, "
            f"best_score={best_candidate.similarity_score if best_candidate else 'N/A'}"
        )
        if request.debug:
            debug_info['total_candidates_found'] = len(candidate_results)

        # 사용자에게 최종 응답 반환
        return QuoteResponse(
            quote_id=request.quote_id,
            quote_content=request.quote_content,
            candidates=candidate_results,
            best_candidate=best_candidate,
            max_distortion_score=max_distortion_score,
            label=label,
            error=None,
            debug_info=debug_info,
        )

    except Exception as e:
        # 예상치 못한 에러가 발생했을 때 서버가 죽지 않고 에러 메시지를 반환하도록 함
        logger.error(f"[API] Unexpected error: {e}", exc_info=True)
        return QuoteResponse(
            quote_id=request.quote_id,
            quote_content=request.quote_content,
            candidates=[],
            error=f"Unexpected error: {str(e)}",
            debug_info=debug_info,
        )





# =========================================================
# [서버 실행부]
# 이 파일을 직접 실행(python app.py)했을 때만 작동합니다.
# =========================================================

if __name__ == "__main__":
    import uvicorn
    
    # 환경변수에서 포트를 가져오거나, 없으면 8000번 사용
    port = int(os.getenv("API_PORT", 8000))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    logger.info(f"Starting Quote Origin API on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
