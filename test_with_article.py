"""
크롬 익스텐션 테스트 (기사.html 사용)
"""

import subprocess
import time
import sys
import os
from pathlib import Path

def print_section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_step(num, desc):
    print(f"\n[Step {num}] {desc}")
    print("-" * 80)

def check_servers():
    """서버 상태 확인"""
    print_section("서버 상태 확인")
    
    import requests
    
    servers = {
        "테스트 API 서버": "http://localhost:8000/health",
        "HTML 서버": "http://localhost:8080/"
    }
    
    for name, url in servers.items():
        try:
            response = requests.get(url, timeout=2)
            print(f"✓ {name}: 실행 중")
        except:
            print(f"✗ {name}: 미실행")
            return False
    
    return True

def main():
    print("\n" + "🔍 " * 20)
    print("크롬 익스텐션 테스트 (기사.html)")
    print("🔍 " * 20)
    
    # Step 1: 서버 상태 확인
    print_step(1, "서버 상태 확인")
    if not check_servers():
        print("\n⚠️  필수 서버를 시작해야 합니다!")
        print("\n새 터미널 창들에서 각각 다음 명령어를 실행하세요:")
        print("\n  [터미널 1] python run_server_test.py")
        print("  [터미널 2] python serve_article.py")
        print("\n그 후 이 스크립트를 다시 실행하세요.")
        return False
    
    # Step 2: 크롬 익스텐션 로드
    print_step(2, "크롬 익스텐션 설치 (수동)")
    guide = """
1️⃣  Chrome을 열고 주소창에 입력:
    chrome://extensions/

2️⃣  우상단 토글에서 '개발자 모드' 활성화

3️⃣  '패키지되지 않은 확장 프로그램 로드' 클릭

4️⃣  다음 폴더 선택:
    c:\\08_QDD3\\quote-origin-pipeline\\chrome_extension

5️⃣  확인:
    - "Quote Origin Detector" 표시됨
    - 빨간 오류 없음
"""
    print(guide)
    
    # Step 3: 기사 열기
    print_step(3, "테스트 기사 열기")
    article_url = "http://localhost:8080/기사.html"
    print(f"브라우저에서 다음 URL을 열어주세요:")
    print(f"  {article_url}")
    print(f"\n또는 아래 링크 클릭:")
    print(f"  ➜ {article_url}")
    
    # Step 4: 테스트 항목
    print_step(4, "테스트 항목")
    checklist = """
✅ 체크리스트:

1. 페이지 로드 확인
   □ 기사 HTML이 정상적으로 표시되는가?
   □ 익스텐션 아이콘이 활성화되어 있는가? (컬러)

2. 콘솔 확인 (F12 → Console)
   □ "[Quote Origin]" 메시지 보이는가?
   □ 탐지된 인용문 개수가 표시되는가?
   □ 에러 메시지는 없는가?

3. 익스텐션 팝업 (아이콘 클릭)
   □ 팝업이 열리는가?
   □ 분석 중이라는 메시지나 결과가 보이는가?
   □ 유사도, 원문, 출처 정보가 있는가?

4. 결과 검증
   □ 유사도가 0-100% 범위인가?
   □ 원문이 의미있는 텍스트인가?
   □ 출처 URL이 정상 형식인가?
"""
    print(checklist)
    
    # Step 5: 디버깅
    print_step(5, "문제 해결")
    debug = """
❌ 익스텐션 아이콘이 회색이면?
   → manifest.json에 localhost가 추가되었는지 확인
   → 확장 프로그램 페이지에서 수동으로 reload

❌ 콘솔에 "[Quote Origin]" 메시지가 없으면?
   → content-script.js가 로드되었는지 확인
   → 확장 프로그램 페이지에서 "Service Worker" 클릭해 로그 확인
   → 페이지 새로고침 (F5)

❌ "API 연결 실패" 오류?
   → python run_server_test.py 실행 확인
   → http://localhost:8000/health 접속 확인
   → 파이어월 포트 8000 개방 확인

❌ 팝업이 빈 화면?
   → F12 개발자 도구 → Console 탭 확인
   → 네트워크 에러 있는지 확인
   → popup.js 콘솔 로그 확인
"""
    print(debug)
    
    # Step 6: 다음 단계
    print_step(6, "명령어 요약")
    summary = """
🚀 빠른 시작:

터미널 1:
  python run_server_test.py

터미널 2:
  python serve_article.py

그 다음:
  1. Chrome → chrome://extensions/
  2. 개발자 모드 활성화
  3. chrome_extension 폴더 로드
  4. http://localhost:8080/기사.html 방문
  5. F12 콘솔 확인
  6. 익스텐션 아이콘 클릭
"""
    print(summary)
    
    print_section("준비 완료!")
    print("✅ 모든 준비가 완료되었습니다!")
    print("\n현재 상태:")
    print("  ✓ 테스트 API 서버: 실행 중 (포트 8000)")
    print("  ✓ HTML 서버: 실행 중 (포트 8080)")
    print("  ✓ 기사.html: 서빙 준비 완료")
    print("\n이제 위의 안내에 따라 크롬 익스텐션을 로드하고 테스트하세요!")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n종료됨")
