import { useState } from "react";

import { getApiErrorMessage } from "../api/errors";
import { rsvpToEvent } from "../api/events";
import type { RsvpResponse } from "../api/types";
import { useAuth } from "../auth/AuthProvider";
import { getAnonymousRsvpToken } from "../utils/anonymousRsvpToken";
import { ErrorMessage } from "./ErrorMessage";
import { LoadingState } from "./LoadingState";
import { SuccessMessage } from "./SuccessMessage";

interface RsvpPanelProps {
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

const primaryRsvpButtonClassName =
  "rounded-md bg-slate-900 px-3 py-1.5 text-sm font-semibold text-white hover:bg-slate-800 hover:text-white focus:outline-none focus:ring-2 focus:ring-slate-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60";

const secondaryRsvpButtonClassName =
  "rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 hover:border-slate-400 hover:bg-slate-100 hover:text-slate-950 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60";

export function RsvpPanel({ eventId, onRsvpSuccess }: RsvpPanelProps) {
  const { status: authStatus } = useAuth();
  const [submitState, setSubmitState] = useState<SubmitState>(initialSubmitState);

  const isSessionLoading = authStatus === "loading";
  const isSubmitting = submitState.status === "submitting";
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
      aria-labelledby="rsvp-heading"
      className="grid gap-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
    >
      <div>
        <h2
          id="rsvp-heading"
          className="m-0 text-lg font-semibold leading-tight text-slate-900"
        >
          RSVP
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          Let the organizer know whether you plan to attend.
        </p>
      </div>

      {isSessionLoading ? (
        <LoadingState message="Checking session before RSVP..." />
      ) : null}

      {authStatus === "anonymous" ? (
        <p className="m-0 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-600">
          You can RSVP anonymously, but you need an account if you want future
          event update or cancellation notifications.
        </p>
      ) : null}

      {authStatus === "expired" ? (
        <p className="m-0 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-600">
          Your session has expired. You can sign in again or RSVP anonymously
          where the event allows it.
        </p>
      ) : null}

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          disabled={isDisabled}
          onClick={() => void submitRsvp(true)}
          className={primaryRsvpButtonClassName}
        >
          Attending
        </button>
        <button
          type="button"
          disabled={isDisabled}
          onClick={() => void submitRsvp(false)}
          className={secondaryRsvpButtonClassName}
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
