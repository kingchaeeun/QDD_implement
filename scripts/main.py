"""
Example CLI runner for the qdd2 pipeline.

[파일 설명]
이 파일은 QDD2(Quote Disinformation Detection) 파이프라인의
명령줄 인터페이스(CLI) 실행 예제입니다.
핵심 로직은 run_qdd2 함수에 있으며, 인라인 텍스트나 파일 경로를 받아
인용문 출처를 검색하고 SBERT를 이용한 유사도 매칭을 수행합니다.

Usage:
  python main.py --text '트럼프 "베네수엘라 상공 전면폐쇄"' --date 2024-11-29

Flags:
  --text / --file : 입력 텍스트 (둘 중 하나 필수)
  --quote         : 특정 인용문 (선택 사항)
  --date          : 기사 날짜 YYYY-MM-DD (선택 사항)
  --debug         : 상세 로그 출력 여부 (boolean flag)
  --search        : 웹 검색 및 스팬 매칭 실행 여부
  --top-matches   : SBERT 매칭 후 반환할 최종 후보 개수
"""

import argparse # 명령줄 인수를 처리하는 표준 라이브러리 모듈
import logging # 로그 메시지를 기록하는 모듈
import sys # 시스템 관련 파라미터 및 함수를 제공하는 모듈 (예외 시 종료 등)

# QDD2 파이프라인 내부 모듈 임포트
from qdd2.snippet_matcher import find_best_span_from_candidates_debug # SBERT 기반 스니펫 유사도 매칭 함수
from qdd2.translation import translate_ko_to_en # 한국어 -> 영어 번역 함수
from qdd2.pipeline import build_queries_from_text # NER/키워드 추출 및 검색 쿼리 빌드 함수
from qdd2.search_client import google_cse_search # Google Custom Search Engine (CSE) 클라이언트


