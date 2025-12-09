import { jsx as _jsx } from "react/jsx-runtime";
import React from "react";
import ReactDOM from "react-dom/client";
import { SidePanel } from "./components/SidePanel";
import "./styles/globals.css";
const root = ReactDOM.createRoot(document.getElementById("app"));
root.render(_jsx(React.StrictMode, { children: _jsx(SidePanel, {}) }));
