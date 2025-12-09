import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState, useEffect } from "react";
export const SidePanel = ({ quote }) => {
    const [results, setResults] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    useEffect(() => {
        // Listen for messages from background script
        chrome.runtime.onMessage.addListener((request, _sender, _sendResponse) => {
            if (request.action === "start_loading") {
                setIsLoading(true);
                // 새 분석 시작 시 이전 결과는 유지해도 되지만,
                // UX를 위해 비우고 싶다면 아래 주석을 해제
                // setResults([]);
            }
            else if (request.action === "display_results") {
                setResults(request.data || []);
                setIsLoading(false);
            }
        });
        // 초기 로드 시, 백그라운드에 저장된 최신 결과가 있으면 가져오기
        chrome.runtime.sendMessage({ action: "get_latest_results" }, (response) => {
            if (response?.results && Array.isArray(response.results) && response.results.length > 0) {
                setResults(response.results);
                setIsLoading(Boolean(response.isLoading));
            }
            else if (response?.isLoading) {
                setIsLoading(true);
            }
        });
    }, []);
    return (_jsxs("div", { className: "w-full h-full bg-background text-foreground flex flex-col", children: [_jsxs("div", { className: "bg-gradient-to-r from-primary to-accent text-white p-4 shadow-md", children: [_jsx("h1", { className: "text-lg font-bold", children: "\uC6D0\uBB38 \uCC3E\uAE30" }), _jsx("p", { className: "text-xs opacity-90", children: "\uC9C1\uC811 \uC778\uC6A9\uBB38\uC758 \uC6D0\uBB38\uC744 \uAC80\uC0C9\uD569\uB2C8\uB2E4" })] }), _jsxs("div", { className: "flex-1 overflow-y-auto p-4", children: [isLoading && (_jsx("div", { className: "flex justify-center items-center h-32", children: _jsx("div", { className: "animate-spin rounded-full h-8 w-8 border-t-2 border-primary" }) })), !isLoading && results.length === 0 && (_jsx("p", { className: "text-center text-muted-foreground text-sm py-8", children: "\uBD84\uC11D\uD560 \uC778\uC6A9\uBB38\uC744 \uD074\uB9AD\uD574\uC8FC\uC138\uC694." })), !isLoading && results.length > 0 && (_jsx("div", { className: "space-y-3", children: results.map((result, idx) => {
                            const similarity = result.similarity_score ?? 0;
                            // distortion_score는 0~1 확률 값으로 들어온다.
                            const distortionProb = typeof result.distortion_score === "number" ? result.distortion_score : null;
                            const distortionPercent = distortionProb !== null ? distortionProb * 100 : null;
                            const similarityColor = similarity >= 70
                                ? "bg-green-100 text-green-800"
                                : similarity >= 50
                                    ? "bg-blue-100 text-blue-800"
                                    : "bg-orange-100 text-orange-800";
                            const distortionColor = distortionPercent === null
                                ? "bg-gray-100 text-gray-700"
                                : distortionPercent >= 70
                                    ? "bg-red-100 text-red-800"
                                    : distortionPercent >= 40
                                        ? "bg-yellow-100 text-yellow-800"
                                        : "bg-emerald-100 text-emerald-800";
                            return (_jsxs("div", { className: "p-3 border border-border rounded-lg space-y-1.5", children: [_jsxs("div", { className: "flex justify-between items-start gap-2", children: [_jsxs("p", { className: "text-xs font-medium line-clamp-3", children: ["\"", result.original_span || result.quote || quote, "\""] }), _jsxs("div", { className: "flex flex-col items-end gap-1", children: [_jsxs("span", { className: `text-[10px] font-semibold px-2 py-0.5 rounded ${similarityColor}`, children: ["\uC720\uC0AC\uB3C4 ", similarity, "%"] }), _jsxs("span", { className: `text-[10px] font-semibold px-2 py-0.5 rounded ${distortionColor}`, children: ["\uC65C\uACE1", " ", distortionPercent !== null ? `${distortionPercent.toFixed(2)}%` : "N/A"] })] })] }), _jsx("p", { className: "text-[10px] text-muted-foreground truncate", children: result.source_url })] }, idx));
                        }) }))] }), _jsx("div", { className: "border-t border-border p-3 text-xs text-muted-foreground text-center", children: _jsx("p", { children: "Quote Origin Pipeline \u00A9 2024" }) })] }));
};
