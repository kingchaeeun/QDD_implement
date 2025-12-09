import React, { useState, useEffect } from "react";

interface SidePanelProps {
  quoteId?: string;
  quote?: string;
}

export const SidePanel: React.FC<SidePanelProps> = ({ quote }) => {
  const [results, setResults] = useState<Array<any>>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // Listen for messages from background script
    chrome.runtime.onMessage.addListener((request, _sender, _sendResponse) => {
      if (request.action === "start_loading") {
        setIsLoading(true);
        // 새 분석 시작 시 이전 결과는 유지해도 되지만,
        // UX를 위해 비우고 싶다면 아래 주석을 해제
        // setResults([]);
      } else if (request.action === "display_results") {
        setResults(request.data || []);
        setIsLoading(false);
      }
    });

    // 초기 로드 시, 백그라운드에 저장된 최신 결과가 있으면 가져오기
    chrome.runtime.sendMessage({ action: "get_latest_results" }, (response) => {
      if (response?.results && Array.isArray(response.results) && response.results.length > 0) {
        setResults(response.results);
        setIsLoading(Boolean(response.isLoading));
      } else if (response?.isLoading) {
        setIsLoading(true);
      }
    });
  }, []);

  return (
    <div className="w-full h-full bg-background text-foreground flex flex-col">
      {/* Header */}
      <div className="bg-gradient-to-r from-primary to-accent text-white p-4 shadow-md">
        <h1 className="text-lg font-bold">원문 찾기</h1>
        <p className="text-xs opacity-90">직접 인용문의 원문을 검색합니다</p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {isLoading && (
          <div className="flex justify-center items-center h-32">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-primary"></div>
          </div>
        )}

        {!isLoading && results.length === 0 && (
          <p className="text-center text-muted-foreground text-sm py-8">분석할 인용문을 클릭해주세요.</p>
        )}

        {!isLoading && results.length > 0 && (
          <div className="space-y-3">
            {results.map((result, idx) => {
              const similarity = result.similarity_score ?? 0;
              // distortion_score는 0~1 확률 값으로 들어온다.
              const distortionProb: number | null =
                typeof result.distortion_score === "number" ? result.distortion_score : null;
              const distortionPercent = distortionProb !== null ? distortionProb * 100 : null;

              const similarityColor =
                similarity >= 70
                  ? "bg-green-100 text-green-800"
                  : similarity >= 50
                  ? "bg-blue-100 text-blue-800"
                  : "bg-orange-100 text-orange-800";

              const distortionColor =
                distortionPercent === null
                  ? "bg-gray-100 text-gray-700"
                  : distortionPercent >= 70
                  ? "bg-red-100 text-red-800"
                  : distortionPercent >= 40
                  ? "bg-yellow-100 text-yellow-800"
                  : "bg-emerald-100 text-emerald-800";

              return (
                <div key={idx} className="p-3 border border-border rounded-lg space-y-1.5">
                  <div className="flex justify-between items-start gap-2">
                    <p className="text-xs font-medium line-clamp-3">
                      "{result.original_span || result.quote || quote}"
                    </p>
                    <div className="flex flex-col items-end gap-1">
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded ${similarityColor}`}>
                        유사도 {similarity}%
                      </span>
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded ${distortionColor}`}>
                        {/* 예: 45.16% 처럼 소수점 둘째 자리에서 반올림 */}
                        왜곡{" "}
                        {distortionPercent !== null ? `${distortionPercent.toFixed(2)}%` : "N/A"}
                      </span>
                    </div>
                  </div>
                  <p className="text-[10px] text-muted-foreground truncate">{result.source_url}</p>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-border p-3 text-xs text-muted-foreground text-center">
        <p>Quote Origin Pipeline © 2024</p>
      </div>
    </div>
  );
};
