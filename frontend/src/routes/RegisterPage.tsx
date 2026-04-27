import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { signUp } from "aws-amplify/auth";

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

export function RegisterPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitState, setSubmitState] = useState<SubmitState>(initialSubmitState);

  const isSubmitting = submitState.status === "submitting";

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (isSubmitting) {
      return;
    }

    const trimmedUsername = username.trim();
    const trimmedEmail = email.trim();

    setSubmitState({
      status: "submitting",
      message: null
    });

    try {
      // Cognito owns account creation and email verification. The frontend only
      // collects the fields required by the current User Pool baseline:
      // username, email, and password.
      const result = await signUp({
        username: trimmedUsername,
        password,
        options: {
          userAttributes: {
            email: trimmedEmail
          }
        }
      });

      if (result.isSignUpComplete) {
        setSubmitState({
          status: "success",
          message: "Registration complete. You can log in now."
        });
        navigate("/login");
        return;
      }

      // Most self-service signups need a confirmation code. Pass only the
      // username through router state so the confirmation page can prefill it;
      // never pass password or auth tokens between pages.
      navigate("/confirm-register", {
        state: {
          username: trimmedUsername
        }
      });
    } catch (error) {
      setSubmitState({
        status: "error",
        message: getAuthErrorMessage(error)
      });
    }
  };

  return (
    <>
      <h1>Register</h1>

      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="register-username">Username</label>
          <input
            id="register-username"
            name="username"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
          />
        </div>

        <div>
          <label htmlFor="register-email">Email</label>
          <input
            id="register-email"
            name="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </div>

        <div>
          <label htmlFor="register-password">Password</label>
          <input
            id="register-password"
            name="password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </div>

        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Registering..." : "Register"}
        </button>
      </form>

      {submitState.status === "error" ? (
        <ErrorMessage message={submitState.message} />
      ) : null}

      {submitState.status === "success" ? (
        <SuccessMessage message={submitState.message} />
      ) : null}

      <p>
        Already have an account? <Link to="/login">Login</Link>
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

  return "Registration failed.";
}
