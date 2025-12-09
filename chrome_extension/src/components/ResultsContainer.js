import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import clsx from "clsx";
export const ResultsContainer = ({ results, isLoading = false, onQuoteClick }) => {
    if (isLoading) {
        return (_jsx("div", { className: "flex justify-center items-center h-64", children: _jsx("div", { className: "animate-spin rounded-full h-8 w-8 border-t-2 border-primary" }) }));
    }
    if (!results || results.length === 0) {
        return (_jsx("div", { className: "flex justify-center items-center h-64 text-muted-foreground", children: _jsx("p", { children: "\uBD84\uC11D \uACB0\uACFC\uB97C \uD45C\uC2DC\uD560 \uC778\uC6A9\uBB38\uC774 \uC5C6\uC2B5\uB2C8\uB2E4." }) }));
    }
    return (_jsx("div", { className: "space-y-3", children: results.map((result) => (_jsxs("div", { onClick: () => onQuoteClick(result.id), className: clsx("p-4 border border-border rounded-lg hover:bg-secondary cursor-pointer transition-colors"), children: [_jsxs("div", { className: "flex justify-between items-start gap-2 mb-2", children: [_jsxs("p", { className: "text-sm font-medium text-foreground flex-1 line-clamp-2", children: ["\"", result.quote, "\""] }), _jsxs("span", { className: clsx("text-xs font-semibold px-2 py-1 rounded whitespace-nowrap", result.similarity_score >= 70
                                ? "bg-green-100 text-green-800"
                                : result.similarity_score >= 50
                                    ? "bg-blue-100 text-blue-800"
                                    : "bg-orange-100 text-orange-800"), children: [result.similarity_score, "%"] })] }), _jsxs("p", { className: "text-xs text-muted-foreground truncate", children: ["\uCD9C\uCC98: ", result.source] })] }, result.id))) }));
};
