import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";

export function AuthNav() {
  const { logout, status, user } = useAuth();

  const handleLogout = () => {
    void logout();
  };

  if (status === "loading") {
    return <span aria-live="polite">Checking session...</span>;
  }

  if (status === "authenticated" && user) {
    return (
      <>
        {/* Display username for convenience only. Backend authorization still
            comes from Cognito tokens and server-side checks, not UI state. */}
        <span>Signed in as {user.username}</span>{" "}
        <button type="button" onClick={handleLogout}>
          Logout
        </button>
      </>
    );
  }

  return (
    <>
      {/* Expired is different from anonymous: the user had a session, but it no
          longer has the token type the backend authorizers validate. */}
      {status === "expired" ? (
        <span aria-live="polite">Session expired</span>
      ) : null}{" "}
      <Link to="/login">Login</Link>{" "}
      <Link to="/register">Register</Link>
    </>
  );
}
