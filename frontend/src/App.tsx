import {
  lazy,
  Suspense,
  type ReactNode
} from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { LoadingState } from "./components/LoadingState";

const ConfirmRegisterPage = lazy(() =>
  import("./routes/ConfirmRegisterPage").then((module) => ({
    default: module.ConfirmRegisterPage
  }))
);
const CreateEventPage = lazy(() =>
  import("./routes/CreateEventPage").then((module) => ({
    default: module.CreateEventPage
  }))
);
const EditEventPage = lazy(() =>
  import("./routes/EditEventPage").then((module) => ({
    default: module.EditEventPage
  }))
);
const EventDetailPage = lazy(() =>
  import("./routes/EventDetailPage").then((module) => ({
    default: module.EventDetailPage
  }))
);
const EventListPage = lazy(() =>
  import("./routes/EventListPage").then((module) => ({
    default: module.EventListPage
  }))
);
const EventRsvpsPage = lazy(() =>
  import("./routes/EventRsvpsPage").then((module) => ({
    default: module.EventRsvpsPage
  }))
);
const LoginPage = lazy(() =>
  import("./routes/LoginPage").then((module) => ({ default: module.LoginPage }))
);
const MyEventsPage = lazy(() =>
  import("./routes/MyEventsPage").then((module) => ({
    default: module.MyEventsPage
  }))
);
const NotFoundPage = lazy(() =>
  import("./routes/NotFoundPage").then((module) => ({
    default: module.NotFoundPage
  }))
);
const RegisterPage = lazy(() =>
  import("./routes/RegisterPage").then((module) => ({
    default: module.RegisterPage
  }))
);

export function App() {
  return (
    <Routes>
      {/* These are internal React routes. BrowserRouter adds /app in the
          address bar, so /events renders at /app/events. API calls are
          different: fetch must still call same-origin /events, not /app/events. */}
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/events" replace />} />
        <Route path="/events" element={withPageSuspense(<EventListPage />)} />
        <Route
          path="/create-event"
          element={withPageSuspense(<CreateEventPage />)}
        />
        <Route
          path="/events/:eventId"
          element={withPageSuspense(<EventDetailPage />)}
        />
        <Route
          path="/events/:eventId/edit"
          element={withPageSuspense(<EditEventPage />)}
        />
        <Route
          path="/events/:eventId/rsvps"
          element={withPageSuspense(<EventRsvpsPage />)}
        />
        <Route path="/my-events" element={withPageSuspense(<MyEventsPage />)} />
        <Route path="/login" element={withPageSuspense(<LoginPage />)} />
        <Route path="/register" element={withPageSuspense(<RegisterPage />)} />
        <Route
          path="/confirm-register"
          element={withPageSuspense(<ConfirmRegisterPage />)}
        />
        <Route path="*" element={withPageSuspense(<NotFoundPage />)} />
      </Route>
    </Routes>
  );
}

function withPageSuspense(children: ReactNode) {
  return (
    <Suspense fallback={<LoadingState message="Loading page..." />}>
      {children}
    </Suspense>
  );
}
