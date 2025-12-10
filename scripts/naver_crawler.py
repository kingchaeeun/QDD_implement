"""
Naver News 'World (104)' Section Crawler Module.

[파일 설명]
네이버 뉴스 '세계' 섹션(SID=104)의 기사 목록을 날짜별로 순회하며 수집합니다.
QDD2 프로젝트의 목적에 맞게 '인용문이 포함된 기사'만 선별적으로 저장합니다.

[주요 기능]
1. 날짜 범위 지정 (과거 -> 최신 역순 혹은 지정 범위)
2. 헤드라인(제목)에 직접 인용문(" ")이 있는 기사만 필터링
3. 국내 경제/부동산 관련 노이즈 데이터 제거
4. CSV 저장을 위한 DataFrame 반환

"""

import re
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple

import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urlparse, parse_qs

# -------------------------------------------------------------------
# 0. 전역 설정 (Global Settings)
# --------------------------------------------------------------------

BASE_URL = "https://news.naver.com"
WORLD_SID1 = "104"  # 네이버 뉴스 '세계' 섹션 ID
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36"
)

# 세션 설정 (헤더 재사용으로 차단 확률 낮춤)
session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})


def is_world_section_url(url: str) -> bool:
    """
    URL 파라미터를 분석하여 '세계(104)' 섹션 기사인지 확인합니다.
    다른 섹션(정치, 경제 등) 기사가 섞여 들어오는 것을 방지합니다.
    """
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    # 모바일(mnews)은 'sid', PC버전(main)은 'sid1' 파라미터를 사용함
    sid_vals = qs.get("sid") or qs.get("sid1")
    if not sid_vals:
        return False

    return sid_vals[0] == WORLD_SID1  # "104"


# -------------------------------------------------------------------
# 1. 텍스트 처리 유틸 함수 (Text Utilities)
# -------------------------------------------------------------------

def clean_text(text: Optional[str]) -> str:
    """
    기사 본문에서 불필요한 정보(기자 이메일, 저작권, 광고 등)를 정제합니다.
    """
    if not text:
        return ""

    text = re.sub(r"\([^)]+\)", "", text)  # 괄호와 그 안의 내용 제거 (예: (서울=연합뉴스))
    text = re.sub(r"\[[^\]]+\]", "", text)  # 대괄호와 그 안의 내용 제거 [ ... ]
    text = re.sub(r"\s{2,}", " ", text)  # 공백이 2개 이상이면 1개로 줄임
    text = re.sub(r"ⓒ.*?무단전재.*", "", text)  # 일반적인 저작권 문구 제거
    text = re.sub(r"▶.*", "", text)  # 하단 '클릭하세요' 류의 링크 텍스트 제거

    return text.strip()


def extract_date_ymd(raw_date: Optional[str]) -> str:
    """
    '2024.12.02. 오전 10:31' 같은 다양한 날짜 문자열에서
    '2024.12.02' 형태의 날짜만 깔끔하게 추출합니다.
    """
    if not raw_date:
        return ""

    # 정규표현식: 숫자4개(연) + 구분자 + 숫자2개(월) + 구분자 + 숫자2개(일)
    m = re.search(r"(\d{4})[.\-](\d{2})[.\-](\d{2})", raw_date)
    if m:
        yyyy, mm, dd = m.groups()
        return f"{yyyy}.{mm}.{dd}"
    return raw_date.strip()


def get_html(url: str, max_retry: int = 3, sleep: float = 0.5) -> Optional[str]:
    """
    URL에 요청을 보내 HTML을 가져옵니다.
    네이버 서버가 일시적으로 응답하지 않을 경우를 대비해 재시도(Retry) 로직을 포함합니다.
    """
    for _ in range(max_retry):
        try:
            resp = session.get(url, timeout=5)
            if resp.status_code == 200:
                return resp.text
        except Exception:
            time.sleep(sleep)
    return None


def has_direct_quote(text: str, min_chars: int = 3) -> bool:
    """
    문자열(주로 제목)에 직접 인용문(큰따옴표)이 포함되어 있는지 검사합니다.
    QDD2 데이터셋은 '누가 뭐라고 말했다'는 인용문 검증이 핵심이므로 중요합니다.
    """
    if not text:
        return False

    # 특수 따옴표들을 표준 큰따옴표(")로 통일
    normalized = (
        text.replace("“", '"')
            .replace("”", '"')
            .replace("«", '"')
            .replace("»", '"')
            .replace("「", '"')
            .replace("」", '"')
            .replace("『", '"')
            .replace("』", '"')
    )

    # 따옴표 안에 있는 내용물만 추출
    segments = re.findall(r'"([^"]+)"', normalized)

    for seg in segments:
        # 따옴표 안에 최소 3글자 이상의 의미 있는(한글/영어) 내용이 있어야 함
        meaningful_chars = re.findall(r"[가-힣A-Za-z]", seg)
        if len(meaningful_chars) >= min_chars:
            return True

    return False


