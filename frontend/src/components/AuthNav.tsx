import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";
import { LoadingState } from "./LoadingState";
import { StatusMessage } from "./StatusMessage";

export function AuthNav() {
  const { logout, status, user } = useAuth();

  const handleLogout = () => {
    void logout();
  };

  if (status === "loading") {
    return <LoadingState message="Checking session..." />;
  }

  if (status === "authenticated" && user) {
    return (
      <div className="flex flex-wrap items-center gap-2">
        {/* Display username for convenience only. Backend authorization still
            comes from Cognito tokens and server-side checks, not UI state. */}
        <span className="text-sm text-slate-600">
          Signed in as{" "}
          <span className="font-medium text-slate-800">{user.username}</span>
        </span>
        <button
          className="rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-sm font-medium text-slate-700 hover:border-blue-300 hover:text-blue-700"
          type="button"
          onClick={handleLogout}
        >
          Logout
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {/* Expired is different from anonymous: the user had a session, but it no
          longer has the token type the backend authorizers validate. */}
      {status === "expired" ? (
        <StatusMessage message="Session expired" />
      ) : null}
      <Link
        className="rounded-md px-2.5 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100 hover:text-blue-700"
        to="/login"
      >
        Login
      </Link>
      <Link
        className="rounded-md bg-blue-600 px-2.5 py-1.5 text-sm font-semibold text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        to="/register"
      >
        Register
      </Link>
    </div>
  );
}
