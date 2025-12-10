"""
High-level helpers that compose extraction + query building.
(엔티티 추출과 쿼리 생성을 연결하는 파이프라인 모듈)
"""

import logging
from typing import Dict, Optional

from qdd2.keywords import extract_entities_only
from qdd2.query_builder import generate_search_query

logger = logging.getLogger(__name__)


def build_queries_from_text(
    text: str,
    quote_sentence: Optional[str] = None,
    article_date: Optional[str] = None,
    device: int = 0,
    debug: bool = False,
) -> Dict:
    """
    [파이프라인 메인 함수]
    텍스트를 입력받아 다음 과정을 순차적으로 수행합니다:
      1) NER(개체명 인식) 수행 -> 인물, 장소 추출 (extract_entities_only)
      2) 검색 쿼리 생성 (generate_search_query)

    Args:
        text (str): 분석할 본문 텍스트
        quote_sentence (str): (선택) 찾고자 하는 핵심 인용구
        article_date (str): 기사 날짜 (YYYY-MM-DD)
        device (int): GPU 번호 (0, 1...) 또는 CPU(-1)
        debug (bool): 디버그 모드 여부

    Returns:
        Dict: {
            "entities": [...],
            "entities_by_type": {...},
            "queries": {"ko": "...", "en": "..."}
        }
    """
    extraction = extract_entities_only(
        text,
        device=device,
        debug=debug,
    )
    logger.info(
        "Extraction complete: %d entities found",
        len(extraction.get("entities", [])),
    )
    logger.debug("Entities by type: %s", extraction["entities_by_type"])

    # 2. 검색 쿼리 생성
    queries = generate_search_query(
        extraction["entities_by_type"],
        quote_sentence=quote_sentence,
        article_date=article_date,
    )

    logger.info("Query generation complete (ko/en)")
    logger.debug("KO query: %s", queries["ko"])
    logger.debug("EN query: %s", queries["en"])

    # 3. 결과 합치기 및 반환
    return {
        **extraction,
        "queries": queries,
    }
