#!/usr/bin/env python
"""
Quote Origin API - Quick Start Guide

이 스크립트는 API 서버를 시작하고 테스트하는 방법을 보여줍니다.

**1단계: 필요한 패키지 설치**

    pip install -r requirements-api.txt

**2단계: API 서버 시작**

방법 1 (기본 설정):
    python run_server.py

방법 2 (포트 변경):
    python run_server.py --port 9000

방법 3 (개발 모드):
    python run_server.py --reload

방법 4 (모듈 실행):
    python -m qdd2.backend_api

**3단계: API 테스트**

    python test_backend_api.py

**4단계: 웹 브라우저에서 API 문서 확인**

    http://localhost:8000/docs         (Swagger UI)
    http://localhost:8000/redoc        (ReDoc)

"""

print(__doc__)

import subprocess
import sys
import os

def print_menu():
    """메뉴 출력"""
    print("\n" + "=" * 80)
    print("Quote Origin API - Quick Start")
    print("=" * 80)
    print("\n선택하세요:")
    print("  1. API 서버 시작 (기본 포트 8000)")
    print("  2. API 서버 시작 (포트 변경)")
    print("  3. API 서버 시작 (개발 모드)")
    print("  4. API 테스트 실행")
    print("  5. 패키지 설치")
    print("  6. 종료")
    print("=" * 80)

def start_server(port=8000, reload=False):
    """API 서버 시작"""
    cmd = ["python", "run_server.py", "--port", str(port)]
    if reload:
        cmd.append("--reload")
    
    print(f"\n▶ API 서버 시작 중... (포트: {port})")
    print(f"  명령어: {' '.join(cmd)}")
    print(f"\n  API 문서: http://localhost:{port}/docs")
    print(f"  ReDoc: http://localhost:{port}/redoc")
    print(f"  종료: Ctrl+C\n")
    
    try:
        subprocess.run(cmd, check=False)
    except KeyboardInterrupt:
        print("\n\n종료됨.")

def run_tests():
    """API 테스트 실행"""
    print("\n▶ API 테스트 실행 중...\n")
    cmd = ["python", "test_backend_api.py"]
    try:
        subprocess.run(cmd, check=False)
    except KeyboardInterrupt:
        print("\n\n종료됨.")

def install_packages():
    """패키지 설치"""
    print("\n▶ 필요한 패키지 설치 중...\n")
    cmd = ["pip", "install", "-r", "requirements-api.txt"]
    try:
        subprocess.run(cmd, check=False)
    except KeyboardInterrupt:
        print("\n\n종료됨.")

def main():
    """메인 루프"""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    while True:
        print_menu()
        choice = input("\n선택 (1-6): ").strip()
        
        if choice == "1":
            start_server(port=8000)
        elif choice == "2":
            try:
                port = int(input("포트 번호를 입력하세요 (기본값 8000): ") or 8000)
                start_server(port=port)
            except ValueError:
                print("❌ 잘못된 포트 번호입니다.")
        elif choice == "3":
            start_server(port=8000, reload=True)
        elif choice == "4":
            run_tests()
        elif choice == "5":
            install_packages()
        elif choice == "6":
            print("\n종료합니다.")
            sys.exit(0)
        else:
            print("❌ 잘못된 선택입니다. 다시 시도하세요.")

if __name__ == "__main__":
    main()
