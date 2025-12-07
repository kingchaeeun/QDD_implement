# test_single_article_qdd2.py

from main import run_qdd2
from qdd2.translation import translate_ko_to_en
from qdd2.text_utils import extract_quotes


def main():
    # 1) 여기다가 테스트할 기사 텍스트 / 날짜 넣기
    article_text = """
    트럼프 대통령은 "처음에는 (내전이) 미친 짓이고 통제 불가능한 일이라고 생각했다. 하지만 이 문제가 당신과 이 자리에 있는 많은 친구, 수단에 얼마나 중요한지 알게 됐다"며 수단 문제에 본격적으로 개입하겠다고 밝혔다.

그러면서 빈 살만 왕세자가 자신에게 "수단에서 끔찍한 일이 벌어지고 있다"며 개입을 요청했다고 설명했다.

트럼프 대통령은 이후 자신의 소셜미디어 트루스소셜에 "수단에서 엄청난 잔혹 행위가 벌어지고 있다"며 "수단은 지구상에서 가장 폭력적인 지역이자 동시에 매우 심각한 인도주의적 위기가 발생한 곳이다. 식량, 의료진 등 모든 것이 절실하다"는 글을 올렸다.
    """

    article_date = "2025-11-20"  # 네가 원하는 날짜로 셋팅

    # 2) 인용문 추출 (네가 쓰는 extract_quotes 그대로 사용)
    quotes_ko = extract_quotes(article_text) or []
    quotes_ko = list(dict.fromkeys(q for q in quotes_ko if q))  # 중복 제거

    print("[INFO] 추출된 인용문:")
    for q in quotes_ko:
        print(" -", q)

    if not quotes_ko:
        print("❌ 인용문이 추출되지 않음. 따옴표 형태 확인 필요.")
        return

    # 3) 기사/인용문 기준으로 '트럼프 문맥 여부' 판단 (네 build_dataset 코드와 동일 로직)
    article_lower = article_text.lower()
    is_trump_article = (
        "트럼프" in article_text
        or "도널드 트럼프" in article_text
        or "donald trump" in article_lower
        or "president trump" in article_lower
    )

    for quote_ko in quotes_ko:
        print("\n==============================")
        print("[QUOTE_KO]", quote_ko)

        quote_lower = str(quote_ko).lower()
        is_trump_quote = (
            "트럼프" in quote_ko
            or "도널드 트럼프" in quote_ko
            or "donald trump" in quote_lower
            or "president trump" in quote_lower
        )

        use_rollcall = True and (is_trump_article or is_trump_quote)
        print(f"[INFO] use_rollcall = {use_rollcall}")

        try:
            original_en = translate_ko_to_en(quote_ko)
        except Exception as e:
            print("[WARN] translate_ko_to_en 실패:", e)
            original_en = None

        print("[INFO] original_en:", original_en)

        # 4) 실제 run_qdd2 한 번 호출
        out = run_qdd2(
            text=article_text,
            file_path=None,
            quote=quote_ko,
            date=article_date,
            top_n=15,
            top_k=3,
            rollcall=True,
            debug=True,
            search=True,
            top_matches=3,
        )

        print("\n[INFO] run_qdd2 반환 key 목록:", list(out.keys()))

        best_span = out.get("best_span")
        span_candidates = out.get("span_candidates") or []

        import pprint

        print("\n[RESULT] best_span 딕셔너리 전체:")
        pprint.pp(best_span)

        print("\n[RESULT] span_candidates (상위 3개만 미리보기):")
        for i, cand in enumerate(span_candidates[:3], start=1):
            print(f"  [{i}] score={cand.get('best_score')} url={cand.get('url')}")

        print("\n[CHECK] source URL (best_span['url']):", (best_span or {}).get("url"))

if __name__ == "__main__":
    main()

