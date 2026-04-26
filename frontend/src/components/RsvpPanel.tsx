import { useState } from "react";

import { getApiErrorMessage } from "../api/errors";
import { rsvpToEvent } from "../api/events";
import type { RsvpResponse } from "../api/types";
import { useAuth } from "../auth/AuthProvider";
import { getAnonymousRsvpToken } from "../utils/anonymousRsvpToken";

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
    <section aria-labelledby="rsvp-heading">
      <h2 id="rsvp-heading">RSVP</h2>

      {isSessionLoading ? <p>Checking session before RSVP...</p> : null}

      {authStatus === "anonymous" ? (
        <p>
          You can RSVP anonymously, but you need an account if you want future
          event update or cancellation notifications.
        </p>
      ) : null}

      {authStatus === "expired" ? (
        <p>
          Your session has expired. You can sign in again or RSVP anonymously
          where the event allows it.
        </p>
      ) : null}

      <button
        type="button"
        disabled={isDisabled}
        onClick={() => void submitRsvp(true)}
      >
        Attending
      </button>{" "}
      <button
        type="button"
        disabled={isDisabled}
        onClick={() => void submitRsvp(false)}
      >
        Not attending
      </button>

      {submitState.message ? (
        <p role={submitState.status === "error" ? "alert" : "status"}>
          {submitState.message}
        </p>
      ) : null}
    </section>
  );
}

function buildSuccessMessage(response: RsvpResponse): string {
  const action = response.operation === "created" ? "created" : "updated";
  const attendance = response.item.attending ? "attending" : "not attending";

  return `RSVP ${action}: ${attendance}.`;
}
