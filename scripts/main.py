"""
Example CLI runner for the qdd2 pipeline.

Usage:
  python main.py --text '트럼프 "베네수엘라 상공 전면폐쇄"' --date 2024-11-29

Flags:
  --text / --file : input text (one must be provided)
  --quote         : specific quote sentence (optional; if omitted, pass None)
  --date          : article date YYYY-MM-DD (optional)
  --top-n         : number of keywords to extract (default 15)
  --top-k         : keywords used in the final query (default 3)
  --rollcall      : rollcall.com-friendly query mode (boolean flag)
  --debug         : verbose prints from NER/keyword extraction (boolean flag)
  --search        : run web search + span matching
"""

import argparse
import logging
import sys

from qdd2.snippet_matcher import find_best_span_from_candidates_debug
from qdd2.translation import translate_ko_to_en
from qdd2.pipeline import build_queries_from_text
from qdd2.search_client import google_cse_search
from qdd2.trump_utils import detect_trump_context
from qdd2.rollcall_search import get_search_results, fetch_transcript_text
from datetime import datetime


# def run_qdd2(
#     text: str | None = None,
#     file_path: str | None = None,
#     quote: str | None = None,
#     date: str | None = None,
#     top_n: int = 15,
#     top_k: int = 3,
#     rollcall: bool = False,
#     debug: bool = False,
#     search: bool = False,
#     top_matches: int = 1,  # ★ 추가
# ):
#     def get_top_k_spans(
#         quote_en: str,
#         candidates: list[dict],
#         k: int,
#         num_before: int = 1,
#         num_after: int = 1,
#         min_score: float = 0.0,
#     ):
#         results = []
#         for c in candidates:
#             span = find_best_span_from_candidates_debug(
#                 quote_en=quote_en,
#                 candidates=[c],
#                 num_before=num_before,
#                 num_after=num_after,
#                 min_score=min_score,
#             )
#             if span:
#                 results.append(span)
#
#         results = sorted(results, key=lambda x: x.get("best_score", 0), reverse=True)
#         return results[:k]
#
#     """
#     QDD2 파이프라인을 Python 함수로 호출할 수 있게 한 엔트리포인트.
#
#     반환값 예시:
#     {
#         "pipeline_result": {...},          # build_queries_from_text 결과
#         "search_items": [ {...}, ... ],    # 검색 결과 아이템 (search=True일 때만)
#         "best_span": {...} or None,        # SBERT 기반 best span (search=True + 후보 있을 때만)
#     }
#     """
#     logging.basicConfig(
#         level=logging.DEBUG if debug else logging.INFO,
#         format="[%(levelname)s] %(message)s",
#     )
#     logger = logging.getLogger("qdd2.cli")
#
#     logger.info("[Step 0] Starting QDD2 pipeline (function mode)")
#
#     # 1) 텍스트 로딩
#     if text is not None:
#         loaded_text = text
#     elif file_path is not None:
#         try:
#             with open(file_path, "r", encoding="utf-8") as f:
#                 loaded_text = f.read()
#         except Exception as e:
#             raise RuntimeError(f"Failed to read file {file_path}: {e}")
#     else:
#         raise ValueError("Either `text` or `file_path` must be provided.")
#
#     logger.info("[Step 1] Loaded text (%d chars)", len(loaded_text))
#     if quote:
#         logger.info("Quote provided: %s", quote)
#     if date:
#         logger.info("Article date: %s", date)
#     logger.info(
#         "Args: top_n=%d, top_k=%d, rollcall=%s, debug=%s, search=%s",
#         top_n, top_k, rollcall, debug, search,
#     )
#
#     # 2) 파이프라인 호출
#     logger.info("[Step 2] Calling pipeline.build_queries_from_text()")
#     result = build_queries_from_text(
#         text=loaded_text,
#         top_n_keywords=top_n,
#         top_k_for_query=top_k,
#         quote_sentence=quote,
#         article_date=date,
#         rollcall_mode=rollcall,
#         device=0,  # CPU by default
#         debug=debug,
#     )
#     logger.info("[Step 3] Pipeline completed")
#     logger.info(
#         "Summary: entities=%d, keywords=%d, queries(ko=%s / en=%s)",
#         len(result.get("entities", [])),
#         len(result.get("keywords", [])),
#         bool(result.get("queries", {}).get("ko")),
#         bool(result.get("queries", {}).get("en")),
#     )
#     quote_text = quote or ""
#
#     # 3-A) NER 기반 트럼프 감지
#     is_trump_context = detect_trump_context(
#     article_text=loaded_text,
#     quote_text=quote,
#     pipeline_result=result,
# )
#
#     logger.info("Trump context detected: %s", is_trump_context)
#     search_items: list[dict] = []
#     best_span: dict | None = None
#     span_candidates: list[dict] = []
#
#     # ---------------------
#     # 4) 검색 + SBERT 매칭
#     # ---------------------
#     if search:
#         logger.info("[Step 4] Running search with generated query")
#
#         query = result["queries"].get("en") or result["queries"].get("ko")
#         if not query:
#             logger.warning("No query available to search.")
#         else:
#             # 4-A) Trump + rollcall → Rollcall JSON + transcript 본문 사용
#             if is_trump_context and rollcall:
#                 logger.info("[Search] Trump context + rollcall=True → using Rollcall JSON search")
#                 rollcall_links: list[str] = []
#                 try:
#                     rollcall_links = get_search_results(query, top_k=5)
#                 except Exception as e:
#                     logger.warning("Rollcall search failed, fallback to CSE: %s", e)
#
#                 logger.info("[Search] Rollcall raw links: %d", len(rollcall_links))
#
#                 # Rollcall 결과를 search_items로 래핑
#                 search_items = [
#                     {"link": url, "snippet": ""} for url in rollcall_links if url
#                 ]
#
#                 # Rollcall에서도 결과가 하나도 없으면 CSE fallback
#                 if not search_items:
#                     logger.info("[Search] No rollcall results, fallback to Google CSE")
#                     data = google_cse_search(query, num=20, debug=debug)
#                     search_items = data.get("items", []) or []
#
#             # 4-B) 그 외에는 CSE만 사용
#             else:
#                 logger.info("[Search] Using Google CSE (non-Trump context or rollcall=False)")
#                 data = google_cse_search(query, num=5, debug=debug)
#                 search_items = data.get("items", []) or []
#
#         if not search_items:
#             logger.warning("No results returned from search backends.")
#         else:
#             logger.info("[Search] Rollcall/CSE items: %d", len(search_items))
#             logger.info("[Step 5] Running SBERT snippet matching on search results")
#
#             # 1) 유사도 계산용 영어 기준 문장
#             quote_for_match_en: str | None = None
#
#             if quote_text:
#                 try:
#                     quote_for_match_en = translate_ko_to_en(quote_text)
#                 except Exception as e:
#                     logger.warning("Quote translation failed, fallback to EN query: %s", e)
#
#             if not quote_for_match_en:
#                 quote_for_match_en = result["queries"].get("en")
#
#             if quote_for_match_en:
#                 candidates: list[dict] = []
#
#                 # Trump + rollcall인 경우: transcript 본문을 후보 텍스트로 사용
#                 if is_trump_context and rollcall:
#                     for it in search_items:
#                         url = it.get("link")
#                         if not url:
#                             continue
#                         try:
#                             body = fetch_transcript_text(url)
#                         except Exception as e:
#                             logger.warning("Failed to fetch transcript text: %s", e)
#                             continue
#
#                         if not body:
#                             continue
#
#                         candidates.append(
#                             {
#                                 "url": url,
#                                 "snippet": body,
#                             }
#                         )
#                 else:
#                     # 일반 CSE: snippet 기반 후보
#                     for it in search_items:
#                         url = it.get("link")
#                         if not url:
#                             continue
#                         snippet = it.get("snippet", "") or ""
#                         if not snippet:
#                             continue
#                         candidates.append(
#                             {
#                                 "url": url,
#                                 "snippet": snippet,
#                             }
#                         )
#
#                 if candidates:
#                     try:
#                         top_spans = get_top_k_spans(
#                             quote_en=quote_for_match_en,
#                             candidates=candidates,
#                             k=top_matches,
#                             num_before=1,
#                             num_after=1,
#                             min_score=0.0,
#                         )
#                         best_span = top_spans[0] if top_spans else None
#                         if best_span:
#                             logger.info(
#                                 "[Step 6] Best span found: score=%.4f, url=%s",
#                                 best_span.get("best_score", -1.0),
#                                 best_span.get("url", ""),
#                             )
#                             span_candidates = best_span.get("top_k_candidates", []) or []
#                         else:
#                             logger.warning("No span passed the similarity threshold.")
#                     except Exception as e:
#                         logger.warning("SBERT snippet matching failed: %s", e)
#                 else:
#                     logger.warning("No candidate texts for similarity matching.")
#             else:
#                 logger.warning("No English text available for similarity matching.")
#
#     # 4) (옵션) 검색 + SBERT 기반 best span
#     search_items: list[dict] = []
#     best_span: dict | None = None
#     span_candidates: list[dict] = []  # ★ 추가: 후보 span 리스트

    # if search:
    #     logger.info("[Step 4] Running search with generated query")
    #
    #     # 쿼리는 EN → KO 우선 사용
    #     query = result["queries"].get("en") or result["queries"].get("ko")
    #
    #     if not query:
    #         logger.warning("No query available to search.")
    #     else:
    #         # 4-A) 트럼프 컨텍스트 + rollcall=True → Rollcall 우선, 실패 시 CSE
    #         if is_trump_context and rollcall:
    #             logger.info("[Search] Trump context + rollcall=True → using Rollcall Selenium search first")
    #             try:
    #                 rollcall_links = get_search_results(query, top_k=5)
    #                 logger.info("[Search] Rollcall links found: %d", len(search_items))
    #
    #             except Exception as e:
    #                 logger.warning("Rollcall search failed, fallback to CSE: %s", e)
    #                 rollcall_links = []
    #
    #             search_items = [
    #                 {"link": url, "snippet": ""}
    #                 for url in rollcall_links
    #                 if url
    #             ]
    #
    #             if not search_items:
    #                 logger.info("[Search] No rollcall results, fallback to Google CSE")
    #                 data = google_cse_search(query, num=20, debug=debug)
    #                 search_items = data.get("items", []) or []
    #
    #         # 4-B) 그 외에는 무조건 CSE 사용
    #         else:
    #             logger.info("[Search] Using Google CSE (non-Trump context or rollcall=False)")
    #             data = google_cse_search(query, num=5, debug=debug)
    #             search_items = data.get("items", []) or []
    #
    #     if not search_items:
    #         logger.warning("No results returned from search backends.")
    #     else:
    #         # --- 여기서부터 SBERT 유사도 기반 best span 계산 ---
    #         logger.info("[Step 5] Running SBERT snippet matching on search results")
    #
    #         # 1) 유사도 계산에 사용할 영어 문장 결정
    #         quote_for_match_en: str | None = None
    #
    #         if quote_text:
    #             try:
    #                 quote_for_match_en = translate_ko_to_en(quote_text)
    #             except Exception as e:
    #                 logger.warning("Quote translation failed, fallback to EN query: %s", e)
    #
    #         if not quote_for_match_en:
    #             # fallback: EN 쿼리 자체를 사용
    #             quote_for_match_en = result["queries"].get("en")
    #
    #         if quote_for_match_en:
    #             candidates = []
    #             for it in search_items:
    #                 url = it.get("link")
    #                 if not url:
    #                     continue
    #                 snippet = it.get("snippet", "") or ""
    #                 candidates.append(
    #                     {
    #                         "url": url,
    #                         "snippet": snippet,
    #                     }
    #                 )
    #
    #             if candidates:
    #                 try:
    #                     top_spans = get_top_k_spans(
    #                         quote_en=quote_for_match_en,
    #                         candidates=candidates,
    #                         k=top_matches,
    #                         num_before=1,
    #                         num_after=1,
    #                         min_score=0.2,
    #                     )
    #                     best_span = top_spans[0] if top_spans else None
    #                     if best_span:
    #                         logger.info(
    #                             "[Step 6] Best span found: score=%.4f, url=%s",
    #                             best_span.get("best_score", -1.0),
    #                             best_span.get("url", ""),
    #                         )
    #                         # ★ 추가: snippet_matcher에서 넣어준 후보 리스트 꺼내기
    #                         span_candidates = best_span.get("top_k_candidates", []) or []
    #                     else:
    #                         logger.warning("No span passed the similarity threshold.")
    #                 except Exception as e:
    #                     logger.warning("SBERT snippet matching failed: %s", e)
    #         else:
    #             logger.warning("No English text available for similarity matching.")
    #

