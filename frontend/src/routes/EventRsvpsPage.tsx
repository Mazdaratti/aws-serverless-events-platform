import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getApiErrorMessage } from "../api/errors";
import { getEventRsvps } from "../api/events";
import type {
  EventRsvpsResponse,
  NextCursor,
  RsvpSubject
} from "../api/types";
import { useAuth } from "../auth/AuthProvider";
import { ErrorMessage } from "../components/ErrorMessage";
import { LoadingState } from "../components/LoadingState";
import { StatusMessage } from "../components/StatusMessage";
import { formatEventDate } from "../utils/dates";

type RsvpListItem = EventRsvpsResponse["items"][number];

type LoadState =
  | {
      status: "loading";
      response: null;
      nextCursor: NextCursor;
    }
  | {
      status: "ready";
      response: EventRsvpsResponse;
      nextCursor: NextCursor;
    }
  | {
      status: "error";
      response: EventRsvpsResponse | null;
      nextCursor: NextCursor;
      message: string;
    };

const initialLoadState: LoadState = {
  status: "loading",
  response: null,
  nextCursor: null
};

export function EventRsvpsPage() {
  const { eventId } = useParams<{ eventId: string }>();
  const { status } = useAuth();
  const [loadState, setLoadState] = useState<LoadState>(initialLoadState);
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  useEffect(() => {
    if (status !== "authenticated") {
      return;
    }

    const controller = new AbortController();

    setLoadState(initialLoadState);

    async function loadInitialRsvps() {
      if (!eventId) {
        setLoadState({
          status: "error",
          response: null,
          nextCursor: null,
          message: "Event ID is missing from the route."
        });
        return;
      }

      try {
        // RSVP list access is intentionally backend-authorized. The frontend
        // requests the list for signed-in users, then displays the backend's
        // 403/404/business message if the caller is not allowed.
        const response = await getEventRsvps(eventId, {}, controller.signal);

        setLoadState({
          status: "ready",
          response,
          nextCursor: response.next_cursor
        });
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }

        setLoadState({
          status: "error",
          response: null,
          nextCursor: null,
          message: getApiErrorMessage(error)
        });
      }
    }

    void loadInitialRsvps();

    return () => {
      controller.abort();
    };
  }, [eventId, status]);

  const loadMore = async () => {
    if (!eventId || !loadState.nextCursor || !loadState.response || isLoadingMore) {
      return;
    }

    setIsLoadingMore(true);

    try {
      // The cursor is opaque DynamoDB pagination state wrapped by the backend.
      // The frontend should pass it back unchanged.
      const response = await getEventRsvps(eventId, {
        nextCursor: loadState.nextCursor
      });

      setLoadState({
        status: "ready",
        response: {
          ...response,
          items: [...loadState.response.items, ...response.items]
        },
        nextCursor: response.next_cursor
      });
    } catch (error) {
      setLoadState({
        status: "error",
        response: loadState.response,
        nextCursor: loadState.nextCursor,
        message: getApiErrorMessage(error)
      });
    } finally {
      setIsLoadingMore(false);
    }
  };

  if (status === "loading") {
    return <LoadingState message="Checking session..." />;
  }

  if (status !== "authenticated") {
    return (
      <>
        <h1>Event RSVPs</h1>
        {/* This is a UI prompt only. The protected API route is still the real
            source of truth for RSVP-list access. */}
        <StatusMessage message="You need to sign in before viewing RSVPs." />
        <p>
          <Link to="/login">Login</Link> or{" "}
          <Link to="/register">register</Link> to continue.
        </p>
      </>
    );
  }

  if (loadState.status === "loading") {
    return <LoadingState message="Loading RSVPs..." />;
  }

  if (loadState.status === "error" && !loadState.response) {
    return (
      <>
        <h1>Event RSVPs</h1>
        <ErrorMessage message={loadState.message} />
        <Link to={eventId ? `/events/${eventId}` : "/events"}>Back to event</Link>
      </>
    );
  }

  const response = loadState.response;

  if (!response) {
    return <ErrorMessage message="RSVP response is missing." />;
  }

  return (
    <>
      <h1>Event RSVPs</h1>
      <Link to={`/events/${response.event.event_id}`}>Back to event</Link>

      <section aria-labelledby="rsvp-event-summary">
        <h2 id="rsvp-event-summary">{response.event.title || "Untitled event"}</h2>
        <dl>
          <dt>Date</dt>
          <dd>{formatEventDate(response.event.date)}</dd>
          <dt>Status</dt>
          <dd>{response.event.status}</dd>
          <dt>Capacity</dt>
          <dd>{response.event.capacity === null ? "Unlimited" : response.event.capacity}</dd>
          <dt>RSVPs</dt>
          <dd>
            {response.stats.attending} attending / {response.stats.total} total
          </dd>
        </dl>
      </section>

      {loadState.status === "error" ? (
        <ErrorMessage message={loadState.message} />
      ) : null}

      {response.items.length === 0 ? (
        <StatusMessage message="No RSVPs yet." />
      ) : (
        <ul>
          {response.items.map((item) => (
            <li key={`${getSubjectKey(item.subject)}-${item.updated_at}`}>
              <RsvpListItemView item={item} />
            </li>
          ))}
        </ul>
      )}

      {loadState.nextCursor ? (
        <button
          type="button"
          disabled={isLoadingMore}
          onClick={() => void loadMore()}
        >
          {isLoadingMore ? "Loading..." : "Load more"}
        </button>
      ) : null}
    </>
  );
}

function RsvpListItemView({ item }: { item: RsvpListItem }) {
  return (
    <article>
      <h3>{getSubjectLabel(item.subject)}</h3>
      <dl>
        <dt>Status</dt>
        <dd>{item.attending ? "Attending" : "Not attending"}</dd>
        <dt>Created</dt>
        <dd>{formatEventDate(item.created_at)}</dd>
        <dt>Updated</dt>
        <dd>{formatEventDate(item.updated_at)}</dd>
      </dl>
    </article>
  );
}

function getSubjectLabel(subject: RsvpSubject): string {
  if (subject.anonymous) {
    return "Anonymous RSVP";
  }

  return subject.user_id ? `User ${subject.user_id}` : "Authenticated user";
}

function getSubjectKey(subject: RsvpSubject): string {
  if (subject.anonymous) {
    return "anonymous";
  }

  return subject.user_id ?? subject.type;
}