def run_qdd2(
    text: str | None = None, # 인라인 입력 텍스트. Python 3.10+의 유니언 타입 힌트 (str 또는 None)
    file_path: str | None = None, # 파일 경로 (str 또는 None)
    quote: str | None = None, # 특정 인용문
    date: str | None = None, # 기사 날짜 (YYYY-MM-DD 포맷)
    debug: bool = False, # 상세 로그 출력 여부
    search: bool = False, # 웹 검색 수행 여부
    top_matches: int = 1, # SBERT 매칭 후 반환할 최종 후보 개수
):
    """
    QDD2 파이프라인 엔트리포인트 (함수 버전).

    텍스트를 분석하여 엔티티/키워드를 추출하고, 검색 쿼리를 생성하며,
    필요 시 웹 검색과 SBERT 유사도 매칭을 수행합니다.

    [반환 값]
    {
        "pipeline_result": {...},       # build_queries_from_text 결과 (엔티티, 키워드, 쿼리 포함)
        "search_items": [ {...}, ... ], # 웹 검색 결과 리스트 (link, snippet 등 포함)
        "best_span": {...} or None,     # SBERT 기반 최고 점수 매칭 스팬
        "span_candidates": [ {...}, ... ]  # top-k 스팬 후보 리스트
    }
    """

    # 1. 로깅 설정: debug 플래그에 따라 로깅 레벨을 DEBUG/INFO로 설정
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="[%(levelname)s] %(message)s",   # 로그 레벨과 메시지만 출력하는 간단한 포맷
    )
    logger = logging.getLogger("qdd2.cli")  # 로거 인스턴스 생성

    logger.info("[Step 0] Starting QDD2 pipeline (function mode)")

    # 1) 텍스트 로딩: text 또는 file_path 중 하나를 사용
    if text is not None:
        loaded_text = text
    elif file_path is not None:
        # 파일 경로가 주어지면 파일에서 텍스트를 읽어옴
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                loaded_text = f.read()
        except Exception as e:
            raise RuntimeError(f"Failed to read file {file_path}: {e}")
    else:
        # text와 file_path 모두 없으면 오류 발생 (상호 배타적 그룹 설정과 일치)
        raise ValueError("Either `text` or `file_path` must be provided.")

    logger.info("[Step 1] Loaded text (%d chars)", len(loaded_text))
    if quote:
        logger.info("Quote provided: %s", quote)
    if date:
        logger.info("Article date: %s", date)

    # 전달받은 파라미터 로깅
    logger.info(
        "Args: top_n=%d, top_k=%d, debug=%s, search=%s, top_matches=%d",
        debug, search, top_matches,
    )

    # 2) 쿼리 빌드
    logger.info("[Step 2] Calling pipeline.build_queries_from_text()")
    # build_queries_from_text를 호출하여 NER, 키워드 추출, 검색 쿼리를 생성함
    result = build_queries_from_text(
        text=loaded_text,
        quote_sentence=quote,
        article_date=date,
        device=0,  # CPU
        debug=debug,
    )
    logger.info("[Step 3] Pipeline completed")
    # 분석 결과 요약 출력
    logger.info(
        "Summary: entities=%d, keywords=%d, queries(ko=%s / en=%s)",
        len(result.get("entities", [])),
        len(result.get("keywords", [])),
        bool(result.get("queries", {}).get("ko")),
        bool(result.get("queries", {}).get("en")),
    )

    quote_text = quote or ""


    # 결과 담을 변수 초기화
    search_items: list[dict] = []
    best_span: dict | None = None
    span_candidates: list[dict] = []

    # -------------------------------------------------------
    # [Helper Function] SBERT 매칭 헬퍼 함수
    # -------------------------------------------------------
    def get_top_k_spans(
        quote_en: str,
        candidates: list[dict],
        k: int,
        num_before: int = 1,
        num_after: int = 1,
        min_score: float = 0.1,   # 유사도 임계값
    ) -> list[dict]:
        """
        검색된 후보군(candidates) 각각에 대해 SBERT 유사도 검사를 수행하고,
        점수가 높은 순서대로 k개의 결과를 반환합니다.
        """
        results: list[dict] = []
        for c in candidates:
            # 개별 후보에 대해 가장 매칭이 잘 되는 부분(Span) 찾기
            span = find_best_span_from_candidates_debug(
                quote_en=quote_en,
                candidates=[c],
                num_before=num_before,
                num_after=num_after,
                min_score=min_score,
            )
            if span:
                results.append(span)
        # 유사도 점수(best_score) 기준으로 내림차순 정렬
        results = sorted(results, key=lambda x: x.get("best_score", 0.0), reverse=True)
        return results[:k]

    # -------------------------------------------------------
    # 3) 검색 및 SBERT 매칭 실행 (Search Flag가 True일 때만)
    # -------------------------------------------------------
    if search:
        logger.info("[Step 4] Running search with generated query")

        queries = result.get("queries") or {}
        # 영어 쿼리 우선, 없으면 한국어 쿼리 사용
        query = queries.get("en") or queries.get("ko")

        if not query:
            logger.warning("No query available to search.")
        else:
            logger.info("[Search] Using Google CSE")
            # Google CSE API 호출 (최대 5개 결과)
            data = google_cse_search(query, num=5, debug=debug)
            search_items = data.get("items", []) or []

        if not search_items:
            logger.warning("No results returned from search backends")
        else:
            logger.info("[Search] CSE items: %d", len(search_items))
            logger.info("[Step 5] Running SBERT snippet matching on search results")

            # --- SBERT 매칭 준비 ---
            # 비교 기준이 될 문장(Anchor)을 설정 (번역된 인용문 또는 영어 쿼리)
            quote_for_match_en: str | None = None

            if quote_text:
                try:
                    # 한국어 인용문이 있다면 영어로 번역하여 매칭 정확도 향상 시도
                    quote_for_match_en = translate_ko_to_en(quote_text)
                except Exception as e:
                    logger.warning("Quote translation failed, fallback to EN query: %s", e)

            # 번역 실패하거나 인용문이 없으면 생성된 영어 쿼리를 기준 문장으로 사용
            if not quote_for_match_en:
                quote_for_match_en = queries.get("en")

            # --- 매칭 실행 ---
            if quote_for_match_en:
                candidates: list[dict] = []

                # 검색 결과(Item)들을 매칭 후보(Candidate) 형식으로 변환
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
                            "snippet": snippet,  # CSE 결과의 요약문(snippet)을 분석 대상으로 함
                        }
                    )

                if candidates:
                    try:
                        # 위에서 정의한 헬퍼 함수로 상위 k개 유사도 결과 추출
                        top_spans = get_top_k_spans(
                            quote_en=quote_for_match_en,
                            candidates=candidates,
                            k=top_matches,
                            num_before=1,
                            num_after=1,
                            min_score=0.1,  # 유사도 0.1 이상만
                        )
                        if top_spans:
                            best_span = top_spans[0]    # 가장 점수 높은 1개 (대표 결과)
                            span_candidates = top_spans  # 상위 k개 리스트

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

    # 최종 결과 반환
    return {
        "pipeline_result": result,  # 키워드 및 쿼리 생성 결과
        "search_items": search_items,  # 구글 검색 결과 리스트
        "best_span": best_span,  # 가장 유사한 단일 결과
        "span_candidates": span_candidates,  # 상위 유사도 결과 리스트
    }