def run_qdd2(
    text: str | None = None,
    file_path: str | None = None,
    quote: str | None = None,
    date: str | None = None,
    top_n: int = 15,
    top_k: int = 3,
    rollcall: bool = False,
    debug: bool = False,
    search: bool = False,
    top_matches: int = 1,
):
    """
    QDD2 파이프라인 엔트리포인트 (함수 버전).

    반환 예시:
    {
        "pipeline_result": {...},       # build_queries_from_text 결과
        "search_items": [ {...}, ... ], # 검색 결과
        "best_span": {...} or None,     # SBERT 기반 최종 span
        "span_candidates": [ {...}, ... ]  # top-k 후보들 (선택)
    }
    """
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="[%(levelname)s] %(message)s",
    )
    logger = logging.getLogger("qdd2.cli")

    logger.info("[Step 0] Starting QDD2 pipeline (function mode)")

    # 1) 텍스트 로딩
    if text is not None:
        loaded_text = text
    elif file_path is not None:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                loaded_text = f.read()
        except Exception as e:
            raise RuntimeError(f"Failed to read file {file_path}: {e}")
    else:
        raise ValueError("Either `text` or `file_path` must be provided.")

    logger.info("[Step 1] Loaded text (%d chars)", len(loaded_text))
    if quote:
        logger.info("Quote provided: %s", quote)
    if date:
        logger.info("Article date: %s", date)
    logger.info(
        "Args: top_n=%d, top_k=%d, rollcall=%s, debug=%s, search=%s, top_matches=%d",
        top_n, top_k, rollcall, debug, search, top_matches,
    )

    # 2) 쿼리 빌드
    logger.info("[Step 2] Calling pipeline.build_queries_from_text()")
    result = build_queries_from_text(
        text=loaded_text,
        top_n_keywords=top_n,
        top_k_for_query=top_k,
        quote_sentence=quote,
        article_date=date,
        rollcall_mode=rollcall,
        device=0,  # CPU
        debug=debug,
    )
    logger.info("[Step 3] Pipeline completed")
    logger.info(
        "Summary: entities=%d, keywords=%d, queries(ko=%s / en=%s)",
        len(result.get("entities", [])),
        len(result.get("keywords", [])),
        bool(result.get("queries", {}).get("ko")),
        bool(result.get("queries", {}).get("en")),
    )

    quote_text = quote or ""

    # 3) 트럼프 컨텍스트 감지
    is_trump_context = detect_trump_context(
        article_text=loaded_text,
        quote_text=quote,
        pipeline_result=result,
    )
    logger.info("Trump context detected: %s", is_trump_context)

    # 4) 검색 + SBERT span
    search_items: list[dict] = []
    best_span: dict | None = None
    span_candidates: list[dict] = []

    def get_top_k_spans(
        quote_en: str,
        candidates: list[dict],
        k: int,
        num_before: int = 1,
        num_after: int = 1,
        min_score: float = 0.1,   # 필요하면 0.15, 0.2 로 조정
    ) -> list[dict]:
        """
        snippet_matcher.find_best_span_from_candidates_debug 를 후보별로 돌려서
        top-k span dict 리스트를 반환.
        """
        results: list[dict] = []
        for c in candidates:
            from qdd2.snippet_matcher import find_best_span_from_candidates_debug

            span = find_best_span_from_candidates_debug(
                quote_en=quote_en,
                candidates=[c],
                num_before=num_before,
                num_after=num_after,
                min_score=min_score,
            )
            if span:
                results.append(span)

        results = sorted(results, key=lambda x: x.get("best_score", 0.0), reverse=True)
        return results[:k]

    if search:
        logger.info("[Step 4] Running search with generated query")

        queries = result.get("queries") or {}
        query = queries.get("en") or queries.get("ko")

        if not query:
            logger.warning("No query available to search.")
        else:
            # 4-A) Trump + rollcall=True → Rollcall JSON 우선
            if is_trump_context and rollcall:
                logger.info("[Search] Trump context + rollcall=True → using Rollcall JSON search")

                rollcall_links: list[str] = []
                try:
                    rollcall_links = get_search_results(query, top_k=5)
                except Exception as e:
                    logger.warning("Rollcall search failed, fallback to CSE: %s", e)

                logger.info("[Search] Rollcall raw links: %d", len(rollcall_links))

                # 🔹 기사 날짜에서 연도 뽑기
                target_year = None
                if date:
                    try:
                        # 네가 이미 쓰는 포맷에 맞게만 파싱
                        for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
                            try:
                                target_year = datetime.strptime(str(date).strip(), fmt).year
                                break
                            except ValueError:
                                continue
                    except Exception:
                        target_year = None
                # 🔹 연도가 있으면 slug에서 연도로 한 번 필터링
                filtered_links: list[str] = []
                if target_year:
                    year_token = f"-{target_year}/"
                    for url in rollcall_links:
                        if year_token in url:
                            filtered_links.append(url)

                    logger.info("[Search] Rollcall links filtered by year %s: %d",
                                target_year, len(filtered_links))

                # 🔹 연도로 필터했는데 아무것도 없으면 원본 그대로 사용
                effective_links = filtered_links if filtered_links else rollcall_links

                search_items = [{"link": url, "snippet": ""} for url in effective_links if url]

                if not search_items:
                    logger.info("[Search] No rollcall results, fallback to Google CSE")
                    data = google_cse_search(query, num=20, debug=debug)
                    search_items = data.get("items", []) or []
            else:
                # 4-B) 일반 CSE 검색
                logger.info("[Search] Using Google CSE (non-Trump context or rollcall=False)")
                data = google_cse_search(query, num=5, debug=debug)
                search_items = data.get("items", []) or []

        if not search_items:
            logger.warning("No results returned from search backends.")
        else:
            logger.info("[Search] Rollcall/CSE items: %d", len(search_items))
            logger.info("[Step 5] Running SBERT snippet matching on search results")

            # 1) 유사도 기준 문장 (영어)
            quote_for_match_en: str | None = None

            if quote_text:
                try:
                    quote_for_match_en = translate_ko_to_en(quote_text)
                except Exception as e:
                    logger.warning("Quote translation failed, fallback to EN query: %s", e)

            if not quote_for_match_en:
                quote_for_match_en = queries.get("en")

            if quote_for_match_en:
                candidates: list[dict] = []

                # Trump + rollcall → transcript 본문
                if is_trump_context and rollcall:
                    for it in search_items:
                        url = it.get("link")
                        if not url:
                            continue
                        try:
                            body = fetch_transcript_text(url)
                        except Exception as e:
                            logger.warning("Failed to fetch transcript text: %s", e)
                            continue
                        if not body:
                            continue
                        candidates.append(
                            {
                                "url": url,
                                "snippet": body,
                            }
                        )
                else:
                    # 일반 CSE → snippet 기반
                    for it in search_items:
                        url = it.get("link")
                        if not url:
                            continue
                        snippet = it.get("snippet", "") or ""
                        if not snippet:
                            continue
                        candidates.append(
                            {
                                "url": url,
                                "snippet": snippet,
                            }
                        )

                if candidates:
                    try:
                        top_spans = get_top_k_spans(
                            quote_en=quote_for_match_en,
                            candidates=candidates,
                            k=top_matches,
                            num_before=1,
                            num_after=1,
                            min_score=0.1,
                        )
                        if top_spans:
                            best_span = top_spans[0]
                            span_candidates = top_spans  # 필요하면 top_k 전체 넘김

                            logger.info(
                                "[Step 6] Best span found: score=%.4f, url=%s",
                                best_span.get("best_score", -1.0),
                                best_span.get("url", ""),
                            )
                        else:
                            logger.warning("No span passed the similarity threshold.")
                    except Exception as e:
                        logger.warning("SBERT snippet matching failed: %s", e)
                else:
                    logger.warning("No candidate texts for similarity matching.")
            else:
                logger.warning("No English text available for similarity matching.")

    # ★★★ 반드시 여기에서 한 번만 return ★★★
    return {
        "pipeline_result": result,
        "search_items": search_items,
        "best_span": best_span,
        "span_candidates": span_candidates,
    }

    # return {
    #     "pipeline_result": result,
    #     "search_items": search_items,
    #     "best_span": best_span,
    #     "span_candidates": span_candidates,  # ★ 추가
    #
    # }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="QDD2 extraction/query test runner")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--text", type=str, help="Inline text to process")
    src.add_argument("--file", type=str, help="Path to a UTF-8 text file to process")

    parser.add_argument("--quote", type=str, default=None, help="Specific quote sentence (optional)")
    parser.add_argument("--date", type=str, default=None, help="Article date YYYY-MM-DD")
    parser.add_argument("--top-n", type=int, default=15, help="Number of keywords to extract (default: 15)")
    parser.add_argument("--top-k", type=int, default=3, help="Keywords to include in query (default: 3)")
    parser.add_argument("--rollcall", action="store_true", help="Use rollcall.com-oriented query construction")
    parser.add_argument("--debug", action="store_true", help="Verbose debug logs")
    parser.add_argument("--search",action="store_true",help="Automatically run web search (Rollcall for Trump context, otherwise Google CSE)")
    parser.add_argument("--top-matches",type=int,default=1,help="Number of top similarity spans to return (default: 1)")

    return parser.parse_args()


