"""
Snippet-level semantic matching helpers using SentenceTransformer.
(SBERT를 이용한 문맥 단위 의미 유사도 매칭 도구)

이 모듈은 단순히 '단어'가 겹치는 것을 찾는 게 아니라,
AI(SBERT)를 사용하여 '의미'가 가장 유사한 문장 덩어리(Span)를 찾아냅니다.
"""

import re
from typing import Dict, List, Optional

import torch
from sentence_transformers import util

from qdd2.models import get_sentence_model
from qdd2.text_utils import contains_korean, clean_text


def split_into_sentences(text: str, is_ko: Optional[bool] = None) -> List[str]:
    """
        [문장 분리기]
        긴 텍스트를 문장 단위로 쪼갭니다.
        단순히 마침표(.)로 자르는 것뿐만 아니라, 너무 짧은 문장은 노이즈로 보고 버립니다.

        Args:
            text: 분리할 전체 텍스트
            is_ko: 한국어 여부 (None이면 자동 감지)
        """
    if is_ko is None:
        is_ko = contains_korean(text)

    # 1. 정규표현식으로 문장 분리
    # (?<=[.!?]) : 마침표, 느낌표, 물음표 뒤에서 자르되, 기호는 앞 문장에 포함시킴
    rough = re.split(r"(?<=[.!?])\s+", text or "")

    sentences = []
    for s in rough:
        s = clean_text(s)   # 특수문자 제거 등 기본 정제
        if not s:
            continue

        # 2. 길이 필터링 (너무 짧은 문장은 무시)
        # 한국어는 10자 미만, 영어는 20자 미만이면 의미 없는 문장일 확률이 높음
        if is_ko and len(s) < 10:
            continue
        if not is_ko and len(s) < 20:
            continue
        sentences.append(s)

    return sentences


def extract_span(
    sentences: List[str],
    center_idx: int,
    num_before: int = 1,
    num_after: int = 1,
    join_with: str = " "
):
    """
    [문맥 추출기]
    특정 문장(center_idx)을 기준으로 앞(before), 뒤(after) 문장을 합쳐서
    하나의 긴 '문맥 덩어리(Span)'를 만듭니다.

    예: [문장A, 문장B, 문장C] 에서 문장B가 중심이고 앞뒤 1개씩 포함하면
    -> "문장A 문장B 문장C" 반환
    """
    n = len(sentences)
    if n == 0:
        raise ValueError("sentences list is empty")

    # 인덱스 범위 체크
    if not (0 <= center_idx < n):
        raise IndexError(f"center_idx {center_idx} is out of range for {n} sentences")

    # 범위를 벗어나지 않도록 min/max 처리
    start_idx = max(0, center_idx - num_before)
    end_idx = min(n - 1, center_idx + num_after)

    # 문장들을 공백으로 이어 붙임
    span = join_with.join(sentences[start_idx : end_idx + 1])
    return span, start_idx, end_idx


