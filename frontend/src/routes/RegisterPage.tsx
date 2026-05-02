import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { signUp } from "aws-amplify/auth";

import { ErrorMessage } from "../components/ErrorMessage";
import {
  PageHeader,
  PageLayout,
  Panel
} from "../components/LayoutPrimitives";
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

const fieldClassName = "grid gap-1.5";

const labelClassName = "text-sm font-semibold text-slate-700";

const controlClassName =
  "min-h-10 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-slate-500 focus:ring-1 focus:ring-slate-400";

const submitButtonClassName =
  "inline-flex w-fit rounded-md bg-slate-900 px-3 py-1.5 text-sm font-semibold text-white hover:bg-slate-800 hover:text-white focus:outline-none focus:ring-2 focus:ring-slate-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60";

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
    <PageLayout>
      <PageHeader>
        <div>
          <h1>Register</h1>
          <p className="m-0 max-w-2xl text-sm leading-6 text-slate-600">
            Create an account to publish events and manage RSVPs.
          </p>
        </div>
      </PageHeader>

      <div className="grid max-w-4xl gap-6">
        <Panel>
          <form
            className="m-0 grid max-w-2xl gap-4 border-0 bg-transparent p-0"
            onSubmit={handleSubmit}
          >
            <div className={fieldClassName}>
              <label className={labelClassName} htmlFor="register-username">
                Username
              </label>
              <input
                id="register-username"
                name="username"
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
                className={controlClassName}
              />
            </div>

            <div className={fieldClassName}>
              <label className={labelClassName} htmlFor="register-email">
                Email
              </label>
              <input
                id="register-email"
                name="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
                className={controlClassName}
              />
            </div>

            <div className={fieldClassName}>
              <label className={labelClassName} htmlFor="register-password">
                Password
              </label>
              <input
                id="register-password"
                name="password"
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                className={controlClassName}
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className={submitButtonClassName}
            >
              {isSubmitting ? "Registering..." : "Register"}
            </button>
          </form>
        </Panel>

        {submitState.status === "error" ? (
          <ErrorMessage message={submitState.message} />
        ) : null}

        {submitState.status === "success" ? (
          <SuccessMessage message={submitState.message} />
        ) : null}

        <p className="m-0 text-sm text-slate-600">
          Already have an account?{" "}
          <Link
            className="font-medium text-slate-700 hover:text-slate-950"
            to="/login"
          >
            Login
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

  return "Registration failed.";
}
