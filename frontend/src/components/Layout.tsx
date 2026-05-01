import { Link, Outlet } from "react-router-dom";

import { AuthNav } from "./AuthNav";

export function Layout() {
  return (
    <>
      <header className="border-b border-slate-200 bg-white">
        <nav
          aria-label="Primary navigation"
          className="mx-auto flex max-w-6xl flex-wrap items-center gap-3 px-4 py-3"
        >
          <div className="flex flex-wrap items-center gap-3">
            {/* These links are React routes. BrowserRouter adds /app in the
                address bar, so /events here renders as /app/events. */}
            <Link
              className="rounded-md px-2 py-1 font-semibold text-slate-950 hover:bg-slate-100 hover:text-blue-700"
              to="/events"
            >
              Events
            </Link>
            <Link
              className="rounded-md px-2 py-1 font-medium text-slate-700 hover:bg-slate-100 hover:text-blue-700"
              to="/my-events"
            >
              My events
            </Link>
            <Link
              className="rounded-md px-2 py-1 font-medium text-slate-700 hover:bg-slate-100 hover:text-blue-700"
              to="/create-event"
            >
              Create event
            </Link>
          </div>

          <div className="ml-auto">
            <AuthNav />
          </div>
        </nav>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6 sm:py-8">
        <Outlet />
      </main>
    </>
  );
}
