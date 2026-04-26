import { Link, Navigate, Route, Routes } from "react-router-dom";

// Temporary route content keeps the router working while each page is promoted
// into a real component during the frontend foundation build-out.
function PlaceholderPage({ title }: { title: string }) {
  return (
    <main>
      <h1>{title}</h1>
    </main>
  );
}

export function App() {
  return (
    <>
      <header>
        <nav aria-label="Primary navigation">
          <Link to="/events">Events</Link>
          <Link to="/login">Login</Link>
          <Link to="/register">Register</Link>
        </nav>
      </header>

      {/* These are internal React routes. BrowserRouter adds /app in the
          address bar, so this /events route renders at /app/events. API calls
          are different: fetch must still call same-origin /events, not
          /app/events. */}
      <Routes>
        <Route path="/" element={<Navigate to="/events" replace />} />
        <Route path="/events" element={<PlaceholderPage title="Events" />} />
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
      </Routes>
    </>
  );
}
