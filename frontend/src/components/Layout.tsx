import { Link, Outlet } from "react-router-dom";

import { AuthNav } from "./AuthNav";

export function Layout() {
  return (
    <>
      <header>
        <nav aria-label="Primary navigation">
          {/* These links are React routes. BrowserRouter adds /app in the
              address bar, so /events here renders as /app/events. */}
          <Link to="/events">Events</Link>{" "}
          <Link to="/create-event">Create event</Link>{" "}
          <AuthNav />
        </nav>
      </header>

      <main>
        <Outlet />
      </main>
    </>
  );
}