def find_best_match_span_in_snippet(
    quote_text: str,
    snippet_text: str,
    url: str,
    num_before: int = 1,
    num_after: int = 1,
) -> Optional[Dict]:
    """
    [핵심 매칭 함수: Span-to-Span]
    인용문(Quote)과 검색 결과 요약문(Snippet) 사이의 의미적 유사도를 계산합니다.

    단순 문장 비교가 아니라,
    '인용문 문맥 덩어리' vs '요약문 문맥 덩어리'를 비교하여 정확도를 높였습니다.
    """
    if not snippet_text:
        return None

    # -----------------------------
    # 1) 인용문(Quote) 쪽 Span 만들기
    # -----------------------------
    # 전제: 검색 단계에서 이미 영어로 번역된 인용문이 들어온다고 가정 (is_ko=False)
    quote_sentences = split_into_sentences(quote_text, is_ko=False)

    if quote_sentences:
        # 인용문이 여러 문장일 경우, 가운데 문장을 중심으로 문맥을 형성함
        center_idx_q = len(quote_sentences) // 2
        quote_span_text, _, _ = extract_span(
            quote_sentences,
            center_idx_q,
            num_before=num_before,
            num_after=num_after,
            join_with=" ",
        )
    else:
        # 문장 분리가 안 될 정도로 짧거나 하나라면 통째로 사용
        quote_span_text = quote_text

    # -----------------------------
    # 2) 요약문(Snippet) 쪽 Span 후보들 만들기
    # -----------------------------
    sentences = split_into_sentences(snippet_text, is_ko=False)
    if not sentences:
        return None

    sim_model = get_sentence_model()    # SBERT 모델 로드 (캐싱됨)

    try:
        with torch.no_grad():   # 추론 시 그래디언트 계산 끄기 (메모리 절약)

            # 3) 인용문 Span을 벡터(Embedding)로 변환
            quote_emb = sim_model.encode(
                [quote_span_text],
                convert_to_tensor=True,
                normalize_embeddings=True,  # 코사인 유사도 계산을 위해 정규화
            )[0]

            # 4) 요약문 내의 모든 가능한 Span 후보 생성
            span_texts: List[str] = []
            span_meta: List[Dict] = []  # center_idx, start_idx, end_idx 저장

            n = len(sentences)
            for center_idx in range(n):
                span_text, s_idx, e_idx = extract_span(
                    sentences,
                    center_idx,
                    num_before=num_before,
                    num_after=num_after,
                    join_with=" ",
                )
                span_texts.append(span_text)
                span_meta.append(
                    {
                        "center_idx": center_idx,
                        "span_start_idx": s_idx,
                        "span_end_idx": e_idx,
                    }
                )

            # 5) 요약문 Span 후보들을 일괄 벡터화 (Batch Encoding)
            span_embs = sim_model.encode(
                span_texts,
                convert_to_tensor=True,
                normalize_embeddings=True,
            )

            # 6) 유사도 계산 (Quote Vector vs All Snippet Vectors)
            sims = util.cos_sim(quote_emb, span_embs)[0]

            # 가장 점수가 높은(유사한) 인덱스 찾기
            best_idx = int(torch.argmax(sims).item())
            best_score = float(sims[best_idx].item())

    except Exception as e:
        print(f"[WARN] SBERT similarity error (span-span mode): {e}")
        return None

    # -----------------------------
    # 7) 결과 반환
    # -----------------------------
    best_span_text = span_texts[best_idx]
    meta = span_meta[best_idx]
    center_idx = meta["center_idx"]

    best_sentence = sentences[center_idx]  # 인터페이스 유지용

    return {
        "url": url,
        "best_sentence": sentences[center_idx],  # 가장 중심이 되는 문장
        "best_score": best_score,  # 유사도 점수 (0~1)
        "span_text": best_span_text,  # 비교에 사용된 전체 문맥 덩어리
        "span_start_idx": meta["span_start_idx"],
        "span_end_idx": meta["span_end_idx"],
    }



def find_best_span_from_candidates_debug(
    quote_en: str,
    candidates: List[Dict],
    num_before: int = 1,
    num_after: int = 1,
    min_score: float = 0.4,
) -> Optional[Dict]:
    """
    [전체 후보군 탐색기]
    여러 검색 결과(Snippet)들을 순회하며,
    SBERT를 통해 가장 인용문과 유사한 '최고의 원문 후보'를 찾아냅니다.

    Returns:
        가장 점수가 높은 하나의 결과(best_global)를 반환하되,
        내부에 "top_k_candidates" 리스트를 포함시켜 2, 3등 후보도 볼 수 있게 합니다.
    """

    global_candidates: List[Dict] = []

    for cand in candidates:
        url = cand.get("url")
        snippet = cand.get("snippet")
        if not url:
            continue

        try:
            # 개별 스니펫 내에서 최고의 Span 찾기
            span_res = find_best_match_span_in_snippet(
                quote_text=quote_en,
                snippet_text=snippet,
                url=url,
                num_before=num_before,
                num_after=num_after,
            )
        except Exception as e:
            print(f"[WARN] span extraction error (url={url}): {e}")
            continue

        if not span_res:
            continue

        # 점수 필터링
        score = span_res.get("best_score", -1.0)
        if score < min_score:
            continue

            # 후보 리스트에 추가
        global_candidates.append(span_res)

    # 후보가 하나도 없으면 실패
    if not global_candidates:
        return None

    # 점수 기준 내림차순 정렬
    sorted_candidates = sorted(
        global_candidates,
        key=lambda x: x.get("best_score", 0.0),
        reverse=True,
    )

    # 1등 후보 선택
    best_global = sorted_candidates[0]

    # best뿐만 아니라 전체 등수 정보를 함께 담아 보냄
    # 나중에 디버깅하거나, 사용자에게 "다른 후보 보기" 기능을 제공할 때 유용함
    best_global["top_k_candidates"] = sorted_candidates

    return best_global
