import React from "react";
import ReactDOM from "react-dom/client";
import "./styles/globals.css";

const App = () => (
  <div className="p-4 text-center">
    <h1>Quote Origin Pipeline</h1>
    <p>사이드 패널을 확인해주세요.</p>
  </div>
);

const root = ReactDOM.createRoot(document.getElementById("app")!);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