# -------------------------------------------------------------------
# 2. 개별 기사 본문 수집 (Article Scraper)
# -------------------------------------------------------------------

def get_article_content(url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    기사 상세 페이지 URL로 접속하여 제목, 날짜, 본문을 가져옵니다.
    """
    try:
        html = get_html(url)
        if not html:
            return None, None, None

        soup = BeautifulSoup(html, "html.parser")

        # 1) 제목 추출 (네이버 뉴스 구조에 따른 선택자
        title = None
        title_area = soup.find(id="title_area")
        if title_area:
            h2 = title_area.find("h2")
            title = (h2 or title_area).get_text(strip=True)
        else:
            h2 = soup.find("h2")
            if h2:
                title = h2.get_text(strip=True)

        # 2) 날짜 추출
        date_tag = (
            soup.select_one(".media_end_head_info_datestamp_time")
            or soup.select_one("span.t11")
            or soup.select_one(".article_info .date")
        )
        raw_date = date_tag.get_text(strip=True) if date_tag else None
        date_str = extract_date_ymd(raw_date)

        # 3) 본문 추출 및 정제
        content_tag = soup.find(id="dic_area") or soup.find("article")
        content = clean_text(content_tag.get_text()) if content_tag else None

        if not title or not content:
            return None, None, None

        return title, date_str, content

    except Exception:
        return None, None, None


# -------------------------------------------------------------------
# 3. 필터링 로직 (Filter Condition)
# -------------------------------------------------------------------

def check_conditions(title: str, content: str) -> bool:
    """
    수집된 기사를 저장할지 말지 결정하는 필터입니다.
    1. 제목에 인용문이 있어야 함
    2. 국내 이슈(부동산, 국내경제)는 제외함
    """
    if not title or not content:
        return False

    # 조건 1) 제목에 직접 인용문(큰따옴표) 존재 여부
    if not has_direct_quote(title):
        return False

    # 조건 2) 세계 뉴스에 섞여 들어온 국내 경제/부동산 키워드 제외
    exclude_keywords = [
        "부동산", "아파트", "전세", "월세", "청약", "분양",
        "재건축", "국토부", "LH", "집값", "공시가격",
        "코스피", "코스닥", "한국은행", "금융위", "금감원",
        "국내 경제", "우리나라 경제", "한국 경제", "전경련",
    ]

    full_text = f"{title} {content}"
    for kw in exclude_keywords:
        if kw in full_text:
            return False

    return True


# -------------------------------------------------------------------
# 4. 크롤러 메인 파이프라인 (Crawler Main)
# -------------------------------------------------------------------

def crawl_world_articles(
    num_articles: int = 100,            # 수집 목표 개수
    days_back: int = 90,                # 며칠 전까지 검색할지 (날짜 지정 안 했을 때)
    start_date: Optional[str] = None,   # 시작 날짜 (YYYY-MM-DD)
    end_date: Optional[str] = None,     # 종료 날짜 (YYYY-MM-DD)
) -> pd.DataFrame:
    """
    세계(104) 섹션을 순회하며 조건에 맞는 기사를 수집합니다.
    """
    data = {"category": [], "title": [], "date": [], "content": [], "url": []}
    collected_count = 0
    visited: set[str] = set()   # 중복 수집 방지용 방문 기록

    print(">>> 기사 수집 시작 (세계 섹션, 헤드라인 직접 인용문 필터)...")

    # [Step 1] 탐색할 날짜 리스트 생성
    date_list: list[str] = []
    allowed_start_dt: Optional[datetime] = None
    allowed_end_dt: Optional[datetime] = None

    if start_date and end_date:
        # 사용자가 날짜 범위를 직접 지정한 경우
        start_norm = start_date.replace("-", "")
        end_norm = end_date.replace("-", "")

        try:
            start_dt = datetime.strptime(start_norm, "%Y%m%d")
            end_dt = datetime.strptime(end_norm, "%Y%m%d")
        except ValueError:
            print("[ERROR] 날짜 포맷 오류. YYYYMMDD 또는 YYYY-MM-DD 형식이어야 합니다.")
            return pd.DataFrame(data)

        # start_dt를 '최신 날짜', end_dt를 '과거 날짜'로 정렬 (네이버 뉴스는 최신->과거 순 탐색이 유리)
        if start_dt < end_dt:
            start_dt, end_dt = end_dt, start_dt

        allowed_start_dt = end_dt   # 범위의 가장 과거
        allowed_end_dt = start_dt   # 범위의 가장 최신

        # 최신 날짜부터 과거 날짜로 리스트 생성
        n_days = (start_dt - end_dt).days
        for i in range(n_days + 1):
            day = start_dt - timedelta(days=i)
            date_list.append(day.strftime("%Y%m%d"))

    else:
        # 날짜 지정이 없으면 오늘부터 days_back 만큼 과거로
        today = datetime.today()
        allowed_end_dt = today
        allowed_start_dt = today - timedelta(days=days_back - 1)

        for d in range(days_back):
            date = today - timedelta(days=d)
            date_list.append(date.strftime("%Y%m%d"))

    # [Step 2] 날짜별 -> 페이지별 순회
    for date_str in date_list:
        if collected_count >= num_articles:
            break

        page = 1

        while True:
            # 목표량 채웠으면 전체 종료
            if collected_count >= num_articles:
                break

            # 네이버 뉴스 리스트 URL 생성
            list_url = (
                f"{BASE_URL}/main/list.naver"
                f"?mode=LSD&mid=shm&sid1={WORLD_SID1}"
                f"&date={date_str}&page={page}"
            )

            html = get_html(list_url)
            if not html:
                break

            soup = BeautifulSoup(html, "html.parser")

            # 기사 링크 태그 추출
            a_tags = soup.select("a[href*='/mnews/article/'], a[href*='/read.naver']")

            # 링크가 하나도 없으면 해당 날짜의 페이지 끝에 도달한 것
            if not a_tags:
                break

            # 이 페이지에서 '실제로 수집된' 개수가 0개여도,
            # 다음 페이지에는 유효한 기사가 있을 수 있으므로 new_on_page 변수로 break 하지 않음.
            # 대신 중복 체크 로직을 강화하여 페이지 끝을 감지해야 함.
            duplicate_count = 0 # 이 페이지의 기사가 모두 이미 본 거라면 종료

            for a in a_tags:
                href = a.get("href")
                if not href: continue
                if href.startswith("/"):
                    href = BASE_URL + href

                if not is_world_section_url(href):
                    continue

                # 이미 수집했거나 확인한 URL이면 건너뜀
                if href in visited:
                    duplicate_count += 1
                    continue
                visited.add(href)

                # 기사 내용 가져오기
                title, art_date, content = get_article_content(href)

                # 날짜 범위 체크 (리스트 날짜와 실제 기사 날짜가 다를 수 있음)
                if not art_date:
                    continue

                m = re.search(r"(\d{4})[.\-](\d{2})[.\-](\d{2})", art_date)
                if not m:
                    continue
                yyyy, mm, dd = m.groups()
                try:
                    art_dt = datetime(int(yyyy), int(mm), int(dd))
                except ValueError:
                    continue

                if allowed_start_dt and allowed_end_dt:
                    if not (allowed_start_dt <= art_dt <= allowed_end_dt):
                        continue

                # 필터 조건 확인 (인용문 제목 등)
                if title and content and check_conditions(title, content):
                    data["category"].append("세계")
                    data["title"].append(title)
                    data["date"].append(art_date)
                    data["content"].append(content)
                    data["url"].append(href)

                    collected_count += 1

                    print(
                        f"[{collected_count}/{num_articles}] 저장 | "
                        f"{art_date} | {title[:40]}..."
                    )

                    if collected_count >= num_articles:
                        break

                # 서버 부하 방지
                time.sleep(0.05)

            # 네이버는 페이지 끝을 넘어가면 이전 페이지 내용을 반복해서 보여주는 경우가 있음
            # 만약 이 페이지의 모든 링크가 이미 visited에 있다면 더 볼 필요 없음
            if duplicate_count == len(a_tags):
                # print(f"   [{date_str}] {page}페이지: 모든 기사가 중복. 날짜 탐색 종료.")
                break

            page += 1
            time.sleep(0.1)

        print(f"   [{date_str}] 탐색 완료. 누적 수집: {collected_count}개")

    print(f"\n>>> 최종 수집 완료: {len(df)}개")
    return pd.DataFrame(data)



# -------------------------------------------------------------------
# 5. 실행부 (CLI 테스트)
# -------------------------------------------------------------------

if __name__ == "__main__":
    df = crawl_world_articles(
        num_articles=50,        # 50개 모으면 종료
        start_date="2025-8-13", # 시작일 (최신)
        end_date="2025-8-7",    # 종료일 (과거)
    )

    if not df.empty:
        filename = "articles.csv"
        # 엑셀에서 한글 깨짐 방지를 위해 utf-8-sig 인코딩 사용
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"\n파일 저장 완료: {filename}")
        print(df[["date", "title"]].head())
    else:
        print("\n조건에 맞는 데이터가 없습니다.")
