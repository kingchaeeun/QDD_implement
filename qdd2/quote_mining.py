"""
Quote-mining distortion classifier integration.
(인용 왜곡 탐지 모델 연동 모듈)

이 모듈은 사전에 학습된 분류 모델(`classifier_best.bin`)을 로드하고,
간단한 함수 하나로 추론(Inference)을 수행할 수 있도록 도와줍니다.

입력: (인용문, 원문 스니펫)
출력: 왜곡 확률 (0~1 사이 값)

예상되는 모델 경로:
    quote-origin-pipeline/QuoteMiningDetection/model_result/classifier_best.bin
"""

from functools import lru_cache
from pathlib import Path
from typing import Dict, Tuple

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from qdd2 import config


def _get_project_root() -> Path:
    """
    [경로 도우미]
    현재 파일의 위치를 기준으로 프로젝트의 최상위 루트 디렉토리를 찾습니다.

    구조 가정:
      - 현재 파일: .../quote-origin-pipeline/qdd2/classifier.py
      - 루트:      .../quote-origin-pipeline/
    """
    # __file__은 현재 파일의 경로입니다
    # .resolve()로 절대 경로를 구하고, .parents[1]로 두 단계 상위 폴더로 이동합니다
    return Path(__file__).resolve().parents[1]


def _get_checkpoint_path() -> Path:
    """
    [체크포인트 경로]
    학습된 모델 파일(classifier_best.bin)의 절대 경로를 반환합니다.
    """
    return (
            _get_project_root()
            / "QuoteMiningDetection"  # 학습 프로젝트 폴더명
            / "model_result"  # 결과 저장소
            / "classifier_best.bin"  # 학습된 가중치 파일
    )


@lru_cache(maxsize=1)
def get_quote_mining_model() -> Tuple[AutoTokenizer, AutoModelForSequenceClassification, torch.device]:
    """
    [모델 로더] (싱글톤 패턴 적용)
    토크나이저와 분류 모델을 로드합니다.
    @lru_cache가 있으므로, 이 함수가 여러 번 호출되어도 실제 로딩은 '최초 1회'만 수행됩니다.

    Returns:
        (tokenizer, model, device) 튜플
    """

    # 1. 장치 설정: GPU(cuda)가 있으면 사용하고, 없으면 CPU를 씁니다.
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # 2. 파일 존재 여부 확인
    ckpt_path = _get_checkpoint_path()
    if not ckpt_path.is_file():
        raise FileNotFoundError(
            f"Quote-mining checkpoint not found at: {ckpt_path}. "
            "Please place `classifier_best.bin` under QuoteMiningDetection/model_result/."
        )

    # 3. 모델 뼈대(Architecture)와 토크나이저 준비
    tokenizer = AutoTokenizer.from_pretrained(config.QUOTE_MINING_MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(
        config.QUOTE_MINING_MODEL_NAME,
        num_labels=2,   # 레이블이 2개(0:정상, 1:왜곡)인 분류 모델
    )
    # 4. 학습된 가중치(State Dictionary) 로드
    # map_location=device: CPU 환경에서도 GPU로 학습된 모델을 로드할 수 있게 해줍니다.
    state = torch.load(ckpt_path, map_location=device)

    # 5. 가중치 덮어쓰기
    if isinstance(state, dict):
        # state가 딕셔너리 형태라면 (일반적인 저장 방식)
        # strict=False: 모델 레이어 이름이 살짝 달라도(예: module.bert vs bert) 에러 내지 않고 로드함
        model.load_state_dict(state, strict=False)
    else:
        # state가 모델 객체 통째로 저장된 경우 (Fallback)
        model = state

    # 모델을 해당 장치(GPU/CPU)로 이동시키고, 평가 모드(eval)로 전환
    model.to(device)
    model.eval()

    return tokenizer, model, device


@torch.no_grad()    # 추론 시에는 기울기(Gradient) 계산을 꺼서 메모리를 아낍니다.
def score_quote_pair(quote_text: str, origin_span_text: str) -> Dict[str, float]:
    """
    [핵심 추론 함수]
    인용문(quote)과 원문 구간(origin_span)을 비교하여 왜곡 확률을 계산합니다.

    Args:
        quote_text: "트럼프가 베네수엘라를 폐쇄한다고 했다" (인용문)
        origin_span_text: "모든 교통을 차단하는 것을 고려 중이다" (원문 의심 구간)

    Returns:
        {
            "prob_original": 0.1,   # 원본일 확률 (정상)
            "prob_distorted": 0.9,  # 왜곡일 확률
            "is_distorted": True,   # 왜곡 여부 (50% 이상이면 True)
        }
    """
    # 위에서 만든 로더를 통해 모델과 토크나이저를 가져옵니다.
    tokenizer, model, device = get_quote_mining_model()

    # 1. 입력 텍스트 전처리 (Tokenization)
    # 두 문장을 하나의 쌍(Pair)으로 묶어서 모델에 넣습니다.
    encoded = tokenizer(
        text=quote_text,
        text_pair=origin_span_text,
        padding="max_length",  # 길이를 맞춤
        truncation=True,  # 너무 길면 자름
        max_length=256,  # 최대 길이 제한
        return_tensors="pt",  # PyTorch 텐서 형태로 반환
    )

    # 데이터를 GPU/CPU 장치로 이동
    encoded = {k: v.to(device) for k, v in encoded.items()}

    # 2. 모델 예측 (Forward Pass)
    outputs = model(**encoded)

    # 모델의 출력값(Logits)을 가져옵니다.
    # getattr: 혹시 출력 형식이 다를 경우를 대비한 안전 장치
    logits = getattr(outputs, "logits", outputs[0])

    # 3. 확률 계산 (Softmax)
    # Logits(-무한대 ~ +무한대)를 확률(0 ~ 1)로 변환
    probs = torch.softmax(logits, dim=-1)[0].detach().cpu().tolist()

    prob_original = float(probs[0])  # 레이블 0: 정상(Original)일 확률
    prob_distorted = float(probs[1])  # 레이블 1: 왜곡(Distorted)일 확률

    return {
        "prob_original": prob_original,
        "prob_distorted": prob_distorted,
        # 왜곡 확률이 50%(0.5) 이상이면 '왜곡됨'으로 판정
        "is_distorted": prob_distorted >= 0.5,
    }


