"use strict";
// Quote detection and highlighting
class QuoteDetector {
    constructor() {
        Object.defineProperty(this, "quotes", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: new Map()
        });
    }
    /**
     * 기사 본문 DOM 루트를 반환
     * - 사이드바/헤더 등 불필요한 영역은 제외하기 위해 사용
     */
    getArticleRootElement() {
        const selectors = ["article", ".article-body", ".article_body", "#articleBodyContents", ".content", "main"];
        for (const selector of selectors) {
            const element = document.querySelector(selector);
            if (element && element.innerText && element.innerText.length > 100) {
                return element;
            }
        }
        return null;
    }
    /**
     * 헤드라인(기사 제목) 요소 목록을 반환
     */
    getHeadlineElements() {
        const selectors = ["h1", "h2", ".media_end_head_headline", "#title_area"];
        const elements = [];
        for (const selector of selectors) {
            const found = document.querySelectorAll(selector);
            found.forEach((el) => {
                if (el.innerText && el.innerText.trim().length > 0) {
                    elements.push(el);
                }
            });
        }
        return elements;
    }
    detectQuotes() {
        const content = this.extractArticleContent();
        if (!content)
            return [];
        // 직선 따옴표, 곡선 따옴표, 싱글 따옴표 모두 감지
        const patterns = [
            /\u201c([\s\S]*?)\u201d/g, // 곡선 쌍따옴표
            // /\u2018([\s\S]*?)\u2019/g, // 곡선 싱글 따옴표
            /"([\s\S]*?)"/g, // 직선 따옴표
        ];
        const detectedQuotes = [];
        let quoteIndex = 0;
        for (const pattern of patterns) {
            let match;
            while ((match = pattern.exec(content)) !== null) {
                const quote = match[1].trim();
                // 길이 필터 (10-500 자)
                if (quote.length >= 10 && quote.length <= 500) {
                    const id = `quote-${quoteIndex++}`;
                    this.quotes.set(id, quote);
                    detectedQuotes.push({
                        id,
                        quote: quote.substring(0, 100),
                        position: match.index,
                    });
                }
            }
        }
        return detectedQuotes;
    }
    extractArticleContent() {
        // Naver 뉴스 기사 본문 + 헤드라인 텍스트 추출
        let content = "";
        const articleRoot = this.getArticleRootElement();
        if (articleRoot && articleRoot.innerText && articleRoot.innerText.length > 100) {
            content = articleRoot.innerText;
        }
        // 헤드라인 텍스트를 앞에 붙여서 인용 탐지에 포함
        const headlineElements = this.getHeadlineElements();
        if (headlineElements.length > 0) {
            const headlineText = headlineElements.map((el) => el.innerText).join(" ");
            content = `${headlineText} ${content}`.trim();
        }
        // 여전히 컨텐츠가 없으면 전체 페이지에서 긴 텍스트 찾기 (fallback)
        if (content.length < 100) {
            const bodyText = document.body.innerText;
            if (bodyText.length > 100) {
                content = bodyText;
            }
        }
        // 공백 정규화
        return content.replace(/\s+/g, " ").trim();
    }
    getFullQuote(quoteId) {
        return this.quotes.get(quoteId);
    }
    /**
     * 기사 본문 영역에서만 인용부를 하이라이트
     * - 주변 문장은 그대로 두고 인용부만 <mark>로 감싼다.
     * - detectQuotes()에서 수집한 quote 텍스트와 매칭하여 올바른 quote_id를 부여한다.
     */
    highlightQuotes(quotes) {
        if (!quotes.length)
            return;
        const roots = [];
        // detectQuotes()에서는 extractArticleContent()에서
        // 헤드라인 텍스트를 본문 앞에 붙여서 분석하기 때문에,
        // DOM 순회에서도 헤드라인을 먼저 처리하고 그 다음에 본문을 처리해야
        // quote-0, quote-1, ... 순서가 직관적으로 맞는다.
        const headlineElements = this.getHeadlineElements();
        headlineElements.forEach((el) => roots.push(el));
        const articleRoot = this.getArticleRootElement();
        if (articleRoot) {
            roots.push(articleRoot);
        }
        if (!roots.length)
            return;
        const quotePattern = /(\u201c[\s\S]*?\u201d|\u2018[\s\S]*?\u2019|"[\s\S]*?"|「[\s\S]*?」|『[\s\S]*?』|《[\s\S]*?》)/g;
        const normalizeQuoteText = (text) => text
            .replace(/[\u201c\u201d\u2018\u2019"「」『』《》]/g, "")
            .replace(/\s+/g, " ")
            .trim();
        // detectQuotes()에서 수집한 전체 quote 텍스트를 기반으로 매핑 생성
        // 동일한 인용문 텍스트가 여러 번 등장할 수 있으므로, 텍스트별로 quote_id 큐를 유지한다.
        const quoteQueueByText = new Map();
        const quoteNumberById = new Map();
        quotes.forEach((q, index) => {
            quoteNumberById.set(q.id, index + 1); // 1부터 시작하는 각주 번호 (검출 순서 기준)
            const full = this.getFullQuote(q.id) ?? q.quote;
            const key = normalizeQuoteText(full);
            if (key) {
                const queue = quoteQueueByText.get(key) ?? [];
                queue.push(q.id);
                quoteQueueByText.set(key, queue);
            }
        });
        // 여러 루트(article, 헤드라인)를 순회하며 텍스트 노드 처리
        roots.forEach((root) => {
            const treeWalker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
            let currentNode;
            const textNodesToProcess = [];
            while ((currentNode = treeWalker.nextNode())) {
                const textNode = currentNode;
                const parentElement = textNode.parentElement;
                // 이미 하이라이트된 영역(mark.quote-highlight 내부)의 텍스트는 다시 처리하지 않는다.
                if (parentElement && parentElement.classList.contains("quote-highlight")) {
                    continue;
                }
                const textContent = textNode.textContent ?? "";
                quotePattern.lastIndex = 0; // 글로벌 패턴 초기화
                if (quotePattern.test(textContent)) {
                    textNodesToProcess.push(textNode);
                }
            }
            for (const textNode of textNodesToProcess) {
                const originalText = textNode.textContent ?? "";
                if (!originalText)
                    continue;
                const fragment = document.createDocumentFragment();
                let lastIndex = 0;
                let match;
                quotePattern.lastIndex = 0;
                while ((match = quotePattern.exec(originalText)) !== null) {
                    const start = match.index;
                    const end = quotePattern.lastIndex;
                    // 인용부 앞의 일반 텍스트 추가
                    if (start > lastIndex) {
                        fragment.appendChild(document.createTextNode(originalText.slice(lastIndex, start)));
                    }
                    const quoteWithBrackets = originalText.slice(start, end);
                    const normalized = normalizeQuoteText(quoteWithBrackets);
                    let quoteId;
                    // 1차: 텍스트가 완전히 일치하는 큐에서 순서대로 하나씩 소진
                    if (normalized) {
                        const exactQueue = quoteQueueByText.get(normalized);
                        if (exactQueue && exactQueue.length > 0) {
                            quoteId = exactQueue.shift();
                            if (exactQueue.length === 0) {
                                quoteQueueByText.delete(normalized);
                            }
                            else {
                                quoteQueueByText.set(normalized, exactQueue);
                            }
                        }
                    }
                    // 2차: 줄바꿈/공백 차이 등으로 인해 부분 문자열로만 일치하는 경우,
                    // 해당 큐에서 하나를 가져온다.
                    if (!quoteId && normalized) {
                        for (const [key, queue] of quoteQueueByText.entries()) {
                            if (!queue.length)
                                continue;
                            if (normalized.includes(key) || key.includes(normalized)) {
                                quoteId = queue.shift();
                                if (!queue.length) {
                                    quoteQueueByText.delete(key);
                                }
                                else {
                                    quoteQueueByText.set(key, queue);
                                }
                                break;
                            }
                        }
                    }
                    if (quoteId) {
                        const mark = document.createElement("mark");
                        mark.classList.add("quote-highlight");
                        mark.dataset.quoteId = quoteId;
                        mark.style.backgroundColor = "#ffeb3b";
                        mark.style.padding = "0 2px";
                        mark.style.borderRadius = "3px";
                        mark.textContent = quoteWithBrackets;
                        // 각주 번호 (quote_id 기반, 공통 컬럼)
                        const numberSpan = document.createElement("span");
                        const footnoteNumber = quoteNumberById.get(quoteId);
                        numberSpan.textContent = footnoteNumber ? String(footnoteNumber) : "";
                        numberSpan.style.fontSize = "0.75em";
                        numberSpan.style.marginLeft = "2px";
                        numberSpan.style.verticalAlign = "super";
                        numberSpan.style.opacity = "0.9";
                        fragment.appendChild(mark);
                        fragment.appendChild(numberSpan);
                    }
                    else {
                        // 매칭되는 quote_id가 없으면 원본 텍스트를 그대로 둔다
                        fragment.appendChild(document.createTextNode(quoteWithBrackets));
                    }
                    lastIndex = end;
                }
                // 마지막 인용부 뒤의 일반 텍스트 추가
                if (lastIndex < originalText.length) {
                    fragment.appendChild(document.createTextNode(originalText.slice(lastIndex)));
                }
                if (textNode.parentNode) {
                    textNode.parentNode.replaceChild(fragment, textNode);
                }
            }
        });
    }
}
// Content Script 메인 로직
class ContentScriptManager {
    constructor() {
        Object.defineProperty(this, "detector", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: new QuoteDetector()
        });
    }
    /**
     * 페이지 오른쪽에 인라인 사이드패널(iframe)을 생성/표시
     * - Chrome sidePanel API 제약(사용자 제스처) 회피용
     */
    openInlineSidePanel() {
        const existing = document.getElementById("qop-side-panel-container");
        if (existing) {
            existing.style.display = "block";
            return;
        }
        const container = document.createElement("div");
        container.id = "qop-side-panel-container";
        Object.assign(container.style, {
            position: "fixed",
            top: "0",
            right: "0",
            width: "420px",
            height: "100vh",
            zIndex: "2147483647",
            backgroundColor: "white",
            boxShadow: "0 0 10px rgba(0,0,0,0.3)",
            borderLeft: "1px solid rgba(0,0,0,0.1)",
        });
        const iframe = document.createElement("iframe");
        iframe.src = chrome.runtime.getURL("html/side-panel.html");
        iframe.style.width = "100%";
        iframe.style.height = "100%";
        iframe.style.border = "none";
        container.appendChild(iframe);
        document.body.appendChild(container);
    }
    initialize() {
        // 네이버 뉴스 도메인 확인
        const isNaverNews = /^https:\/\/n\.news\.naver\.com\/mnews\/article\//.test(window.location.href);
        console.log("Current URL:", window.location.href); // 디버깅 로그 추가
        console.log("Is Naver News:", isNaverNews); // 디버깅 로그 추가
        if (!isNaverNews) {
            console.warn("This script only runs on Naver News article pages.");
            return;
        }
        // 페이지 로드 완료 후 quote 감지
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", () => this.onPageReady());
        }
        else {
            this.onPageReady();
        }
        // Background script로부터 메시지 수신
        chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
            if (request.action === "detect_quotes") {
                this.detectAndHighlight();
                sendResponse({ success: true });
            }
        });
    }
    onPageReady() {
        this.detectAndHighlight();
    }
    detectAndHighlight() {
        const quotes = this.detector.detectQuotes();
        if (quotes.length === 0) {
            return;
        }
        this.detector.highlightQuotes(quotes);
        this.addQuoteClickListeners(quotes);
        // 기사에 진입했을 때, 페이지 내 모든 직접 인용문에 대해
        // 백엔드 파이프라인(find-origin)을 한 번씩 돌려준다.
        // (UI는 마지막 요청만 보여주지만, 백엔드 로그/데이터는 모든 인용문 기준으로 남는다.)
        this.runBackendForAllQuotes(quotes);
    }
    addQuoteClickListeners(quotes) {
        const quoteMap = new Map(quotes.map((q) => [q.id, q]));
        const marks = document.querySelectorAll("mark.quote-highlight");
        marks.forEach((mark) => {
            const quoteId = mark.dataset.quoteId;
            if (!quoteId)
                return;
            const quoteData = quoteMap.get(quoteId);
            if (!quoteData)
                return;
            mark.style.cursor = "pointer";
            mark.style.transition = "all 0.2s";
            mark.addEventListener("mouseenter", () => {
                mark.style.filter = "brightness(0.9)";
            });
            mark.addEventListener("mouseleave", () => {
                mark.style.filter = "brightness(1)";
            });
            mark.addEventListener("click", () => {
                this.onQuoteClick(quoteData);
            });
        });
    }
    async onQuoteClick(quoteData) {
        const fullQuote = this.detector.getFullQuote(quoteData.id);
        if (!fullQuote)
            return;
        // Article 정보 추출
        const articleData = this.extractArticleData();
        // 사용자 클릭 제스처에 직접 반응해서 페이지 내 사이드패널을 먼저 연다.
        this.openInlineSidePanel();
        // 사이드패널/백그라운드에 로딩 상태 시작 알림
        chrome.runtime.sendMessage({ action: "start_loading" });
        chrome.runtime.sendMessage({ action: "set_loading_state", isLoading: true });
        // Backend 호출은 CORS 영향을 받지 않도록 background에서 수행
        chrome.runtime.sendMessage({
            action: "find_origin",
            payload: {
                quote_id: quoteData.id,
                quote_content: fullQuote,
                article_text: articleData.content,
                article_url: window.location.href,
                article_title: articleData.title,
                keywords: articleData.keywords,
            },
        }, (response) => {
            if (!response?.success) {
                console.error("Background find_origin failed:", response?.error);
                return;
            }
            const results = response.data;
            chrome.runtime.sendMessage({
                action: "display_results",
                data: results,
            });
        });
    }
    extractArticleData() {
        const selectors = ["article", ".article-body", ".article_body", "#articleBodyContents", ".content", "main"];
        let content = "";
        for (const selector of selectors) {
            const element = document.querySelector(selector);
            if (element && element.textContent && element.textContent.length > 100) {
                content = element.textContent;
                break;
            }
        }
        content = content.replace(/\s+/g, " ").trim();
        // Title 추출
        const titleElement = document.querySelector('h1, .title, [role="heading"]');
        const title = titleElement?.textContent || document.title;
        // Keywords 추출 (간단한 버전)
        const keywords = this.extractKeywords(content);
        return { content, keywords, title };
    }
    extractKeywords(text) {
        // 간단한 키워드 추출 (공백으로 분리된 주요 단어)
        const words = text.split(/\s+/);
        return words.filter((word) => word.length > 3).slice(0, 10);
    }
    /**
     * 기사 내에서 감지된 모든 인용문에 대해 백엔드 파이프라인을 실행한다.
     * - 요청은 순차적으로 보내서 서버 부하를 피한다.
     * - 각 인용문에 대한 결과는 백엔드 로그 및 background 최신 결과로만 사용된다.
     */
    runBackendForAllQuotes(quotes) {
        if (!quotes.length)
            return;
        const articleData = this.extractArticleData();
        const processSequentially = async () => {
            for (const q of quotes) {
                const fullQuote = this.detector.getFullQuote(q.id) ?? q.quote;
                await new Promise((resolve) => {
                    chrome.runtime.sendMessage({
                        action: "find_origin",
                        payload: {
                            quote_id: q.id,
                            quote_content: fullQuote,
                            article_text: articleData.content,
                            article_url: window.location.href,
                            article_title: articleData.title,
                            keywords: articleData.keywords,
                        },
                    }, (response) => {
                        if (!response?.success) {
                            console.error("Background find_origin failed (bulk):", response?.error);
                        }
                        resolve();
                    });
                });
            }
        };
        processSequentially().catch((err) => {
            console.error("Error while running bulk quote analysis:", err);
        });
    }
}
// 초기화
const manager = new ContentScriptManager();
manager.initialize();
