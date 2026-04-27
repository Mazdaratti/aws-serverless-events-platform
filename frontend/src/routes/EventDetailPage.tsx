import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getApiErrorMessage } from "../api/errors";
import { getEvent } from "../api/events";
import type { PublicEvent, RsvpResponse } from "../api/types";
import { ErrorMessage } from "../components/ErrorMessage";
import { LoadingState } from "../components/LoadingState";
import { RsvpPanel } from "../components/RsvpPanel";
import { formatEventDate } from "../utils/dates";

type LoadState =
  | { status: "loading"; event: null }
  | { status: "ready"; event: PublicEvent }
  | { status: "error"; event: null; message: string };

const initialState: LoadState = {
  status: "loading",
  event: null
};

function getVisibilityLabel(event: PublicEvent): string {
  if (event.requires_admin) {
    return "Admin-only";
  }

  if (!event.is_public) {
    return "Protected";
  }

  return "Public";
}

export function EventDetailPage() {
  const { eventId } = useParams<{ eventId: string }>();
  const [state, setState] = useState<LoadState>(initialState);

  const handleRsvpSuccess = (response: RsvpResponse) => {
    setState((previousState) => {
      if (previousState.status !== "ready") {
        return previousState;
      }

      return {
        status: "ready",
        event: {
          ...previousState.event,
          rsvp_count: response.event_summary.rsvp_count,
          attending_count: response.event_summary.attending_count
        }
      };
    });
  };

  useEffect(() => {
    const controller = new AbortController();

    // Reset before each load so navigating between event pages does not briefly
    // show details from the previously viewed event.
    setState(initialState);

    async function loadEvent() {
      if (!eventId) {
        setState({
          status: "error",
          event: null,
          message: "Event ID is missing from the route."
        });
        return;
      }

      try {
        // Event detail reads are public in the current backend contract. The
        // event may be protected/admin-only for RSVP or mutation workflows, but
        // the read itself does not send a Cognito token.
        const response = await getEvent(eventId, controller.signal);

        setState({
          status: "ready",
          event: response.item
        });
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }

        setState({
          status: "error",
          event: null,
          message: getApiErrorMessage(error)
        });
      }
    }

    void loadEvent();

    return () => {
      controller.abort();
    };
  }, [eventId]);

  if (state.status === "loading") {
    return <LoadingState message="Loading event..." />;
  }

  if (state.status === "error") {
    return (
      <>
        <ErrorMessage message={state.message} />
        <Link to="/events">Back to events</Link>
      </>
    );
  }

  const event = state.event;
  const visibilityLabel = getVisibilityLabel(event);

  return (
    <>
      <Link to="/events">Back to events</Link>
      <h1>{event.title || "Untitled event"}</h1>
      {/* Visibility labels explain the public DTO flags in user-facing terms.
          Backend authorization is still the source of truth for what actions
          are actually allowed. */}
      <p aria-label="Event visibility">
        <strong>{visibilityLabel}</strong>
      </p>

      <dl>
        <dt>Date</dt>
        <dd>{formatEventDate(event.date)}</dd>
        <dt>Location</dt>
        <dd>{event.location}</dd>
        <dt>Description</dt>
        <dd>{event.description}</dd>
        <dt>Capacity</dt>
        <dd>{event.capacity === null ? "Unlimited" : event.capacity}</dd>
        <dt>RSVPs</dt>
        <dd>
          {event.attending_count} attending / {event.rsvp_count} total
        </dd>
      </dl>

      <RsvpPanel
        eventId={event.event_id}
        onRsvpSuccess={handleRsvpSuccess}
      />
    </>
  );
}
