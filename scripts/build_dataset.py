"""
QDD2 Dataset Builder
====================

[파일 설명]
이 스크립트는 수집된 뉴스 기사(CSV)를 읽어들여 다음 작업을 수행합니다:
1. 기사 제목과 본문에서 '인용문(Quote)'을 추출
2. 한국어 인용문을 영어로 번역 (비교용)
3. QDD2 파이프라인(검색 + SBERT)을 실행하여 원문 출처(URL)와 원어 문장을 찾음
4. 결과를 정리하여 새로운 데이터셋(CSV)으로 저장
"""

import pandas as pd     # 데이터프레임 처리를 위한 라이브러리
from tqdm import tqdm   # 진행률 바(Progress Bar)를 보여주는 라이브러리

# QDD2 파이프라인 관련 모듈 임포트
from main import run_qdd2
from qdd2.translation import translate_ko_to_en
from qdd2.text_utils import extract_quotes


def build_dataset_from_articles(
    input_csv: str,
    text_col: str = "content",      # 기사 본문이 들어있는 컬럼명
    date_col: str = "date",         # 기사 날짜가 들어있는 컬럼명
    output_csv: str | None = None,  # 저장할 파일 경로
    span_top_k: int = 3,            # 하나의 인용문당 저장할 최대 원문 후보 개수 (Top 1~3)
    min_score: float | None = None,  # 최소 유사도 점수 (이 점수보다 낮으면 저장 안 함)
) -> pd.DataFrame:
    """
    기사 CSV를 순회하며 인용문 검증 데이터셋을 생성하는 메인 함수입니다.
    """

    # 1. 기사 데이터 로드
    df_articles = pd.read_csv(input_csv)
    print("기사 컬럼:", df_articles.columns.tolist())

    records = []    # 최종 결과를 모을 리스트
    gid = 0         # 인용문 고유 ID (Global ID)

    # 2. 각 기사별로 반복 (tqdm으로 진행상황 표시)
    for _, row in tqdm(df_articles.iterrows(), total=len(df_articles)):

        # 본문 데이터 확인 (비어있으면 건너뜀)
        article_text = row.get(text_col, "")
        if not isinstance(article_text, str) or not article_text.strip():
            continue

        # 날짜 정보 (검색 정확도를 위해 사용)
        article_date = row.get(date_col, None)

        # -------------------------------------------------------
        # [Step A] 인용문 추출 단계
        # 제목과 본문 모두에서 인용문을 뽑아냅니다.
        # -------------------------------------------------------
        quotes_ko: list[str] = []

        # 1) 헤드라인(제목)에서 추출
        title_text = row.get("title", "")
        if isinstance(title_text, str) and title_text.strip():
            title_quotes = extract_quotes(title_text) or []
            quotes_ko.extend(title_quotes)

        # 2) 본문에서 추출
        if isinstance(article_text, str) and article_text.strip():
            body_quotes = extract_quotes(article_text) or []
            quotes_ko.extend(body_quotes)

        # 3) 중복 제거 (순서 유지하면서 중복만 제거하는 파이썬 테크닉)
        quotes_ko = list(dict.fromkeys(q for q in quotes_ko if q))

        # 추출된 인용문이 없으면 다음 기사로 넘어감
        if not quotes_ko:
            continue

        # -------------------------------------------------------
        # [Step B] 각 인용문별 원문 검색 및 검증
        # -------------------------------------------------------
        for quote_ko in quotes_ko:
            gid += 1  # ID 부여

            # (참고용) 한국어 인용문 -> 영어 번역 (일명 '왜곡된 번역' 후보)
            try:
                original_en = translate_ko_to_en(quote_ko)
            except Exception:
                original_en = None

            # 파이프라인 실행
            try:
                out = run_qdd2(
                    text=article_text,  # 문맥 파악을 위한 기사 전문
                    file_path=None,
                    quote=quote_ko,     # 타겟 인용문
                    date=article_date,  # 기사 날짜
                    top_n=15,           # 키워드 추출 개수
                    top_k=3,            # 검색 쿼리용 키워드 개수
                    debug=False,
                    search=True,        # 웹 검색 활성화
                    top_matches=2,      # SBERT 유사도 상위 2개 후보 가져오기
                )
            except Exception as e:
                # 파이프라인 실행 중 에러가 나더라도 멈추지 않고 빈 값으로 기록
                records.append(
                    {
                        "id": gid,
                        "original": quote_ko,           # 원본(한국어)
                        "distorted": original_en,       # 번역본(영어)
                        "article_text": None,           # 찾은 원문(영어)
                        "origin_article_text": None,    # 원문 기사 스니펫
                        "similarity": None,             # 유사도 점수
                        "source_url": None,             # 출처 URL
                    }
                )
                continue

            # 결과에서 SBERT 매칭 후보 리스트 가져오기
            span_candidates = out.get("span_candidates") or []

            # (로그) 진행 상황 확인용
            print("span_candidates 개수:", len(span_candidates), " / quote:", quote_ko[:30])

            # ---------------------------------------------------
            # [Case 1] 상세 후보 리스트가 없는 경우 (Fallback)
            # 보통 검색은 됐는데 SBERT 점수가 애매하거나 하나만 리턴된 경우
            # ---------------------------------------------------
            if not span_candidates:
                best_span = out.get("best_span") or {}

                # 데이터 추출 (키 값이 없을 경우를 대비해 get 사용)
                source_quote_en = (
                    best_span.get("best_sentence")
                    or best_span.get("sentence")
                    or best_span.get("span_text")
                )
                article_span_en = (
                    best_span.get("span_text")
                    or best_span.get("sentence")
                )
                sim_score = (
                    best_span.get("best_score")
                    or best_span.get("score")
                )
                source_url = best_span.get("url")

                # 최소 점수(min_score)보다 낮으면 데이터셋에 넣지 않음 (품질 관리)
                if (min_score is not None) and (sim_score is not None) and (sim_score < min_score):
                    continue

                records.append(
                    {
                        "id": gid,
                        "original": quote_ko,
                        "distorted": original_en,
                        "article_text": source_quote_en,  # SBERT가 찾은 가장 유사한 문장
                        "origin_article_text": article_span_en,  # 검색 결과 스니펫(문맥)
                        "similarity": sim_score,
                        "source_url": source_url,
                    }
                )
                continue

            # ---------------------------------------------------
            # [Case 2] 상세 후보 리스트가 있는 경우 (Top K Loop)
            # 상위 K개의 후보를 모두 데이터셋에 저장
            # ---------------------------------------------------
            for rank, cand in enumerate(span_candidates[:span_top_k], start=1):
                source_quote_en = (
                    cand.get("best_sentence")
                    or cand.get("sentence")
                    or cand.get("span_text")
                )
                article_span_en = (
                    cand.get("span_text")
                    or cand.get("sentence")
                )
                sim_score = (
                    cand.get("best_score")
                    or cand.get("score")
                )
                source_url = cand.get("url")

                # 최소 점수 필터링
                if (min_score is not None) and (sim_score is not None) and (sim_score < min_score):
                    continue

                records.append(
                    {
                        "id": gid,
                        "original": quote_ko,
                        "distorted": original_en,
                        "article_text": source_quote_en,
                        "origin_article_text": article_span_en,
                        "similarity": sim_score,
                        "source_url": source_url,
                    }
                )
    # 3. 데이터프레임 변환 및 저장
    df_out = pd.DataFrame(records)

    if output_csv is not None:
        print(f"Saving dataset to {output_csv}...")
        df_out.to_csv(output_csv, index=False)
        print("Save completed.")

    return df_out

# 스크립트가 직접 실행될 때만 작동하는 블록
if __name__ == "__main__":
    # 입력/출력 파일 경로 설정
    INPUT_CSV = "articles.csv"       # 읽어올 기사 파일
    OUTPUT_CSV = "out_dataset.csv"   # 저장할 결과 파일
    TEXT_COL = "content"             # 본문 컬럼명
    DATE_COL = "date"

    # 함수 실행
    df = build_dataset_from_articles(
        input_csv=INPUT_CSV,
        text_col=TEXT_COL,
        date_col=DATE_COL,
        output_csv=OUTPUT_CSV,
        span_top_k=1,  # 각 인용문당 가장 점수 높은 1개만 저장
        min_score=0.4,  # 유사도 0.2 미만은 버림 (노이즈 제거)
    )

    print("=== 데이터 생성 완료 ===")
    print(df.head())    # 상위 5개 행 미리보기
    print(f"저장 경로: {OUTPUT_CSV}")