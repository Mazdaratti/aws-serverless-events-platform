import { StrictMode } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { App } from "./App";

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("React root element #root was not found in index.html.");
}

ReactDOM.createRoot(rootElement).render(
  <StrictMode>
    {/* CloudFront serves the SPA under /app, so React Router owns that browser
        prefix here. This does not change API paths: fetch calls still go to
        same-origin /events routes, not /app/events. */}
    <BrowserRouter basename="/app">
      <App />
    </BrowserRouter>
  </StrictMode>
);
