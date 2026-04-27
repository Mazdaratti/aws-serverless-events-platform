import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  // Keep Vite's default root base for this app.
  //
  // Browser URLs live under /app because React Router uses basename="/app".
  // Build assets should stay at root paths such as /assets/... so CloudFront
  // treats them as real static files instead of SPA navigation routes.
  //
  // Do not set base: "/app/" here unless the deployment layout also changes.
  plugins: [react()]
});
