"use strict";
// Background Service Worker
class BackgroundManager {
    constructor() {
        Object.defineProperty(this, "latestResults", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: []
        });
        Object.defineProperty(this, "isLoading", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: false
        });
        // quote_id별로 백엔드 결과를 캐싱해서, 동일 인용문 재요청 시
        // 백엔드를 다시 호출하지 않고 즉시 반환한다.
        Object.defineProperty(this, "cacheByQuoteId", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: {}
        });
    }
    initialize() {
        chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
            console.log("[Background] Received message:", request.action);
            if (request.action === "display_results") {
                this.latestResults = request.data;
                this.isLoading = false;
                sendResponse({ success: true });
            }
            else if (request.action === "get_latest_results") {
                sendResponse({ results: this.latestResults, isLoading: this.isLoading });
            }
            else if (request.action === "set_loading_state") {
                this.isLoading = Boolean(request.isLoading);
                sendResponse({ success: true });
            }
            else if (request.action === "find_origin") {
                this.handleFindOrigin(request.payload)
                    .then((data) => {
                    sendResponse({ success: true, data });
                })
                    .catch((error) => {
                    console.error("[Background] Error in find_origin:", error);
                    sendResponse({ success: false, error: String(error) });
                });
                // 비동기 sendResponse 사용을 위해 true 반환
                return true;
            }
        });
    }
    async handleFindOrigin(payload) {
        const quoteId = payload.quote_id;
        // 이미 캐시된 결과가 있으면, 백엔드를 다시 호출하지 않고 즉시 반환
        if (quoteId && this.cacheByQuoteId[quoteId]) {
            this.latestResults = this.cacheByQuoteId[quoteId];
            this.isLoading = false;
            return this.cacheByQuoteId[quoteId];
        }
        this.isLoading = true;
        const response = await fetch("http://localhost:8000/api/find-origin", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        if (!response.ok) {
            const text = await response.text();
            throw new Error(`HTTP ${response.status}: ${text}`);
        }
        const json = await response.json();
        // 백엔드 QuoteResponse를 사이드패널에서 바로 쓸 수 있는 형태로 변환
        const candidates = Array.isArray(json.candidates) ? json.candidates : [];
        const mappedResults = candidates.map((cand) => ({
            quote_id: json.quote_id,
            quote: json.quote_content, // 기존 UI에서 사용하던 필드명 유지
            original_span: cand.original_span,
            // 유사도는 여전히 % 단위 정수로 표시
            similarity_score: Math.round((cand.similarity_score ?? 0) * 100),
            // 왜곡 점수는 0~1 확률 값을 그대로 유지하고, UI에서 자리수 포맷팅
            distortion_score: typeof cand.distortion_score === "number" ? cand.distortion_score : null,
            is_distorted: typeof cand.is_distorted === "boolean" ? cand.is_distorted : null,
            source_url: cand.source_url,
        }));
        this.latestResults = mappedResults;
        if (quoteId) {
            this.cacheByQuoteId[quoteId] = mappedResults;
        }
        this.isLoading = false;
        return mappedResults;
    }
}
const bgManager = new BackgroundManager();
bgManager.initialize();
