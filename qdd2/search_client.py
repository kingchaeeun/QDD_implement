"""
Google CSE client and page/PDF helpers.
(구글 검색 엔진 클라이언트 및 웹페이지/PDF 처리 도구)

이 모듈은 다음 두 가지 핵심 역할을 수행합니다:
1. Google Custom Search JSON API를 사용하여 웹 검색을 수행합니다.
2. 검색된 URL(HTML 또는 PDF)에 접속하여 본문 텍스트를 추출합니다.
"""

import os
import random
import re
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin
from io import BytesIO

import pdfplumber   # PDF 텍스트 추출 라이브러리
import requests

from qdd2 import config
from qdd2.text_utils import contains_korean

# 전역 세션 설정 (HTTP 연결 재사용으로 속도 향상)
SESSION = requests.Session()
SESSION.headers.update(config.HTTP_HEADERS)


def is_valid_page(url: str, timeout: int = config.DEFAULT_TIMEOUT) -> bool:
    """
    [유효성 검사]
    해당 URL이 접속 가능하고, 내용이 충분한 HTML 페이지인지 확인합니다.
    (PDF나 바이너리 파일, 빈 페이지 등을 1차로 걸러냄)
    """
    try:
        # head 요청 대신 get을 쓰되, 내용은 나중에 확인함
        r = SESSION.get(url, timeout=timeout, allow_redirects=True)
        if r.status_code != 200:
            return False

        # Content-Type 확인 (HTML인지)
        content_type = (r.headers.get("Content-Type") or "").lower()
        if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
            return False

        # 본문 길이 확인 (너무 짧으면 에러 페이지일 가능성 높음)
        return len((r.text or "").strip()) > config.HTML_MIN_LENGTH
    except requests.RequestException:
        return False


def google_cse_search(
    q: str,
    num: int = 10,
    start: int = 1,
    lr: Optional[str] = None,
    hl: str = "en",
    gl: str = "us",
    safe: Optional[str] = None,
    retries: int = 3,
    backoff: float = 1.4,
    debug: bool = False,
):
    """
    [구글 검색 API 호출]
    Google Custom Search API를 호출하여 검색 결과를 가져옵니다.
    네트워크 오류 발생 시, 지수 백오프(Exponential Backoff)를 사용하여 재시도합니다.

    Args:
        q: 검색어
        num: 가져올 결과 개수 (1~10)
        start: 시작 인덱스 (페이지네이션 용)
        retries: 실패 시 재시도 횟수
    """
    # 1. API 키 및 검색 엔진 ID(CX) 로드
    # 환경 변수에서 우선적으로 가져오고, 없으면 config 파일의 값을 사용
    api_key = os.getenv(config.GOOGLE_API_KEY_ENV) or (
        config.GOOGLE_API_KEY_ENV if config.GOOGLE_API_KEY_ENV and len(config.GOOGLE_API_KEY_ENV) > 20 else None
    )
    cse_cx = os.getenv(config.GOOGLE_CSE_CX_ENV) or (
        config.GOOGLE_CSE_CX_ENV if config.GOOGLE_CSE_CX_ENV and len(config.GOOGLE_CSE_CX_ENV) > 5 else None
    )

    # 키가 없으면 검색을 할 수 없으므로 강제 종료
    assert api_key and cse_cx, "Set GOOGLE_API_KEY and GOOGLE_CSE_CX environment variables (or populate config values)"

    params = {
        "key": api_key,
        "cx": cse_cx,
        "q": q,
        "num": max(1, min(10, int(num))), # API 제한: 1회 최대 10개
        "start": max(1, min(91, int(start))), # API 제한: 최대 100개까지만 조회 가능
        "hl": hl, # 인터페이스 언어 (Host Language)
        "gl": gl, # 지역 설정 (Geo Location)
    }
    if lr:
        params["lr"] = lr   # 언어 제한 (Language Restrict)
    if safe in ("active", "off"):
        params["safe"] = safe

    url = "https://www.googleapis.com/customsearch/v1"

    # 2. 재시도 로직 (Retry Loop)
    for attempt in range(retries):
        try:
            resp = SESSION.get(url, params=params, timeout=config.DEFAULT_TIMEOUT)
            if debug:
                print(f"[DEBUG] CSE attempt {attempt + 1}: {resp.status_code} -> {resp.url}")

            if resp.status_code == 200:
                return resp.json()

            # 429(Too Many Requests)나 5xx 서버 에러 시 잠시 대기 후 재시도
            if resp.status_code in (429, 500, 502, 503, 504):
                sleep_s = (backoff ** attempt) + random.uniform(0, 0.25)
                time.sleep(sleep_s)
                continue

            # 400, 403 등 재시도해도 안 될 에러는 바로 예외 발생
            resp.raise_for_status()

        except requests.RequestException:
            # 네트워크 연결 에러 등
            sleep_s = (backoff ** attempt) + random.uniform(0, 0.25)
            time.sleep(sleep_s)
            continue

    # 모든 재시도 실패 시 빈 결과 반환
    return {"items": []}


