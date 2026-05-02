import { type FormEvent, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { confirmSignUp, resendSignUpCode } from "aws-amplify/auth";

import { ErrorMessage } from "../components/ErrorMessage";
import {
  PageActions,
  PageHeader,
  PageLayout,
  Panel
} from "../components/LayoutPrimitives";
import { SuccessMessage } from "../components/SuccessMessage";

type LocationState = {
  username?: string;
};

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

const primaryButtonClassName =
  "inline-flex w-fit rounded-md bg-slate-900 px-3 py-1.5 text-sm font-semibold text-white hover:bg-slate-800 hover:text-white focus:outline-none focus:ring-2 focus:ring-slate-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60";

const secondaryButtonClassName =
  "inline-flex w-fit rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 hover:border-slate-400 hover:bg-slate-100 hover:text-slate-950 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60";

export function ConfirmRegisterPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const locationState = location.state as LocationState | null;
  const [username, setUsername] = useState(locationState?.username ?? "");
  const [confirmationCode, setConfirmationCode] = useState("");
  const [submitState, setSubmitState] = useState<SubmitState>(initialSubmitState);

  const isSubmitting = submitState.status === "submitting";
  const canResendCode = username.trim().length > 0 && !isSubmitting;

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
      // Cognito verifies the confirmation code. The frontend only forwards the
      // username and code collected from the user; it does not mark accounts as
      // verified by itself.
      await confirmSignUp({
        username: username.trim(),
        confirmationCode: confirmationCode.trim()
      });

      setSubmitState({
        status: "success",
        message: "Registration confirmed. You can log in now."
      });
      navigate("/login");
    } catch (error) {
      setSubmitState({
        status: "error",
        message: getAuthErrorMessage(error)
      });
    }
  };

  const handleResendCode = async () => {
    if (!canResendCode) {
      return;
    }

    setSubmitState({
      status: "submitting",
      message: null
    });

    try {
      // Resending also stays inside Cognito. This keeps email verification
      // behavior aligned with the User Pool configuration managed by Terraform.
      await resendSignUpCode({
        username: username.trim()
      });

      setSubmitState({
        status: "success",
        message: "Confirmation code sent."
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
          <h1>Confirm registration</h1>
          <p className="m-0 max-w-2xl text-sm leading-6 text-slate-600">
            Enter the code sent by Cognito to finish creating your account.
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
              <label className={labelClassName} htmlFor="confirm-username">
                Username
              </label>
              <input
                id="confirm-username"
                name="username"
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
                className={controlClassName}
              />
            </div>

            <div className={fieldClassName}>
              <label className={labelClassName} htmlFor="confirm-code">
                Confirmation code
              </label>
              <input
                id="confirm-code"
                name="confirmationCode"
                autoComplete="one-time-code"
                value={confirmationCode}
                onChange={(event) => setConfirmationCode(event.target.value)}
                required
                className={controlClassName}
              />
            </div>

            <PageActions>
              <button
                type="submit"
                disabled={isSubmitting}
                className={primaryButtonClassName}
              >
                {isSubmitting ? "Confirming..." : "Confirm registration"}
              </button>
              <button
                type="button"
                onClick={handleResendCode}
                disabled={!canResendCode}
                className={secondaryButtonClassName}
              >
                Resend code
              </button>
            </PageActions>
          </form>
        </Panel>

        {submitState.status === "error" ? (
          <ErrorMessage message={submitState.message} />
        ) : null}

        {submitState.status === "success" ? (
          <SuccessMessage message={submitState.message} />
        ) : null}

        <p className="m-0 text-sm text-slate-600">
          Already confirmed?{" "}
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

  return "Registration confirmation failed.";
}
