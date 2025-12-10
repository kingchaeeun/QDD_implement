"""
Lightweight text helpers: cleaning, normalization, sentence splitting, and quote extraction.
(가벼운 텍스트 처리 도구 모음: 정제, 정규화, 문장 분리, 인용문 추출)

이 모듈은 무거운 NLP 라이브러리 없이, 정규표현식(Regex)만으로
빠르고 효율적으로 텍스트를 다듬는 함수들을 제공합니다.
"""

import re
from typing import Iterable, List


def clean_text(text: str) -> str:
    """
    [공백 정리 함수]
    탭(\t), 줄바꿈(\n), 여러 개의 공백을 하나의 띄어쓰기로 통일하고,
    양쪽 끝의 불필요한 공백을 제거합니다.
    """
    if text is None:
        return ""
    # \s+ : 공백 문자가 1개 이상 연속된 구간을 찾아서 " " (스페이스 1개)로 바꿉니다.
    return re.sub(r"\s+", " ", text).strip()


def normalize_korean_phrase(text: str) -> str:
    """
    [한국어 단어 정규화]
    비교를 위해 단어를 '표준 형태'로 만듭니다.
    예: "문재인_대통령", "문재인 대통령", "문재인/대통령" -> 모두 "문재인대통령"으로 통일

    중복 검사나 엔티티 매칭 시, 띄어쓰기나 특수문자 때문에
    같은 단어를 다르게 인식하는 것을 방지합니다.
    """
    if text is None:
        return ""
    # 특수 기호(가운뎃점, 하이픈, 언더바, 슬래시)와 모든 공백(\s)을 제거합니다.
    normalized = re.sub(r"[·‧ㆍ\\-_/\\s]", "", text)
    # 영어의 경우 소문자로 통일합니다.
    return normalized.lower()


def split_sentences(text: str) -> List[str]:
    """
    [간단한 문장 분리기]
    마침표(.), 느낌표(!), 물음표(?) 뒤에 공백이 오고,
    그 뒤에 다시 글자가 시작될 때 문장을 자릅니다.

    복잡한 NLP 모델 없이도 한국어/영어 혼용 텍스트를 꽤 잘 분리합니다.
    """
    text = clean_text(text)
    if not text:
        return []

    # 정규식 설명:
    # (?<=[.!?]) : 앞쪽에 마침표/느낌표/물음표가 있어야 함 (Lookbehind)
    # \s+        : 그 사이에 공백이 1개 이상 있어야 함
    # (?=[가-힣A-Za-z]) : 뒤쪽에 한글이나 알파벳이 와야 함 (Lookahead)
    # -> 이렇게 하면 "Mr. Kim"의 점(.) 뒤에는 공백은 있지만 바로 대문자가 와서 잘리지 않을 확률이 높음
    return re.split(r"(?<=[.!?])\s+(?=[가-힣A-Za-z])", text)


def extract_quotes(text: str) -> List[str]:
    """
    [단순 인용문 추출]
    큰따옴표(" ") 안에 있는 내용만 빠르게 추출합니다.
    """
    # "([^"]+)" : 따옴표로 시작해서, 따옴표가 아닌 글자들을 쭉 찾고, 따옴표로 끝나는 구간
    return re.findall(r'"([^"]+)"', text or "")


def extract_quotes_advanced(text: str, min_length: int = 6) -> List[str]:
    """
    [고급 인용문 추출]
    큰따옴표(""), 굽은 따옴표(“”), 작은따옴표('') 등 다양한 인용 부호를 모두 찾습니다.
    너무 짧은 인용문이나 중복된 내용은 제거합니다.
    """
    text = text or ""
    # 다양한 인용 부호 패턴 정의
    patterns = [
        r"“([^”]+)”",  # 굽은 큰따옴표 (한글/워드 등에서 사용)
        r'"([^"]+)"',  # 직선 큰따옴표 (프로그래밍 표준)
        r"'([^']+)'",  # 작은따옴표
        r"‘([^’]+)’",  # 굽은 작은따옴표
    ]

    quotes: List[str] = []
    for pattern in patterns:
        # 각 패턴에 맞는 내용을 찾아 리스트에 추가
        quotes.extend(re.findall(pattern, text))

    # 중복 제거 및 길이 필터링 (순서 유지)
    seen = set()
    unique_quotes = []
    for q in quotes:
        cleaned = q.strip()
        # 1. 너무 짧으면(min_length 미만) 의미 없는 말일 수 있으니 제외
        # 2. 이미 등록된 인용문(seen)이면 제외
        if len(cleaned) < min_length or cleaned in seen:
            continue
        seen.add(cleaned)
        unique_quotes.append(cleaned)

    return unique_quotes


def contains_korean(text: str) -> bool:
    """
    [한국어 포함 여부 확인]
    텍스트에 한글 글자(가~힣)가 하나라도 포함되어 있으면 True를 반환합니다.
    검색 쿼리 생성 시 언어 설정(ko/en)을 판단할 때 유용합니다.
    """
    return bool(re.search(r"[가-힣]", text or ""))


def dedupe_preserve_order(items: Iterable[str]) -> List[str]:
    """
    [순서 보장 중복 제거]
    리스트의 순서는 유지하면서 중복된 항목만 제거합니다.
    (Python의 set()을 그냥 쓰면 순서가 뒤섞이기 때문에 이 함수를 사용합니다.)
    """
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
