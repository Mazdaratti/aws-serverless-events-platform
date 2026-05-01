import { NavLink, Outlet } from "react-router-dom";

import { AuthNav } from "./AuthNav";

export function Layout() {
  return (
    <>
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

      <main className="mx-auto max-w-6xl px-4 py-6 sm:py-8">
        <Outlet />
      </main>
    </>
  );
}

function getNavLinkClassName({ isActive }: { isActive: boolean }): string {
  const baseClassName =
    "rounded-md px-2.5 py-1.5 text-sm font-medium hover:bg-slate-100 hover:text-slate-950";

  return isActive
    ? `${baseClassName} bg-slate-100 text-slate-950`
    : `${baseClassName} text-slate-700`;
}

function getCreateEventLinkClassName(): string {
  return "rounded-md bg-slate-900 px-3 py-1.5 text-sm font-semibold text-white hover:bg-slate-800 hover:text-white focus:outline-none focus:ring-2 focus:ring-slate-500 focus:ring-offset-2";
}
