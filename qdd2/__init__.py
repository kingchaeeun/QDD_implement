"""
QDD2 modular package.
(QDD2 모듈 패키지 초기화 파일)

이 파일은 `qdd2` 폴더를 하나의 파이썬 패키지로 인식하게 하고,
핵심 기능들을 외부에서 쉽게 꺼내 쓸 수 있도록(Shortcut) 연결해주는 역할을 합니다.
"""

from qdd2.entities import extract_ner_entities

from qdd2.keywords import extract_entities_only

from qdd2.translation import translate_ko_to_en
from qdd2.name_resolution import resolve_person_name_en, get_wikidata_english_name
from qdd2.query_builder import generate_search_query

# 외부에서 "from qdd2 import *" 를 실행했을 때 가져올 함수 목록 정의
__all__ = [
    "extract_ner_entities",
    "extract_entities_only",      # [수정됨] 변경된 함수 이름 반영
    "translate_ko_to_en",
    "resolve_person_name_en",
    "get_wikidata_english_name",
    "generate_search_query",
]
