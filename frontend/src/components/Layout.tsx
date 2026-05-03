import { NavLink, Outlet } from "react-router-dom";

import { AuthNav } from "./AuthNav";
import { secondaryButtonClassName } from "./uiStyles";

export function Layout() {
  return (
    <div className="min-h-screen bg-sky-50/40 text-slate-950">
      <a
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-white focus:px-3 focus:py-2 focus:text-sm focus:font-semibold focus:text-blue-700 focus:shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        href="#main-content"
      >
        Skip to main content
      </a>
      <header className="border-b border-slate-200 bg-white shadow-sm">
        <nav
          aria-label="Primary navigation"
          className="mx-auto flex max-w-6xl flex-wrap items-center gap-4 px-4 py-3"
        >
          <div className="flex flex-wrap items-center gap-2">
            {/* These links are React routes. BrowserRouter adds /app in the
                address bar, so /events here renders as /app/events. */}
            <NavLink className={getNavLinkClassName} to="/events">
              Events
            </NavLink>
            <NavLink className={getNavLinkClassName} to="/my-events">
              My events
            </NavLink>
            <NavLink className={getCreateEventLinkClassName} to="/create-event">
              Create event
            </NavLink>
          </div>

          <div className="ml-auto flex items-center">
            <AuthNav />
          </div>
        </nav>
      </header>

      <main
        id="main-content"
        className="mx-auto max-w-6xl px-4 py-6 sm:py-8"
      >
        <Outlet />
      </main>
    </div>
  );
}

function getNavLinkClassName({ isActive }: { isActive: boolean }): string {
  const baseClassName =
    "rounded-md px-2.5 py-1.5 text-sm font-medium hover:bg-slate-100 hover:text-blue-700";

  return isActive
    ? `${baseClassName} bg-blue-50 text-blue-700`
    : `${baseClassName} text-slate-700`;
}

function getCreateEventLinkClassName(): string {
  return secondaryButtonClassName;
}
