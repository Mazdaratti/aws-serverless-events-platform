import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { EventListPage } from "./routes/EventListPage";

// Temporary route content keeps the router working while each page is promoted
// into a real component during the frontend foundation build-out.
function PlaceholderPage({ title }: { title: string }) {
  return (
    <>
      <h1>{title}</h1>
    </>
  );
}

export function App() {
  return (
    <Routes>
      {/* These are internal React routes. BrowserRouter adds /app in the
          address bar, so /events renders at /app/events. API calls are
          different: fetch must still call same-origin /events, not /app/events. */}
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/events" replace />} />
        <Route path="/events" element={<EventListPage />} />
        <Route
          path="/events/:eventId"
          element={<PlaceholderPage title="Event details" />}
        />
        <Route path="/login" element={<PlaceholderPage title="Login" />} />
        <Route
          path="/register"
          element={<PlaceholderPage title="Register" />}
        />
        <Route
          path="/confirm-register"
          element={<PlaceholderPage title="Confirm registration" />}
        />
        <Route path="*" element={<PlaceholderPage title="Page not found" />} />
      </Route>
    </Routes>
  );
}
