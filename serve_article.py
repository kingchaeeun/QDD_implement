"""
로컬 HTML 파일을 서빙하는 간단한 서버
기사.html을 로컬에서 테스트하기 위해 사용
"""

import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

PORT = 8080
ARTICLE_PATH = Path(__file__).parent / "기사.html"

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # 루트 요청 시 기사.html 제공
        if self.path == "/" or self.path == "":
            self.path = "/기사.html"
        
        # 기사.html 요청 시 파일 반환
        if self.path == "/기사.html":
            try:
                with open(ARTICLE_PATH, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', len(content))
                self.end_headers()
                self.wfile.write(content)
                return
            except FileNotFoundError:
                self.send_error(404, f"File not found: {ARTICLE_PATH}")
                return
        
        return super().do_GET()

def main():
    os.chdir(Path(__file__).parent)
    
    print("=" * 70)
    print("로컬 HTML 서버 시작")
    print("=" * 70)
    print(f"포트: {PORT}")
    print(f"기사 파일: {ARTICLE_PATH}")
    print(f"URL: http://localhost:{PORT}/기사.html")
    print("=" * 70)
    print("\n테스트 방법:")
    print("1. Chrome을 열고 chrome://extensions/ 방문")
    print("2. 개발자 모드 활성화")
    print("3. chrome_extension 폴더 로드")
    print("4. http://localhost:8080/기사.html 방문")
    print("5. F12 콘솔에서 '[Quote Origin]' 메시지 확인")
    print("6. 익스텐션 아이콘 클릭해서 결과 확인")
    print("\n서버 종료: Ctrl+C")
    print("=" * 70 + "\n")
    
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print(f"✓ 서버 실행 중: http://localhost:{PORT}/")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n서버 종료됨")

if __name__ == "__main__":
    main()
