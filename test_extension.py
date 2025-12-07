"""
크롬 익스텐션 테스트 가이드

이 스크립트는 테스트를 위한 설정과 실행 방법을 안내합니다.
"""

import subprocess
import time
import os
import sys

def print_header(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_step(step_num, description):
    print(f"\n[Step {step_num}] {description}")
    print("-" * 80)

def test_backend_api():
    """백엔드 API 테스트"""
    print_step(1, "백엔드 API 상태 확인")
    
    try:
        import requests
        response = requests.get("http://localhost:8000/api/find-origin", timeout=5)
        print("✓ API 서버 실행 중 (포트 8000)")
        return True
    except requests.exceptions.ConnectionError:
        print("✗ API 서버가 실행 중이 아닙니다!")
        print("\n다음 명령어로 서버를 시작하세요:")
        print("  python run_server.py")
        return False
    except Exception as e:
        print(f"오류: {e}")
        return False

def show_extension_install_guide():
    """크롬 익스텐션 설치 가이드"""
    print_step(2, "크롬 익스텐션 설치 (개발자 모드)")
    
    guide = """
1️⃣  Chrome 주소창에 다음 입력:
    chrome://extensions/

2️⃣  우상단 토글에서 '개발자 모드' 활성화

3️⃣  '패키지되지 않은 확장 프로그램 로드' 클릭

4️⃣  다음 폴더 선택:
    c:\\08_QDD3\\quote-origin-pipeline\\chrome_extension

5️⃣  설치 확인:
    - Extensions 페이지에서 "Quote Origin Detector" 보이는지 확인
    - ID: xxxxxxxxxxxxxxxx 형태의 ID 할당됨
"""
    print(guide)

def show_test_instructions():
    """테스트 방법"""
    print_step(3, "테스트 실행")
    
    instructions = """
📖 테스트 순서:

1️⃣  테스트 기사 페이지 방문:
    https://n.news.naver.com/mnews/article/123/0000123456

    (또는 https://n.news.naver.com/ 에서 아무 기사나 선택)

2️⃣  페이지 로드 후:
    - 크롬 개발자 도구 (F12) 열기
    - Console 탭 확인
    - "[Quote Origin]" 로그 메시지 확인

    예시:
    [Quote Origin] 3개의 직접인용문 탐지됨
    [Quote Origin] 백엔드로 3개 인용문 전송 중...

3️⃣  익스텐션 아이콘 클릭:
    - 팝업이 열리면서 분석 결과 표시
    - 각 인용문의 유사도, 원문, 출처 확인

4️⃣  결과 확인:
    ✓ 유사도 점수 (%)
    ✓ 원문 텍스트
    ✓ 출처 URL (클릭하면 새 탭 열림)

🎯 예상 결과:
    - 직접인용문: "..." 형태의 텍스트만 탐지
    - 길이: 10자 이상 500자 이하
    - 유사도: 0.7 이상이면 신뢰도 높음
"""
    print(instructions)

def show_debugging_tips():
    """디버깅 팁"""
    print_step(4, "문제 해결")
    
    tips = """
❌ 익스텐션 아이콘이 회색이면:
   → 네이버 뉴스 페이지가 아닙니다
   → https://n.news.naver.com/mnews/article/* 형태여야 함

❌ 콘솔에 오류 메시지:
   → F12 → Console 탭 확인
   → "[Quote Origin]" 메시지 보이는지 확인
   → 네트워크 오류면 백엔드 서버 상태 확인

❌ 팝업에서 "인용문을 분석 중입니다..." 표시:
   → 2-3분 기다려보기 (첫 로드 시 모델 다운로드 중일 수 있음)
   → 또는 F5 새로고침

❌ "연결 실패" 오류:
   → Backend API 서버 실행 확인:
     python run_server.py
   → 포트 8000이 개방되어 있는지 확인

🔍 개발자 도구에서 확인하기:
   1. 익스텐션 페이지 (chrome://extensions/)
   2. "Quote Origin Detector" 찾기
   3. "Service Worker" 클릭 → 백그라운드 콘솔
   4. 또는 웹페이지에서 F12 → Console
"""
    print(tips)

def show_file_structure():
    """파일 구조 확인"""
    print_step(5, "파일 구조 확인")
    
    structure = """
확인할 파일들:

chrome_extension/
├── manifest.json              ← 익스텐션 설정
├── js/
│   ├── background.js         ← 백그라운드 워커
│   ├── content-script.js     ← 👈 직접인용문 탐지 (핵심)
│   └── popup.js              ← 팝업 UI 스크립트
├── html/
│   └── popup.html            ← 팝업 HTML
└── css/
    ├── popup.css             ← 팝업 스타일
    └── highlight.css         ← 페이지 하이라이트

✓ 모든 파일이 있는지 확인하세요!
"""
    print(structure)

def main():
    print("\n" + "🔍 " * 20)
    print("크롬 익스텐션 테스트 가이드")
    print("🔍 " * 20)
    
    # 백엔드 확인
    if not test_backend_api():
        print("\n⚠️  백엔드 서버를 먼저 시작해야 합니다!")
        print("\n새 터미널에서 다음 명령어 실행:")
        print("  cd c:\\08_QDD3\\quote-origin-pipeline")
        print("  python run_server.py")
        print("\n그 후 이 스크립트를 다시 실행하세요.")
        sys.exit(1)
    
    # 가이드 표시
    show_extension_install_guide()
    show_test_instructions()
    show_file_structure()
    show_debugging_tips()
    
    print_step(6, "준비 완료!")
    print("""
✅ 준비 완료!

다음 단계:
1. 백엔드 서버 실행: python run_server.py
2. Chrome 개발자 모드에서 익스텐션 로드
3. 네이버 뉴스 기사 방문
4. 익스텐션 팝업에서 결과 확인

문제 발생 시 위의 "문제 해결" 섹션을 참고하세요.
""")

if __name__ == "__main__":
    main()
