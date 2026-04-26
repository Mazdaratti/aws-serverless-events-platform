import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getApiErrorMessage } from "../api/errors";
import { getEvent } from "../api/events";
import type { PublicEvent, RsvpResponse } from "../api/types";
import { RsvpPanel } from "../components/RsvpPanel";

type LoadState =
  | { status: "loading"; event: null }
  | { status: "ready"; event: PublicEvent }
  | { status: "error"; event: null; message: string };

const initialState: LoadState = {
  status: "loading",
  event: null
};

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
    return <p>Loading event...</p>;
  }

  if (state.status === "error") {
    return (
      <>
        <p role="alert">{state.message}</p>
        <Link to="/events">Back to events</Link>
      </>
    );
  }

  const event = state.event;

  return (
    <>
      <Link to="/events">Back to events</Link>
      <h1>{event.title}</h1>
      <dl>
        <dt>Date</dt>
        <dd>{new Date(event.date).toLocaleString()}</dd>
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
