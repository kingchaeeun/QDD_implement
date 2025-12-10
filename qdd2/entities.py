"""
NER helpers: run pipeline, merge BIO tokens, and return cleaned entities.
(NER 도우미: 파이프라인 실행, BIO 토큰 병합, 엔티티 정제)

이 모듈은 AI 모델이 뱉어낸 '토큰 조각'들을 우리가 이해할 수 있는 '완전한 단어'로 조립합니다.
예: "B-PER(트)", "I-PER(럼)", "I-PER(프)" -> "PER: 트럼프"
"""

from typing import Dict, List, Sequence

from qdd2 import config
from qdd2.models import get_ner_pipeline
from qdd2.text_utils import split_sentences


def merge_ner_entities(results: Sequence[Dict], debug: bool = False) -> List[Dict]:
    """
    [BIO 태그 병합 함수]
    모델이 예측한 BIO(Begin-Inside-Outside) 태그 조각들을 모아서 하나의 완전한 개체명으로 만듭니다.

    Args:
        results: 모델의 Raw 출력값 (예: [{'entity': 'B-PER', 'word': '트'}, ...])

    Returns:
        정제된 엔티티 리스트 (예: [{'label': 'PER', 'word': '트럼프'}])
    """
    merged_groups = []  # 병합된 토큰 그룹들을 담을 리스트
    buffer = []  # 현재 조립 중인 단어 조각들을 임시로 담는 버퍼

    for ent in results:
        # 1. 태그 분석 (예: "B-PER" -> type="PER", tag="B")
        parts = (ent.get("entity") or "").split("-")
        entity_type = parts[0] if parts else ""     # PER, LOC, ORG 등
        tag_type = parts[1] if len(parts) > 1 else "B"  # B(시작) 또는 I(중간)

        # 2. 필터링 (config.py에 정의된 관심 있는 라벨만 처리)
        if entity_type not in config.NER_LABELS:
            if debug:
                print(f"Skipping non-target label: {entity_type}")
            continue

        # 3. BIO 로직에 따른 그룹핑
        if tag_type == "B":
            # "B"(Begin)가 나오면 새로운 단어의 시작입니다.
            # 기존에 조립 중이던게 있다면(buffer) 저장하고, 새 버퍼를 시작합니다.
            if buffer:
                merged_groups.append(buffer)

            buffer = [ent]
        elif tag_type == "I" and buffer:
            # "I"(Inside)가 나왔고, 버퍼에 앞선 조각이 있다면 이어 붙일지 확인합니다.
            prev_type = (buffer[-1]["entity"] or "").split("-")[0]

            # (1) 같은 종류(PER-PER)이고 (2) 위치가 인접해 있다면 같은 단어로 간주
            if entity_type == prev_type and ent["start"] <= buffer[-1]["end"] + 1:
                buffer.append(ent)
            else:
                # 이어지지 않는다면 기존 버퍼를 저장하고 새로 시작
                merged_groups.append(buffer)
                buffer = [ent]
        else:
            # 그 외의 경우(O 태그 등) 기존 버퍼를 털어냅니다
            if buffer:
                merged_groups.append(buffer)
            buffer = []

    # 루프가 끝나고 남은 버퍼 처리
    if buffer:
        merged_groups.append(buffer)

    # 4. 최종 문자열 조립 및 정제
    entities: List[Dict] = []
    for group in merged_groups:
        # 그룹의 첫 번째 토큰에서 라벨(PER 등)을 가져옵니다.
        entity_type = (group[0]["entity"] or "").split("-")[0]

        # 각 토큰의 글자(word)를 이어 붙입니다.
        # "##"은 BERT 토크나이저가 단어 중간임을 표시하는 기호이므로 제거합니다.
        # 예: "트" + "##럼" + "##프" -> "트럼프"
        word = "".join([str(e.get("word", "")).replace("##", "") for e in group]).strip()

        # --- 필터링 ---
        if len(word) < 2:   # 한 글자짜리는 보통 의미가 없어서 버림
            continue
        if word in {'"', "'", "(", ")", "[", "]", "{", "}", ",", ".", "!", "?"}:
            continue
        if word.replace(" ", "").replace("-", "").replace("·", "") == "":
            continue

        entities.append({"label": entity_type, "word": word})
        if debug:
            print(f"Merged entity: {entity_type} -> {word}")

    return entities


def extract_ner_entities(text: str, device: int = config.DEFAULT_DEVICE, debug: bool = False) -> List[Dict]:
    """
    [NER 실행 메인 함수]
    텍스트를 문장 단위로 쪼개서 NER을 수행하고, 결과를 합쳐서 반환합니다.

    Returns:
        [{'label': 'PER', 'word': '트럼프'}, {'label': 'LOC', 'word': '베네수엘라'}, ...]
    """
    # 1. 문장 분리 (BERT 입력 길이 제한 해결)
    sentences = split_sentences(text)

    # 2. 모델 로드 (캐싱된 파이프라인 가져오기)
    ner = get_ner_pipeline(device=device)
    all_entities: List[Dict] = []

    # 3. 각 문장별로 NER 수행
    for idx, sentence in enumerate(sentences):
        # 모델 추론 실행 (Raw Output)
        raw = ner(sentence)

        # BIO 태그 병합 및 정제
        merged = merge_ner_entities(raw, debug=debug)
        all_entities.extend(merged)

        if debug:
            print(f"[Sentence {idx + 1}] {sentence[:80]}...")
            print(f"  Raw: {len(raw)} -> Merged: {len(merged)}")

    return all_entities
