"""
Search-query construction utilities.
"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from qdd2.name_resolution import resolve_person_name_en
from qdd2.translation import translate_ko_to_en

logger = logging.getLogger(__name__)

def _format_date_en(article_date: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    article_date를 문자열로 받아서
    - 원본 문자열 (article_date_str)
    - 영어 포맷(예: November 30, 2025) 을 튜플로 반환
    """
    if article_date is None:
        return None, None

    s = str(article_date).strip()
    if not s:
        return None, None

    dt = None
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(s, fmt)
            break
        except ValueError:
            continue

    if dt is None:
        # 못 파싱하면 그냥 원본을 그대로 쓰도록
        return s, s

    # 원하는 포맷: November 30, 2025  (쉼표 포함)
    date_en = dt.strftime("%B %d %Y")
    return s, date_en


def _normalize_token(tok: str) -> str:
    """Normalize token for deduplication: lowercase, strip punctuation/extra spaces."""
    # 정규화: 구두점/추가 공백 제거, 소문자 변환
    normalized = re.sub(r"[^\w\s]", " ", tok).lower()
    # 연속된 공백을 하나로 줄이고 앞뒤 공백 제거
    return " ".join(normalized.split()).strip()


def _dedupe_preserve(seq: List[str]) -> List[str]:
    """Remove duplicates while preserving order and ignoring empty tokens (punct/space-insensitive)."""
    seen = set()  # 이미 정규화되어 본 토큰을 저장
    out: List[str] = []
    for item in seq:
        if not item:  # 빈 문자열(토큰)은 건너뛰기
            continue
        norm = _normalize_token(item)  # 토큰 정규화
        if not norm or norm in seen:  # 정규화 후 비어있거나 이미 본 토큰이면 건너뛰기
            continue
        seen.add(norm)
        out.append(item)  # 원본 토큰을 결과 리스트에 추가 (순서 유지)
    return out


def generate_search_query(
    entities_by_type: Dict[str, List[str]],
    quote_sentence: Optional[str] = None,
    article_date: Optional[str] = None,  # YYYY-MM-DD
    use_wikidata: bool = True
) -> Dict[str, Optional[str]]:
    """
    Build Korean/English search queries using entities (Speaker, Location) only.
    (Keywords logic removed)

    Structure:
        speaker + location tokens + optional quoted sentence
    """
    # ----------------------------------------------------
    # 1. 날짜 포맷팅 및 화자(Speaker) 정보 추출
    # ----------------------------------------------------
    # 날짜 포맷팅 (원본 문자열과 영어 포맷)
    article_date_str, date_en = _format_date_en(article_date)

    per_list = entities_by_type.get("PER", [])
    if not per_list:
        return {"ko": None, "en": None}

    speaker_ko = per_list[0]  # 첫 번째 인물(PER)을 화자로 간주

    # 영어 화자 이름 결정: use_wikidata가 True면 Wikidata에서, 아니면 번역 사용
    if use_wikidata:
        speaker_en = resolve_person_name_en(speaker_ko)
    else:
        try:
            speaker_en = translate_ko_to_en(speaker_ko)
        except Exception:
            speaker_en = speaker_ko

    # ----------------------------------------------------
    # 2. LOC (장소) 정보 추출 및 번역 (최대 2개)
    # ----------------------------------------------------
    # LOC는 일반 모드에서만 사용할 거라 그대로 둠
    loc_list = entities_by_type.get("LOC", [])[:2] # 최대 2개 LOC
    loc_list = _dedupe_preserve(loc_list) # 중복 제거 (순서 보존)
    locs_ko = " ".join(loc_list) # 한국어 LOC는 공백으로 연결

    locs_en_tokens: List[str] = []
    for loc in loc_list:
        try:
            loc_en_full = translate_ko_to_en(loc)
            # 번역된 결과에서 쉼표 앞 부분만 사용 (예: '서울, 한국' -> '서울')
            loc_en_first = loc_en_full.split(",")[0]
            # 앞의 2단어까지만 사용 (쿼리 길이 제한)
            loc_en_first = " ".join(loc_en_first.split()[:2])
            if loc_en_first:
                locs_en_tokens.append(loc_en_first)
        except Exception:
            logger.warning("Location translation failed, falling back to original: %s", loc)
            locs_en_tokens.append(loc)


    # ----------------------------------------------------
    # 3. 인용구(Quote) 번역
    # ----------------------------------------------------
    quote_en_full: Optional[str] = None
    if quote_sentence:
        try:
            quote_en_full = translate_ko_to_en(quote_sentence)
        except Exception:
            quote_en_full = None

    # ----------------------------------------------------
    # 4. 영어(EN) 검색 쿼리 구성
    # ----------------------------------------------------
    # 구성: 화자 + 장소 + 인용구 (키워드 제외)
    query_en_tokens: List[str] = _dedupe_preserve(
        [speaker_en] + locs_en_tokens
    )
    if quote_en_full:
        query_en_tokens.append(quote_en_full) # 인용구는 끝에 추가
    query_en = " ".join(query_en_tokens).strip()

    # ----------------------------------------------------
    # 5. 한국어(KO) 검색 쿼리 구성
    # ----------------------------------------------------
    query_ko_parts = [speaker_ko] # 화자
    if locs_ko:
        query_ko_parts.append(locs_ko) # 장소 토큰

    if quote_sentence:
        query_ko_parts.append(quote_sentence) # 인용구

    # 모든 한국어 파트를 합친 후, 공백으로 나누고 다시 중복을 제거하여 최종 쿼리 생성
    query_ko = " ".join(
        _dedupe_preserve(" ".join(query_ko_parts).split())
    ).strip()

    return {"ko": query_ko or None, "en": query_en or None}