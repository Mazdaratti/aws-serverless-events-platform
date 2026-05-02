import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getApiErrorMessage } from "../api/errors";
import { getEvent } from "../api/events";
import type { PublicEvent, RsvpResponse } from "../api/types";
import { ErrorMessage } from "../components/ErrorMessage";
import {
  PageActions,
  PageHeader,
  PageLayout,
  Panel
} from "../components/LayoutPrimitives";
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
      <PageLayout>
        <ErrorMessage message={state.message} />
        <PageActions>
          <Link
            className="text-sm font-medium text-slate-700 hover:text-slate-950"
            to="/events"
          >
            Back to events
          </Link>
        </PageActions>
      </PageLayout>
    );
  }

  const event = state.event;
  const visibilityLabel = getVisibilityLabel(event);

  return (
    <PageLayout>
      <PageHeader>
        <div>
          <p className="m-0">
            <Link
              className="text-sm font-medium text-slate-700 hover:text-slate-950"
              to="/events"
            >
              Back to events
            </Link>
          </p>
          <h1>{event.title || "Untitled event"}</h1>
          <p className="m-0 max-w-2xl text-sm leading-6 text-slate-600">
            {formatEventDate(event.date)} at{" "}
            {event.location || "location not specified"}
          </p>
        </div>

        <PageActions>
          {/* This link is only a management shortcut. The edit page and backend
              still decide whether the current caller can update this event. */}
          <Link
            className="text-sm font-medium text-slate-700 hover:text-slate-950"
            to={`/events/${event.event_id}/edit`}
          >
            Edit event
          </Link>
          {/* RSVP-list access is also backend-authorized. The frontend link is
              just a shortcut for creators/admins who are allowed through. */}
          <Link
            className="text-sm font-medium text-slate-700 hover:text-slate-950"
            to={`/events/${event.event_id}/rsvps`}
          >
            View RSVPs
          </Link>
        </PageActions>
      </PageHeader>

      <div className="grid max-w-4xl gap-6">
        <Panel>
          {/* Visibility labels explain the public DTO flags in user-facing terms.
              Backend authorization is still the source of truth for what actions
              are actually allowed. */}
          <p aria-label="Event visibility" className="m-0">
            <strong className="inline-flex w-fit rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-700">
              {visibilityLabel}
            </strong>
          </p>

          <dl className="m-0 mt-4 grid gap-y-2.5 text-sm sm:grid-cols-[minmax(7rem,max-content)_minmax(0,1fr)] sm:gap-x-4">
            <dt className="font-semibold text-slate-500">Date</dt>
            <dd className="m-0 min-w-0 break-words text-slate-700">
              {formatEventDate(event.date)}
            </dd>

            <dt className="font-semibold text-slate-500">Location</dt>
            <dd className="m-0 min-w-0 break-words text-slate-700">
              {event.location || "Location not specified"}
            </dd>

            <dt className="font-semibold text-slate-500">Description</dt>
            <dd className="m-0 min-w-0 break-words text-slate-700">
              {event.description || "No description provided."}
            </dd>

            <dt className="font-semibold text-slate-500">Capacity</dt>
            <dd className="m-0 min-w-0 break-words text-slate-700">
              {event.capacity === null ? "Unlimited" : event.capacity}
            </dd>

            <dt className="font-semibold text-slate-500">RSVPs</dt>
            <dd className="m-0 min-w-0 break-words text-slate-700">
              {event.attending_count} attending / {event.rsvp_count} total
            </dd>
          </dl>
        </Panel>

        <RsvpPanel
          eventId={event.event_id}
          onRsvpSuccess={handleRsvpSuccess}
        />
      </div>
    </PageLayout>
  );
}
