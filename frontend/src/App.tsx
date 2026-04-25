import { Link, Navigate, Route, Routes } from "react-router-dom";

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

      {/* BrowserRouter adds /app to these UI routes. API calls must still use /events. */}
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
