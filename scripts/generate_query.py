"""
Compatibility wrappers around the refactored qdd2 modules.
This keeps the existing import surface while routing logic to modular components.
"""

from qdd2.name_resolution import resolve_person_name_en
from qdd2.query_builder import generate_search_query
from qdd2.search_client import (
    collect_candidates_google_cse,
    extract_pdf_url_from_html,
    extract_text_from_pdf_url,
    google_cse_search,
    html_to_text,
    is_valid_page,
)
from qdd2.snippet_matcher import (
    extract_span,
    find_best_match_span_in_snippet,
    find_best_span_from_candidates_debug,
    split_into_sentences,
)
from qdd2.text_utils import contains_korean
from qdd2.translation import translate_ko_to_en

__all__ = [
    "resolve_person_name_en",
    "generate_search_query",
    "collect_candidates_google_cse",
    "extract_pdf_url_from_html",
    "extract_text_from_pdf_url",
    "google_cse_search",
    "html_to_text",
    "is_valid_page",
    "extract_span",
    "find_best_match_span_in_snippet",
    "find_best_span_from_candidates_debug",
    "split_into_sentences",
    "contains_korean",
    "translate_ko_to_en",
]
