"""
Entity extraction utilities.
"""

from typing import Dict, List, Sequence, Tuple
from qdd2 import config
from qdd2.entities import extract_ner_entities
from qdd2.text_utils import normalize_korean_phrase


def extract_entities_only(
    text: str,
    device: int = config.DEFAULT_DEVICE,
    debug: bool = False,
) -> Dict:
    """
    텍스트에서 NER(개체명 인식) 모델을 사용하여 엔티티(인물, 장소 등)만 추출합니다.
    (기존의 KeyBERT 키워드 추출 로직은 제거되었습니다.)

    Args:
        text (str): 분석할 기사 본문 텍스트
        device (int): 모델을 돌릴 장치 (CPU/GPU)
        debug (bool): 디버그 로그 출력 여부

    Returns:
        Dict:
            {
                "entities": [...],  # 모델이 뱉어낸 원본 엔티티 리스트 (점수 포함)
                "entities_by_type": {"PER": [...], "LOC": [...], ...}  # 타입별로 정리되고 중복 제거된 리스트
            }
    """
    # 1. NER 모델 실행
    # text에서 사람(PER), 장소(LOC), 기관(ORG) 등을 찾아냅니다.
    entities = extract_ner_entities(text, device=device, debug=debug)

    # 2. 결과 정리를 위한 변수 초기화
    entities_by_type: Dict[str, List[str]] = {} # 결과를 타입별로 담을 딕셔너리
    seen_normalized = set() # 중복 체크용 (띄어쓰기 제거된 버전 저장)

    # 3. 추출된 엔티티 하나씩 순회하며 정제
    for ent in entities:
        label = ent["label"]    # 예: 'PER', 'LOC'
        word = ent["word"]      # 예: '트럼프', '서울시'

        # 비교를 위해 정규화 (특수문자 제거, 공백 정리 등)
        normalized = normalize_korean_phrase(word)

        is_duplicate = False

        # 중복 및 포함 관계 처리 (예: '서울' vs '서울시')
        # 이미 등록된 단어들(seen)과 현재 단어(normalized)를 비교
        for seen in list(seen_normalized):

            # CASE A: 현재 단어가 이미 있는 단어의 '일부분'인 경우 (Skip)
            # 예: 이미 '서울시'가 있는데 '서울'이 들어옴 -> '서울'은 버림
            if normalized in seen and normalized != seen:
                is_duplicate = True
                break

            # CASE B: 현재 단어가 이미 있는 단어를 '포함'하는 경우 (Update)
            # 예: 이미 '서울'이 있는데 '서울시'가 들어옴
            # -> 기존의 짧은 '서울'을 삭제하고, 더 구체적인 '서울시'를 살림
            if seen in normalized and normalized != seen:
                seen_normalized.discard(seen)   # 기존 짧은 단어 삭제 (set에서)

                # entities_by_type 딕셔너리에서도 기존 짧은 단어를 찾아 삭제
                for lbl in entities_by_type:
                    entities_by_type[lbl] = [
                        w for w in entities_by_type[lbl] if normalize_korean_phrase(w) != seen
                    ]

        # 중복이 아니라면 최종 목록에 추가
        if not is_duplicate:
            seen_normalized.add(normalized) # 중복 체크용 set에 추가

            # 해당 라벨(PER, LOC 등) 리스트가 없으면 새로 생성
            entities_by_type.setdefault(label, [])

            # 리스트에 실제 단어 추가 (혹시 모를 완전 동일 중복 방지)
            if word not in entities_by_type[label]:
                entities_by_type[label].append(word)

    # 4. 최종 결과 반환
    return {
        "entities": entities,
        "entities_by_type": entities_by_type,
    }
