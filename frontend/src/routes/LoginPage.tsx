import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { signIn } from "aws-amplify/auth";

import { useAuth } from "../auth/AuthProvider";
import { ErrorMessage } from "../components/ErrorMessage";
import {
  PageHeader,
  PageLayout,
  Panel
} from "../components/LayoutPrimitives";
import { SuccessMessage } from "../components/SuccessMessage";
import {
  pageTitleClassName,
  primaryButtonClassName,
  textInputClassName,
  textLinkClassName
} from "../components/uiStyles";

type SubmitState =
  | { status: "idle"; message: null }
  | { status: "submitting"; message: null }
  | { status: "success"; message: string }
  | { status: "error"; message: string };

const initialSubmitState: SubmitState = {
  status: "idle",
  message: null
};

const fieldClassName = "grid gap-1.5";

const labelClassName = "text-sm font-semibold text-slate-700";

const loginErrorMessageId = "login-error-message";
const loginSuccessMessageId = "login-success-message";

export function LoginPage() {
  const navigate = useNavigate();
  const { refreshSession } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitState, setSubmitState] = useState<SubmitState>(initialSubmitState);

  const isSubmitting = submitState.status === "submitting";
  const feedbackMessageId =
    submitState.status === "error"
      ? loginErrorMessageId
      : submitState.status === "success"
        ? loginSuccessMessageId
        : undefined;
  const hasAuthError = submitState.status === "error";

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
    <PageLayout>
      <PageHeader>
        <div>
          <h1 className={pageTitleClassName}>Login</h1>
          <p className="m-0 max-w-2xl text-sm leading-6 text-slate-600">
            Sign in to manage your events and RSVP activity.
          </p>
        </div>
      </PageHeader>

      <div className="grid max-w-4xl gap-6">
        <Panel>
          <form
            aria-busy={isSubmitting}
            aria-describedby={feedbackMessageId}
            className="m-0 grid max-w-2xl gap-4 border-0 bg-transparent p-0"
            onSubmit={handleSubmit}
          >
            <div className={fieldClassName}>
              <label className={labelClassName} htmlFor="login-username">
                Username
              </label>
              <input
                id="login-username"
                name="username"
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
                aria-invalid={hasAuthError || undefined}
                className={textInputClassName}
              />
            </div>

            <div className={fieldClassName}>
              <label className={labelClassName} htmlFor="login-password">
                Password
              </label>
              <input
                id="login-password"
                name="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                aria-invalid={hasAuthError || undefined}
                className={textInputClassName}
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className={primaryButtonClassName}
            >
              {isSubmitting ? "Signing in..." : "Login"}
            </button>
          </form>
        </Panel>

        {submitState.status === "error" ? (
          <div id={loginErrorMessageId}>
            <ErrorMessage message={submitState.message} />
          </div>
        ) : null}

        {submitState.status === "success" ? (
          <div id={loginSuccessMessageId}>
            <SuccessMessage message={submitState.message} />
          </div>
        ) : null}

        <p className="m-0 text-sm text-slate-600">
          Need an account?{" "}
          <Link
            className={textLinkClassName}
            to="/register"
          >
            Register
          </Link>
        </p>
      </div>
    </PageLayout>
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
