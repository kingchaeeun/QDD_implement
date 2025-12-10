"""
Translation utilities.
(번역 유틸리티 모듈)

이 모듈은 한국어 텍스트를 영어로 번역하는 기능을 담당합니다.
Hugging Face의 MarianMT 모델(Helsinki-NLP/opus-mt-ko-en)을 사용하여
비교적 가볍고 빠른 번역 성능을 제공합니다.
"""

import logging

from qdd2.models import get_translation_models

logger = logging.getLogger(__name__)


def translate_ko_to_en(text: str) -> str:
    """
    [한영 번역 함수]
    한국어(Korean) 문장을 입력받아 영어(English)로 번역합니다.

    Args:
        text: 번역할 한국어 문장 (예: "트럼프가 말했다.")

    Returns:
        번역된 영어 문장 (예: "Trump said.")
    """
    # 1. 모델과 토크나이저 로드
    # (models.py에서 @lru_cache로 관리되므로, 두 번째 호출부터는 즉시 가져옵니다)
    tokenizer, model = get_translation_models()

    logger.debug("Translating text (len=%d): %s", len(text), text)

    # 2. 텍스트 전처리 (Tokenization)
    # 사람이 쓰는 글자를 모델이 이해하는 숫자(Tensor)로 변환합니다.
    # return_tensors="pt": PyTorch 형식으로 반환
    # truncation=True: 모델이 처리할 수 있는 길이보다 길면 자름 (에러 방지)
    tokens = tokenizer(text, return_tensors="pt", padding=True, truncation=True)

    # 3. 번역문 생성 (Generation)
    # **tokens: 입력 데이터(input_ids, attention_mask 등)를 모델에 주입
    # 모델이 열심히 계산해서 번역된 문장의 숫자 코드를 뱉어냅니다.
    translated = model.generate(**tokens)

    # 4. 결과 후처리 (Decoding)
    # 모델이 뱉은 숫자 코드를 다시 사람의 언어(영어)로 바꿉니다.
    # skip_special_tokens=True: 문장 끝을 알리는 기호(<eos>) 같은 특수 문자를 제거
    out = tokenizer.decode(translated[0], skip_special_tokens=True)

    logger.debug("Translation result: %s", out)

    return out
