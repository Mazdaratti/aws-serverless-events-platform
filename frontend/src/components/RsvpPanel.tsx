import { useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { getApiErrorMessage } from "../api/errors";
import { rsvpToEvent } from "../api/events";
import type { RsvpResponse } from "../api/types";
import { useAuth } from "../auth/AuthProvider";
import { getAnonymousRsvpToken } from "../utils/anonymousRsvpToken";
import { ErrorMessage } from "./ErrorMessage";
import { LoadingState } from "./LoadingState";
import { SuccessMessage } from "./SuccessMessage";
import {
  primaryButtonClassName,
  secondaryButtonClassName,
  textLinkClassName
} from "./uiStyles";

type RsvpAccessLevel = "public" | "protected" | "admin";

interface RsvpPanelProps {
  accessLevel?: RsvpAccessLevel;
  eventId: string;
  onRsvpSuccess?: (response: RsvpResponse) => void;
}

type SubmitState =
  | { status: "idle"; message: null }
  | { status: "submitting"; message: null }
  | { status: "success"; message: string }
  | { status: "error"; message: string };

const initialSubmitState: SubmitState = {
  status: "idle",
  message: null
};

const rsvpDescriptionId = "rsvp-description";
const rsvpHeadingId = "rsvp-heading";

export function RsvpPanel({
  accessLevel = "public",
  eventId,
  onRsvpSuccess
}: RsvpPanelProps) {
  const location = useLocation();
  const { status: authStatus } = useAuth();
  const returnPath = `${location.pathname}${location.search}${location.hash}`;
  const [submitState, setSubmitState] = useState<SubmitState>(initialSubmitState);

  const isSessionLoading = authStatus === "loading";
  const isSubmitting = submitState.status === "submitting";
  const isBusy = isSessionLoading || isSubmitting;
  const isDisabled = isSubmitting || isSessionLoading;

  const submitRsvp = async (attending: boolean) => {
    if (isDisabled) {
      return;
    }

    setSubmitState({
      status: "submitting",
      message: null
    });

    try {
      // RSVP is mixed-mode. Authenticated users must not send anonymous_token;
      // anonymous/expired browser sessions must send one so the backend can
      // build a stable anonymous RSVP subject.
      const response = await rsvpToEvent(eventId, {
        attending,
        ...(authStatus === "authenticated"
          ? {}
          : { anonymous_token: getAnonymousRsvpToken() })
      });

      setSubmitState({
        status: "success",
        message: buildSuccessMessage(response)
      });

      // Backend response is the source of truth for updated counters. Let the
      // parent update its event summary state without making this panel own it.
      onRsvpSuccess?.(response);
    } catch (error) {
      // Preserve backend distinctions such as 400 full/past/cancelled, 403
      // forbidden, and 404 missing event. The API client keeps those messages.
      setSubmitState({
        status: "error",
        message: getApiErrorMessage(error)
      });
    }
  };

  return (
    <section
      aria-busy={isBusy}
      aria-describedby={rsvpDescriptionId}
      aria-labelledby={rsvpHeadingId}
      className="grid gap-4 rounded-lg border border-slate-200 bg-white p-4 shadow-[0_1px_2px_rgba(0,0,0,0.04)]"
    >
      <div>
        <h2
          id={rsvpHeadingId}
          className="m-0 text-lg font-semibold leading-tight text-slate-900"
        >
          RSVP
        </h2>
        <p id={rsvpDescriptionId} className="mt-1 text-sm text-slate-600">
          Let the organizer know whether you plan to attend.
        </p>
      </div>

      {isSessionLoading ? (
        <LoadingState message="Checking session before RSVP..." />
      ) : null}

      {authStatus === "anonymous" && accessLevel === "public" ? (
        <p className="m-0 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-600">
          You can RSVP anonymously, but you need an account if you want future
          event update or cancellation notifications.
        </p>
      ) : null}

      {authStatus === "anonymous" && accessLevel === "protected" ? (
        <p className="m-0 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-600">
          Sign in to RSVP to this protected event.{" "}
          <Link
            className={textLinkClassName}
            state={{ from: returnPath }}
            to="/login"
          >
            Login
          </Link>
        </p>
      ) : null}

      {authStatus === "anonymous" && accessLevel === "admin" ? (
        <p className="m-0 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-600">
          Admin access is required to RSVP to this event.{" "}
          <Link
            className={textLinkClassName}
            state={{ from: returnPath }}
            to="/login"
          >
            Login
          </Link>
        </p>
      ) : null}

      {authStatus === "expired" ? (
        <p className="m-0 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-600">
          Your session has expired. Sign in again to continue, or RSVP
          anonymously where the event allows it.
        </p>
      ) : null}

      <div
        aria-label="RSVP options"
        className="flex flex-wrap items-center gap-2"
        role="group"
      >
        <button
          type="button"
          disabled={isDisabled}
          onClick={() => void submitRsvp(true)}
          className={primaryButtonClassName}
        >
          Attending
        </button>
        <button
          type="button"
          disabled={isDisabled}
          onClick={() => void submitRsvp(false)}
          className={secondaryButtonClassName}
        >
          Not attending
        </button>
      </div>

      {submitState.status === "error" ? (
        <ErrorMessage message={submitState.message} />
      ) : null}

      {submitState.status === "success" ? (
        <SuccessMessage message={submitState.message} />
      ) : null}
    </section>
  );
}

function buildSuccessMessage(response: RsvpResponse): string {
  const action = response.operation === "created" ? "created" : "updated";
  const attendance = response.item.attending ? "attending" : "not attending";

  return `RSVP ${action}: ${attendance}.`;
}
