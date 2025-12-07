import React from "react";
import clsx from "clsx";

interface QuoteCardProps {
  quote: string;
  source: string;
  similarityScore: number;
  onClick: () => void;
}

export const QuoteCard: React.FC<QuoteCardProps> = ({ quote, source, similarityScore, onClick }) => {
  const scoreColor =
    similarityScore >= 70
      ? "bg-green-100 text-green-800"
      : similarityScore >= 50
      ? "bg-blue-100 text-blue-800"
      : "bg-orange-100 text-orange-800";

  return (
    <div onClick={onClick} className="p-4 border border-border rounded-lg hover:bg-secondary cursor-pointer transition-colors">
      <div className="flex justify-between items-start gap-2 mb-2">
        <p className="text-sm font-medium text-foreground flex-1 line-clamp-2">"{quote}"</p>
        <span className={clsx("text-xs font-semibold px-2 py-1 rounded whitespace-nowrap", scoreColor)}>{similarityScore}%</span>
      </div>
      <p className="text-xs text-muted-foreground truncate">출처: {source}</p>
    </div>
  );
};