def load_text(args: argparse.Namespace) -> str:
    if args.text:
        return args.text
    try:
        with open(args.file, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Failed to read file {args.file}: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    args = parse_args()

    out = run_qdd2(
        text=args.text,
        file_path=args.file,
        quote=args.quote,
        date=args.date,
        top_n=args.top_n,
        top_k=args.top_k,
        rollcall=args.rollcall,
        debug=args.debug,
        search=args.search,
        top_matches=args.top_matches,   # ★ 추가
    )

    result = out["pipeline_result"]
    items = out["search_items"]

    print("\n=== Entities by type ===")
    for label, words in result["entities_by_type"].items():
        print(f"{label}: {words}")

    print("\n=== Top keywords ===")
    for kw, score in result["keywords"]:
        print(f"{kw}  ({score:.4f})")

    print("\n=== Queries ===")
    print(f"KO: {result['queries']['ko']}")
    print(f"EN: {result['queries']['en']}")

    if args.search and items:
        print("\n=== Top search results ===")
        for item in items[:5]:
            print(f"- {item.get('title', '').strip()} :: {item.get('link', '')}")

    best_span = out.get("best_span")

    if args.search and out.get("top_spans"):
        print("\n=== Top SBERT similarity spans ===")
        for i, span in enumerate(out["top_spans"], 1):
            print(f"\n# {i}")
            print(f"URL        : {span.get('url', '')}")
            print(f"SCORE      : {span.get('best_score', -1.0):.4f}")
            print(f"SENTENCE   : {span.get('best_sentence', '')}")
            print(f"SPAN TEXT  : {span.get('span_text', '')}")


if __name__ == "__main__":
    main()
