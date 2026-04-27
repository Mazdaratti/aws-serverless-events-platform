import { type FormEvent, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { confirmSignUp, resendSignUpCode } from "aws-amplify/auth";

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
    <>
      <h1>Confirm registration</h1>

      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="confirm-username">Username</label>
          <input
            id="confirm-username"
            name="username"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
          />
        </div>

        <div>
          <label htmlFor="confirm-code">Confirmation code</label>
          <input
            id="confirm-code"
            name="confirmationCode"
            autoComplete="one-time-code"
            value={confirmationCode}
            onChange={(event) => setConfirmationCode(event.target.value)}
            required
          />
        </div>

        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Confirming..." : "Confirm registration"}
        </button>
        <button type="button" onClick={handleResendCode} disabled={!canResendCode}>
          Resend code
        </button>
      </form>

      {submitState.message ? (
        <p role={submitState.status === "error" ? "alert" : "status"}>
          {submitState.message}
        </p>
      ) : null}

      <p>
        Already confirmed? <Link to="/login">Login</Link>
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

  return "Registration confirmation failed.";
}
