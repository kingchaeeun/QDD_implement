"""
Lazy-loading model accessors.
(모델 지연 로딩 모듈)

이 모듈은 무거운 딥러닝 모델들(BERT, 번역 모델 등)을
프로그램이 시작될 때가 아니라, '실제로 처음 필요할 때' 로딩합니다.
또한 @lru_cache를 사용하여 한 번 로딩된 모델은 메모리에 두고 계속 재사용합니다.
"""

from functools import lru_cache
from typing import Tuple

import torch
from sentence_transformers import SentenceTransformer
from transformers import MarianMTModel, MarianTokenizer, pipeline

from qdd2 import config


def _resolve_device(device: int) -> int:
    """
    Hugging Face Transformers 라이브러리에 맞는 장치(Device) 번호를 반환합니다.

    - GPU 사용 가능 시: 해당 인덱스 (예: 0) 반환
    - GPU 불가 또는 CPU 요청 시: -1 반환 (Transformers 규칙)
    """
    if device is None:
        return -1

    # GPU 번호를 넣었더라도, 실제 CUDA가 안 깔려있으면 강제로 CPU(-1)로 변경
    if device >= 0 and not torch.cuda.is_available():
        return -1
    return device


@lru_cache(maxsize=4)
def get_ner_pipeline(device: int = config.DEFAULT_DEVICE):
    """
    [NER 모델 로더]
    개체명 인식(NER)을 위한 Hugging Face 파이프라인을 로드합니다.
    최초 호출 시에만 모델을 메모리에 올리고, 이후에는 캐시된 모델을 반환합니다.

    Args:
        device (int): 사용할 GPU 번호 (기본값은 config에서 가져옴)
    """
    resolved = _resolve_device(device)

    # pipeline 함수 자체가 모델 다운로드/로딩을 모두 처리함
    return pipeline(
        "ner",
        model=config.NER_MODEL_NAME,
        tokenizer=config.NER_MODEL_NAME,
        device=resolved,
    )


@lru_cache(maxsize=1)
def get_translation_models() -> Tuple[MarianTokenizer, MarianMTModel]:
    """
    [번역 모델 로더]
    한국어 -> 영어 번역을 위한 MarianMT 모델과 토크나이저를 로드합니다.

    Returns:
        (tokenizer, model) 튜플 반환
    """
    # from_pretrained: 허깅페이스 허브에서 모델 가중치를 다운로드 및 로드
    tokenizer = MarianTokenizer.from_pretrained(config.TRANSLATION_MODEL_NAME)
    model = MarianMTModel.from_pretrained(config.TRANSLATION_MODEL_NAME)

    # 참고: 번역 모델은 기본적으로 CPU에 로드됩니다.
    # GPU를 쓰려면 사용하는 쪽에서 .to(device)를 호출해야 합니다.
    return tokenizer, model


@lru_cache(maxsize=1)
def get_sentence_model() -> SentenceTransformer:
    """
    [문장 유사도 모델 로더]
    SBERT (Sentence-BERT) 모델을 로드합니다.
    스니펫(Snippet)과 인용문의 유사도를 비교할 때 사용됩니다.
    """
    # SentenceTransformer는 내부적으로 GPU가 있으면 알아서 잡는 편
    return SentenceTransformer(config.SENTENCE_MODEL_NAME)
