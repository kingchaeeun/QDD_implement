"""
Central configuration and constants.
(중앙 설정 및 상수 정의 모듈)

모델의 이름, API 키, 타임아웃 설정 등 프로젝트 전반에서 쓰이는
'값'들을 한곳에서 관리하여 유지보수를 쉽게 합니다.
"""

# --------------------------------------------------------
# 1. 모델 식별자 (Model Identifiers)
# --------------------------------------------------------

# 한국어 개체명 인식(NER) 모델 (KoELECTRA 기반)
# 인물(PER), 장소(LOC) 등을 추출하는 데 사용됩니다.
NER_MODEL_NAME = "monologg/koelectra-base-v3-naver-ner"

# 한영 번역 모델 (MarianMT)
# 한국어 기사를 영어로 번역하여 검색 및 비교에 사용합니다.
TRANSLATION_MODEL_NAME = "Helsinki-NLP/opus-mt-ko-en"

# 문장 유사도 모델 (SBERT)
# 영어로 된 인용문과 검색 결과(Snippet) 사이의 의미적 유사도를 계산합니다.
SENTENCE_MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"

# 인용 왜곡 탐지 모델 (Quote Mining Classifier)
QUOTE_MINING_MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"

# --------------------------------------------------------
# 2. 하드웨어 설정 (Device Configuration)
# --------------------------------------------------------
# 0 이상: GPU 번호 (예: 0번 GPU 사용)
# -1: CPU 사용
# (pipeline 함수 기준에 맞춤. models.py에서 상황에 따라 -1로 자동 보정됨)
DEFAULT_DEVICE = 0

# --------------------------------------------------------
# 3. 데이터 처리 설정
# --------------------------------------------------------
# NER 모델에서 사용할 라벨 필터
# 사람(PER), 조직(ORG), 장소(LOC), 날짜(DAT), 인공물(AFW)만 남기고 나머지는 무시
NER_LABELS = {"PER", "ORG", "LOC", "DAT", "AFW"}


# --------------------------------------------------------
# 4. 웹 검색 설정 (Search Configuration)
# --------------------------------------------------------

# 신뢰할 수 있는 검색 대상 도메인 목록 (Fact-checking Target)
# 이 사이트들 내에서 원문을 찾습니다.
BASE_DOMAINS = [
    "site:whitehouse.gov",
    "site:congress.gov",
    "site:rollcall.com",
    "site:millercenter.org",
    "site:un.org",
    "site:factba.se",
    "site:foxnews.com",
    "site:c-span.org",
    "site:abcnews.go.com",
    "site:nbcnews.com",
    "site:cnn.com",
]

# 크롤링 시 봇 차단을 막기 위한 헤더 정보 (일반 브라우저인 척 위장)
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuoteContextBot/1.0; +https://example.org/bot)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# 유효성 검사 기준
HTML_MIN_LENGTH = 500  # 본문이 500자 미만이면 유효하지 않은 페이지로 간주
DEFAULT_TIMEOUT = 12   # 일반 웹페이지 요청 타임아웃 (초)
PDF_TIMEOUT = 20       # PDF 다운로드 타임아웃 (초)

# --------------------------------------------------------
# 5. 구글 API 키 (Credentials)
# --------------------------------------------------------

# Google Cloud Console에서 발급받은 API Key
GOOGLE_API_KEY_ENV = "your_api_key"

# Programmable Search Engine ID (검색 엔진 ID)
GOOGLE_CSE_CX_ENV = "your_api_key"
