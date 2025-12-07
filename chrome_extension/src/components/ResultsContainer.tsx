import React from "react";
import clsx from "clsx";

interface ResultsContainerProps {
  results: Array<{
    id: string;
    quote: string;
    source: string;
    similarity_score: number;
  }>;
  isLoading?: boolean;
  onQuoteClick: (quoteId: string) => void;
}

export const ResultsContainer: React.FC<ResultsContainerProps> = ({ results, isLoading = false, onQuoteClick }) => {
  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-primary"></div>
      </div>
    );
  }

  if (!results || results.length === 0) {
    return (
      <div className="flex justify-center items-center h-64 text-muted-foreground">
        <p>분석 결과를 표시할 인용문이 없습니다.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {results.map((result) => (
        <div
          key={result.id}
          onClick={() => onQuoteClick(result.id)}
          className={clsx("p-4 border border-border rounded-lg hover:bg-secondary cursor-pointer transition-colors")}
        >
          <div className="flex justify-between items-start gap-2 mb-2">
            <p className="text-sm font-medium text-foreground flex-1 line-clamp-2">"{result.quote}"</p>
            <span
              className={clsx(
                "text-xs font-semibold px-2 py-1 rounded whitespace-nowrap",
                result.similarity_score >= 70
                  ? "bg-green-100 text-green-800"
                  : result.similarity_score >= 50
                  ? "bg-blue-100 text-blue-800"
                  : "bg-orange-100 text-orange-800"
              )}
            >
              {result.similarity_score}%
            </span>
          </div>
          <p className="text-xs text-muted-foreground truncate">출처: {result.source}</p>
        </div>
      ))}
    </div>
  );
};
