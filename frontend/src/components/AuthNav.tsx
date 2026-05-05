import { Link, useLocation } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";
import { LoadingState } from "./LoadingState";
import { StatusMessage } from "./StatusMessage";
import { secondaryButtonClassName, textLinkClassName } from "./uiStyles";

export function AuthNav() {
  const location = useLocation();
  const { logout, status, user } = useAuth();
  const returnPath = `${location.pathname}${location.search}${location.hash}`;
  const authLinkState = { from: returnPath };

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
          className={secondaryButtonClassName}
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
        className={`px-1.5 py-1 text-sm ${textLinkClassName}`}
        state={authLinkState}
        to="/login"
      >
        Login
      </Link>
      <Link
        className={secondaryButtonClassName}
        state={authLinkState}
        to="/register"
      >
        Register
      </Link>
    </div>
  );
}
