import { jsxs as _jsxs } from "react/jsx-runtime";
import clsx from "clsx";
export const QuoteCard = ({ quote, source, similarityScore, onClick }) => {
    const scoreColor = similarityScore >= 70
        ? "bg-green-100 text-green-800"
        : similarityScore >= 50
            ? "bg-blue-100 text-blue-800"
            : "bg-orange-100 text-orange-800";
    return (_jsxs("div", { onClick: onClick, className: "p-4 border border-border rounded-lg hover:bg-secondary cursor-pointer transition-colors", children: [_jsxs("div", { className: "flex justify-between items-start gap-2 mb-2", children: [_jsxs("p", { className: "text-sm font-medium text-foreground flex-1 line-clamp-2", children: ["\"", quote, "\""] }), _jsxs("span", { className: clsx("text-xs font-semibold px-2 py-1 rounded whitespace-nowrap", scoreColor), children: [similarityScore, "%"] })] }), _jsxs("p", { className: "text-xs text-muted-foreground truncate", children: ["\uCD9C\uCC98: ", source] })] }));
};