def collect_candidates_google_cse(
    query: str,
    top_per_domain: int = 3,
    use_siteSearch: bool = True,  # 하위 호환성 유지용 (현재 로직에서는 항상 True처럼 동작)
    safe: Optional[str] = None,
    domain_list: Optional[List[str]] = None,
    debug: bool = False,
) -> List[Dict]:
    """
    [도메인별 검색 수행]
    지정된 신뢰할 수 있는 도메인(UN, 백악관 등) 목록을 순회하며 검색을 수행합니다.
    검색어 예시: "Trump Venezuela site:un.org"
    """
    candidates: List[Dict] = []
    seen = set()    # 중복 URL 방지

    # 검색어에 한글이 포함되어 있으면 한국어/한국 설정으로 변경
    is_ko = contains_korean(query)
    lr = "lang_ko" if is_ko else None
    hl = "ko" if is_ko else "en"
    gl = "kr" if is_ko else "us"

    # 검색할 도메인 목록 (인자로 안 들어오면 config 기본값 사용)
    domains = domain_list if domain_list is not None else config.BASE_DOMAINS

    for site_filter in domains:
        # site:un.org 같은 검색 연산자를 쿼리에 추가
        sub_query = f"{query} {site_filter}"
        remaining = top_per_domain
        start = 1

        while remaining > 0:
            per_req = min(10, remaining)
            data = google_cse_search(
                q=sub_query,
                num=per_req,
                start=start,
                lr=lr,
                hl=hl,
                gl=gl,
                safe=safe,
                debug=debug,
            )
            items = data.get("items", []) or []
            if not items:
                break

            for it in items:
                # 링크 또는 포맷된 URL 가져오기
                url = it.get("link") or it.get("formattedUrl")

                # 중복이거나 유효하지 않은 페이지 스킵
                if not url or url in seen:
                    continue
                if not is_valid_page(url):
                    continue

                candidates.append(
                    {
                        "domain": site_filter.replace("site:", ""),
                        "title": it.get("title", ""),
                        "url": url,
                        "snippet": it.get("snippet", ""),
                    }
                )
                seen.add(url)
                remaining -= 1
                if remaining == 0:
                    break

            # 다음 페이지 검색을 위한 인덱스 증가
            start += per_req
            if start > 91:  # 구글 API 상한선
                break
            time.sleep(0.2) # 과도한 요청 방지 딜레이

    return candidates


def html_to_text(html: str) -> str:
    """
    [HTML 정제]
    BeautifulSoup을 사용하여 HTML 태그, 스크립트, 스타일을 제거하고 순수 텍스트만 추출합니다.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")

    # 불필요한 태그 제거
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(" ")  # 태그 사이를 공백으로 구분
    text = re.sub(r"\s+", " ", text)  # 다중 공백을 하나로 축소
    return text.strip()


def extract_pdf_url_from_html(html: str, base_url: str) -> Optional[str]:
    """
    [HTML 내 PDF 링크 찾기]
    페이지가 PDF를 iframe으로 띄우거나 다운로드 링크를 제공하는 경우, 해당 PDF URL을 찾아냅니다.
    (UN 문서 페이지 같은 곳에서 유용함)
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")

    # 1. iframe 태그 확인
    iframe = soup.find("iframe")
    if iframe and iframe.get("src"):
        src = iframe["src"]
        if ".pdf" in src.lower():
            return urljoin(base_url, src)

    # 2. a 태그(링크) 확인
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if ".pdf" in href.lower():
            return urljoin(base_url, href)

    return None


def extract_text_from_pdf_url(pdf_url: str) -> Optional[str]:
    """
    [PDF 다운로드 및 텍스트 변환]
    URL에서 PDF를 다운로드하고, pdfplumber를 이용해 텍스트를 추출합니다.
    """
    try:
        r = SESSION.get(pdf_url, timeout=config.PDF_TIMEOUT)
        if r.status_code != 200:
            print(f"[WARN] PDF request failed: {pdf_url}, status={r.status_code}")
            return None
    except Exception as e:
        print(f"[WARN] PDF request error: {pdf_url}, {e}")
        return None

    # 메모리 상에서 파일 열기 (디스크 저장 안 함)
    pdf_file = BytesIO(r.content)
    text_chunks: List[str] = []

    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text_chunks.append(page_text)
    except Exception as e:
        print(f"[WARN] PDF parsing error: {pdf_url}, {e}")
        return None

    text = "\n".join(text_chunks)
    text = re.sub(r"\s+", " ", text)    # 공백 정리

    # 인코딩 안전 장치
    try:
        text = bytes(text, "utf-8").decode("utf-8", "ignore")
    except Exception:
        pass

    return text.strip() or None
