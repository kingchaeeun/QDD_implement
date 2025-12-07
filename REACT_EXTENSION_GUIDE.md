# React 기반 Chrome 확장 프로그램 테스트 가이드

## 1. 사전 준비

### 1.1 Backend API 서버 실행

```bash
cd c:\08_QDD3\quote-origin-pipeline
python run_server_test.py
# 또는
python -m run_server_test
```

**포트**: `http://localhost:8000`

### 1.2 테스트 HTML 서버 실행

```bash
cd c:\08_QDD3\quote-origin-pipeline
python serve_article.py
# 또는
python -m serve_article
```

**포트**: `http://localhost:8080/기사.html`

## 2. 확장 프로그램 로드

### 2.1 Chrome 개발자 모드 활성화

1. Chrome 열기
2. `chrome://extensions/` 접속
3. 우측 상단 **개발자 모드** 토글 활성화

### 2.2 확장 프로그램 로드

1. **압축 해제된 확장 프로그램 로드** 클릭
2. `c:\08_QDD3\quote-origin-pipeline\chrome_extension` 폴더 선택

### 2.3 확장 프로그램 아이콘 확인

- 확장 프로그램 아이콘이 Chrome 도구 모음에 표시되어야 함

## 3. 테스트 시나리오

### 3.1 localhost에서 테스트 (권장)

1. Chrome에서 `http://localhost:8080/기사.html` 접속
2. 페이지의 인용문에 노란색 강조 표시가 나타나야 함
3. 강조된 인용문 클릭
4. 우측 패널(Side Panel)에 분석 결과가 표시됨

### 3.2 Naver News 페이지에서 테스트

1. Chrome에서 `https://news.naver.com` 의 기사 페이지 접속
2. 인용문 감지 및 강조
3. 강조된 인용문 클릭 → Side Panel에 결과 표시

## 4. 디버깅

### 4.1 Chrome DevTools에서 확인

1. `chrome://extensions/` 열기
2. 확장 프로그램 아래 **서비스 워커** 클릭 → Background 스크립트 로그 확인
3. 특정 페이지의 콘텐츠 스크립트 확인: F12 → Console 탭

### 4.2 API 연결 확인

```powershell
# API 서버 상태 확인
Invoke-WebRequest -Uri "http://localhost:8000/api/find-origin" -Method POST -Body '{"quote":"test","article_content":"test","keywords":["test"]}' -ContentType "application/json"
```

### 4.3 확장 프로그램 재로드

1. `chrome://extensions/` 에서 확장 프로그램 아래 새로고침 버튼 클릭
2. 또는 F5로 테스트 페이지 새로고침

## 5. 주요 파일 구조

```
chrome_extension/
├── dist/                    # 빌드된 출력 폴더
│   ├── background.js        # Background Service Worker
│   ├── content-script.js    # Content Script
│   ├── side-panel.js        # Side Panel UI
│   ├── popup.js             # Popup UI
│   ├── globals.js           # React + 스타일
│   ├── assets/              # CSS 파일
│   └── src/
│       ├── side-panel.html  # Side Panel HTML
│       └── popup.html       # Popup HTML
├── src/
│   ├── components/
│   │   ├── SidePanel.tsx    # React Side Panel 컴포넌트
│   │   ├── QuoteCard.tsx    # Quote Card 컴포넌트
│   │   └── ResultsContainer.tsx
│   ├── side-panel.tsx       # Side Panel 진입점
│   ├── popup.tsx            # Popup 진입점
│   ├── background.ts        # Background Service Worker (TypeScript)
│   ├── content-script.ts    # Content Script (TypeScript)
│   └── styles/
│       └── globals.css      # 전역 스타일
├── manifest.json            # 확장 프로그램 설정
├── package.json             # Node.js 의존성
├── tsconfig.json            # TypeScript 설정
├── vite.config.ts           # Vite 빌드 설정
├── tailwind.config.js       # Tailwind CSS 설정
└── postcss.config.js        # PostCSS 설정
```

## 6. 빌드 및 개발

### 6.1 개발 모드 (Watch)

```bash
cd c:\08_QDD3\quote-origin-pipeline\chrome_extension
npm run dev
```

### 6.2 프로덕션 빌드

```bash
cd c:\08_QDD3\quote-origin-pipeline\chrome_extension
npm run build
```

### 6.3 변경 후 확장 프로그램 재로드

1. `npm run build` 실행
2. `chrome://extensions/` 에서 새로고침 버튼 클릭

## 7. 예상되는 동작

### 성공 케이스

- ✅ 페이지 로드 시 인용문이 노란색으로 강조됨
- ✅ 강조된 인용문을 클릭하면 Side Panel이 열림
- ✅ Side Panel에 API 분석 결과가 표시됨
- ✅ 유사도 점수에 따라 배지 색상 변경 (녹색/파란색/주황색)

### 에러 케이스

- ❌ API 서버가 실행 중이지 않으면 "✗ API 연결 안됨" 표시
- ❌ 인용문이 감지되지 않으면 "분석할 인용문을 클릭해주세요" 메시지 표시

## 8. 알려진 제한사항

- Manifest V3 제한으로 일부 브라우저 API 사용 불가
- Naver News 페이지의 구조에 따라 인용문 감지 정확도 변동 가능
- localhost 테스트는 `http://localhost:8080/기사.html` 에서만 작동

## 9. 문제 해결

| 문제                       | 해결 방법                                    |
| -------------------------- | -------------------------------------------- |
| Side Panel이 나타나지 않음 | Chrome 재시작 및 확장 재로드                 |
| 인용문이 강조되지 않음     | 콘텐츠 스크립트 로그 확인 (F12 Console)      |
| API 연결 오류              | `http://localhost:8000` 서버 실행 확인       |
| 빌드 실패                  | `npm install` 재실행 및 TypeScript 에러 확인 |
| 매니페스트 에러            | manifest.json 경로 확인 (dist/src/ vs dist/) |

---

**업데이트**: 2024년 12월 5일
**버전**: 1.0.0 (React 기반 재개발)
