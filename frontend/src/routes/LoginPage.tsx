import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { signIn } from "aws-amplify/auth";

import { useAuth } from "../auth/AuthProvider";
import { ErrorMessage } from "../components/ErrorMessage";
import { SuccessMessage } from "../components/SuccessMessage";

type SubmitState =
  | { status: "idle"; message: null }
  | { status: "submitting"; message: null }
  | { status: "success"; message: string }
  | { status: "error"; message: string };

const initialSubmitState: SubmitState = {
  status: "idle",
  message: null
};

export function LoginPage() {
  const navigate = useNavigate();
  const { refreshSession } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitState, setSubmitState] = useState<SubmitState>(initialSubmitState);

  const isSubmitting = submitState.status === "submitting";

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (isSubmitting) {
      return;
    }

    setSubmitState({
      status: "submitting",
      message: null
    });

    try {
      // Cognito is the source of truth for login. The frontend collects the
      // username/password, but it never creates identity or authorization state
      // locally.
      const result = await signIn({
        username: username.trim(),
        password
      });

      if (!result.isSignedIn) {
        setSubmitState({
          status: "error",
          message:
            "Sign-in requires another Cognito step. Use registration confirmation if your account is not confirmed."
        });
        return;
      }

      // Refresh the shared auth context after Cognito signs in so navigation
      // and API token helpers see the new browser session.
      await refreshSession();

      setSubmitState({
        status: "success",
        message: "Signed in."
      });
      navigate("/events");
    } catch (error) {
      setSubmitState({
        status: "error",
        message: getAuthErrorMessage(error)
      });
    }
  };

  return (
    <>
      <h1>Login</h1>

      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="login-username">Username</label>
          <input
            id="login-username"
            name="username"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
          />
        </div>

        <div>
          <label htmlFor="login-password">Password</label>
          <input
            id="login-password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </div>

        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Signing in..." : "Login"}
        </button>
      </form>

      {submitState.status === "error" ? (
        <ErrorMessage message={submitState.message} />
      ) : null}

      {submitState.status === "success" ? (
        <SuccessMessage message={submitState.message} />
      ) : null}

      <p>
        Need an account? <Link to="/register">Register</Link>
      </p>
    </>
  );
}

// Amplify Auth errors are not API responses. Keep this helper local so Cognito
// form handling stays separate from backend /events error handling.
function getAuthErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return "Authentication failed.";
}
