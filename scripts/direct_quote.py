"""
Compatibility wrapper for quote utilities.
Prefer importing from qdd2.text_utils and qdd2.snippet_matcher directly in new code.
"""

from typing import List, Tuple

from qdd2.snippet_matcher import extract_span
from qdd2.text_utils import extract_quotes_advanced, split_sentences


__all__ = ["split_sentences", "extract_quotes_advanced", "extract_span"]
