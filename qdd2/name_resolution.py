"""
Person-name resolution helpers.

[파일 설명]
한국어 인물명(예: '트럼프', '윤석열')을 검색 가능한 영어 이름(예: 'Donald Trump', 'Yoon Suk-yeol')으로
변환하는 헬퍼 모듈입니다.

[변환 우선순위]
1순위: 로컬 인명사전 (PERSON_NAME_LEXICON) - 우리가 직접 지정한 정확한 매핑
2순위: 위키데이터 (Wikidata) - 전 세계 공용 데이터베이스 조회
3순위: 기계 번역 (Translation API) - 위 1, 2안이 모두 실패할 경우 최후의 수단
"""

from typing import Dict, Optional

import requests

from qdd2 import config

# 로컬에 정의된 인명 사전 (예: {"트럼프": "Donald Trump"})
from qdd2.name_lexicon import PERSON_NAME_LEXICON
from qdd2.translation import translate_ko_to_en

def get_wikidata_english_name(korean_name: str, timeout: int = 10) -> Dict[str, Optional[str]]:
    """"
    Wikidata API를 사용하여 한국어 이름에 대응하는 영어 라벨을 조회합니다.

    [Return 예시]
    성공 시: {"ko": "윤석열", "en": "Yoon Suk-yeol", "qid": "Q12345"}
    실패 시: {"error": "..."}
    """
    # 1. 엔티티 검색 (한국어 이름으로 검색)
    search_url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbsearchentities",
        "search": korean_name,
        "language": "ko",
        "format": "json",
    }

    # 위키데이터는 봇 접근 시 User-Agent 헤더를 요구합니다.
    headers = {"User-Agent": config.HTTP_HEADERS["User-Agent"]}

    try:
        resp = requests.get(search_url, params=params, headers=headers, timeout=timeout)
        data = resp.json()
    except Exception:
        return {"error": "Failed to fetch search results"}

    # 검색 결과가 없으면 종료
    if "search" not in data or not data["search"]:
        return {"error": "No matching Wikidata entry"}

    # 2. 첫 번째 검색 결과의 상세 정보(라벨) 조회
    qid = data["search"][0]["id"]
    detail_url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"

    try:
        detail = requests.get(detail_url, headers=headers, timeout=timeout).json()
        labels = detail["entities"][qid]["labels"]
    except Exception:
        return {"error": "Failed to fetch entity details"}

    # 3. 영어 라벨이 있는지 확인
    if "en" in labels:
        return {"ko": korean_name, "en": labels["en"]["value"], "qid": qid}

    # 영어 라벨은 없지만 한국어 라벨은 있는 경우 (번역은 안 됐지만 찾긴 찾음)
    if "ko" in labels:
        return {"ko": korean_name, "en": None, "qid": qid}
    return {"error": "No labels found"}


def resolve_person_name_en(name_ko: str) -> str:
    """
    [핵심 함수] 한국어 인명을 영어 이름으로 변환합니다.

    Flow:
    1. Local Lexicon (수동 사전) 확인
    2. Wikidata 검색
    3. Google/Papago 번역 API
    """
    name_ko = (name_ko or "").strip()
    if not name_ko:
        return ""

    # -------------------------------------------------------
    # [Step 1] 로컬 인명사전 (가장 빠르고 정확함)
    # -------------------------------------------------------

    # 1-1) 완전 일치 검색 (예: "트럼프")
    if name_ko in PERSON_NAME_LEXICON:
        return PERSON_NAME_LEXICON[name_ko]

    # 1-2) 부분 일치 검색 (예: "미국의 트럼프 당선인")
    # 사전 키가 입력 문자열에 포함되어 있으면 그 값을 사용
    for key, val in PERSON_NAME_LEXICON.items():
        if key in name_ko:
            return val

    # -------------------------------------------------------
    # [Step 2] 위키데이터 조회 (공신력 있는 표기법 확인)
    # -------------------------------------------------------
    # 외부 API이므로 너무 오래 걸리면 건너뛰도록 timeout 설정
    try:
        info = get_wikidata_english_name(name_ko, timeout=3)
        if isinstance(info, dict) and info.get("en"):
            return info["en"]
    except Exception:
        # 위키데이터 연결 실패 시 무시하고 다음 단계로
        pass

    # -------------------------------------------------------
    # [Step 3] 최후의 수단: 기계 번역
    # -------------------------------------------------------
    try:
        translated = translate_ko_to_en(name_ko)
        return translated
    except Exception:
        # 번역마저 실패하면 원래 한국어 이름 반환
        return name_ko
