"""
Compatibility wrappers for the refactored qdd2 package.
Existing code can continue to import from find_original.py while the real logic lives in qdd2/.
"""

from qdd2.entities import extract_ner_entities
from qdd2.keywords import extract_keywords_with_ner, rerank_with_ner_boost
from qdd2.text_utils import extract_quotes, split_sentences, normalize_korean_phrase, clean_text
from qdd2.translation import translate_ko_to_en

__all__ = [
    "extract_ner_entities",
    "extract_keywords_with_ner",
    "rerank_with_ner_boost",
    "extract_quotes",
    "split_sentences",
    "normalize_korean_phrase",
    "clean_text",
    "translate_ko_to_en",
]
