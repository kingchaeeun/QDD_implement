import React from "react";
import ReactDOM from "react-dom/client";
import { SidePanel } from "./components/SidePanel";
import "./styles/globals.css";

const root = ReactDOM.createRoot(document.getElementById("app")!);
root.render(
  <React.StrictMode>
    <SidePanel />
  </React.StrictMode>
);
