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
        <StatusMessage message="Session expired" />
      ) : null}{" "}
      <Link to="/login">Login</Link>{" "}
      <Link to="/register">Register</Link>
    </>
  );
}
