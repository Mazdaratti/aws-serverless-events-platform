import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { ConfirmRegisterPage } from "./routes/ConfirmRegisterPage";
import { CreateEventPage } from "./routes/CreateEventPage";
import { EventDetailPage } from "./routes/EventDetailPage";
import { EventListPage } from "./routes/EventListPage";
import { LoginPage } from "./routes/LoginPage";
import { NotFoundPage } from "./routes/NotFoundPage";
import { RegisterPage } from "./routes/RegisterPage";

export function App() {
  return (
    <Routes>
      {/* These are internal React routes. BrowserRouter adds /app in the
          address bar, so /events renders at /app/events. API calls are
          different: fetch must still call same-origin /events, not /app/events. */}
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/events" replace />} />
        <Route path="/events" element={<EventListPage />} />
        <Route path="/create-event" element={<CreateEventPage />} />
        <Route path="/events/:eventId" element={<EventDetailPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/confirm-register" element={<ConfirmRegisterPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
