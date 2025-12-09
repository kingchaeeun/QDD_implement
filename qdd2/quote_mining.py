"""
Quote-mining distortion classifier integration.

This module loads the QuoteMiningDetection RoBERTa-based classifier
(`classifier_best.bin`) and exposes a small inference helper:

    (quote_text, origin_span_text) -> distortion probabilities.

The checkpoint is expected at:
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
    Resolve the root directory of the `quote-origin-pipeline` project.
    We assume this file lives in `quote-origin-pipeline/qdd2/`.
    """
    return Path(__file__).resolve().parents[1]


def _get_checkpoint_path() -> Path:
    """
    Absolute path to the fine-tuned quote-mining classifier checkpoint.
    """
    return (
        _get_project_root()
        / "QuoteMiningDetection"
        / "model_result"
        / "classifier_best.bin"
    )


@lru_cache(maxsize=1)
def get_quote_mining_model() -> Tuple[AutoTokenizer, AutoModelForSequenceClassification, torch.device]:
    """
    Lazily load the tokenizer + classifier once per process.

    Returns:
        (tokenizer, model, device)
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    ckpt_path = _get_checkpoint_path()
    if not ckpt_path.is_file():
        raise FileNotFoundError(
            f"Quote-mining checkpoint not found at: {ckpt_path}. "
            "Please place `classifier_best.bin` under QuoteMiningDetection/model_result/."
        )

    # Backbone + classification head; state dict from QuoteMiningDetection
    tokenizer = AutoTokenizer.from_pretrained(config.QUOTE_MINING_MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(
        config.QUOTE_MINING_MODEL_NAME,
        num_labels=2,
    )

    state = torch.load(ckpt_path, map_location=device)

    # Support both state_dict and full-model saves as best we can.
    if isinstance(state, dict):
        # If some keys don't match exactly, we still want to load what we can.
        model.load_state_dict(state, strict=False)
    else:
        # Fallback: assume the checkpoint is a full model object.
        model = state

    model.to(device)
    model.eval()

    return tokenizer, model, device


@torch.no_grad()
def score_quote_pair(quote_text: str, origin_span_text: str) -> Dict[str, float]:
    """
    Compute distortion probability for a (quote, origin-span) pair.

    Returns:
        {
            "prob_original": float,   # P(label=0)
            "prob_distorted": float,  # P(label=1)
            "is_distorted": bool,
        }
    """
    tokenizer, model, device = get_quote_mining_model()

    encoded = tokenizer(
        text=quote_text,
        text_pair=origin_span_text,
        padding="max_length",
        truncation=True,
        max_length=256,
        return_tensors="pt",
    )

    encoded = {k: v.to(device) for k, v in encoded.items()}

    outputs = model(**encoded)
    # HF models usually return an object with `.logits`
    logits = getattr(outputs, "logits", outputs[0])

    probs = torch.softmax(logits, dim=-1)[0].detach().cpu().tolist()
    prob_original = float(probs[0])
    prob_distorted = float(probs[1])

    return {
        "prob_original": prob_original,
        "prob_distorted": prob_distorted,
        "is_distorted": prob_distorted >= 0.5,
    }