def parse_args() -> argparse.Namespace:
    """CLI 인자 파싱 설정"""
    parser = argparse.ArgumentParser(description="QDD2 extraction/query test runner")

    # 텍스트와 파일 중 하나는 반드시 입력해야 하며, 둘 다 입력할 수는 없음 (상호 배타적)
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--text", type=str, help="Inline text to process")
    src.add_argument("--file", type=str, help="Path to a UTF-8 text file to process")

    # 선택적 인자들
    parser.add_argument("--quote", type=str, default=None, help="Specific quote sentence (optional)")
    parser.add_argument("--date", type=str, default=None, help="Article date YYYY-MM-DD")
    parser.add_argument("--top-n", type=int, default=15, help="Number of keywords to extract (default: 15)")
    parser.add_argument("--top-k", type=int, default=3, help="Keywords to include in query (default: 3)")
    parser.add_argument("--debug", action="store_true", help="Verbose debug logs")
    parser.add_argument("--search",action="store_true",help="Automatically run web search")
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
    """메인 실행 함수"""
    args = parse_args()

    # 파이프라인 실행 및 결과 수신
    out = run_qdd2(
        text=args.text,
        file_path=args.file,
        quote=args.quote,
        date=args.date,
        debug=args.debug,
        search=args.search,
        top_matches=args.top_matches,
    )

    result = out["pipeline_result"]
    items = out["search_items"]

    # --- 결과 출력 (터미널용) ---
    print("\n=== Entities by type ===")
    for label, words in result["entities_by_type"].items():
        print(f"{label}: {words}")

    print("\n=== Queries ===")
    print(f"KO: {result['queries']['ko']}")
    print(f"EN: {result['queries']['en']}")

    if args.search and items:
        print("\n=== Top search results ===")
        for item in items[:5]:
            print(f"- {item.get('title', '').strip()} :: {item.get('link', '')}")

    if args.search and out.get("span_candidates"):
        print("\n=== Top SBERT similarity spans ===")
        for i, span in enumerate(out["span_candidates"], 1):
            print(f"\n# {i}")
            print(f"URL        : {span.get('url', '')}")
            print(f"SCORE      : {span.get('best_score', -1.0):.4f}")
            print(f"SENTENCE   : {span.get('best_sentence', '')}")
            print(f"SPAN TEXT  : {span.get('span_text', '')}")


if __name__ == "__main__":
    main()
