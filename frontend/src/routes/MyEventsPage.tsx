import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getApiErrorMessage } from "../api/errors";
import { cancelEvent, listMyEvents } from "../api/events";
import type { NextCursor, PublicEvent } from "../api/types";
import { useAuth } from "../auth/AuthProvider";
import { ErrorMessage } from "../components/ErrorMessage";
import { EventCard } from "../components/EventCard";
import { LoadingState } from "../components/LoadingState";
import { StatusMessage } from "../components/StatusMessage";
import { SuccessMessage } from "../components/SuccessMessage";
import {
  applyEventListControls,
  hasActiveEventListControls,
  myEventsDefaultControls,
  type EventListControls
} from "../utils/eventListControls";

type LoadState =
  | { status: "loading"; items: PublicEvent[]; nextCursor: NextCursor }
  | { status: "ready"; items: PublicEvent[]; nextCursor: NextCursor }
  | {
      status: "error";
      items: PublicEvent[];
      nextCursor: NextCursor;
      message: string;
    };

type CancelState =
  | { status: "idle"; eventId: null; message: null }
  | { status: "confirming"; eventId: string; message: null }
  | { status: "submitting"; eventId: string; message: null }
  | { status: "success"; eventId: null; message: string }
  | { status: "error"; eventId: string | null; message: string };

const initialLoadState: LoadState = {
  status: "loading",
  items: [],
  nextCursor: null
};

const initialCancelState: CancelState = {
  status: "idle",
  eventId: null,
  message: null
};

export function MyEventsPage() {
  const { status } = useAuth();
  const [loadState, setLoadState] = useState<LoadState>(initialLoadState);
  const [cancelState, setCancelState] = useState<CancelState>(initialCancelState);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [controls, setControls] = useState<EventListControls>(myEventsDefaultControls);

  useEffect(() => {
    if (status !== "authenticated") {
      return;
    }

    const controller = new AbortController();

    setLoadState(initialLoadState);
    setCancelState(initialCancelState);

    async function loadInitialEvents() {
      try {
        // My events is a protected API route. The API client attaches the
        // Cognito token and does not retry anonymously if auth fails.
        const response = await listMyEvents({}, controller.signal);

        setLoadState({
          status: "ready",
          items: response.items,
          nextCursor: response.next_cursor
        });
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }

        setLoadState({
          status: "error",
          items: [],
          nextCursor: null,
          message: getApiErrorMessage(error)
        });
      }
    }

    void loadInitialEvents();

    return () => {
      controller.abort();
    };
  }, [status]);

  const loadMore = async () => {
    if (!loadState.nextCursor || isLoadingMore) {
      return;
    }

    setIsLoadingMore(true);

    try {
      // next_cursor is opaque backend pagination state. The frontend stores it
      // and sends it back unchanged instead of decoding it.
      const response = await listMyEvents({
        nextCursor: loadState.nextCursor
      });

      setLoadState({
        status: "ready",
        items: [...loadState.items, ...response.items],
        nextCursor: response.next_cursor
      });
    } catch (error) {
      setLoadState({
        status: "error",
        items: loadState.items,
        nextCursor: loadState.nextCursor,
        message: getApiErrorMessage(error)
      });
    } finally {
      setIsLoadingMore(false);
    }
  };

  const startCancel = (eventId: string) => {
    setCancelState({
      status: "confirming",
      eventId,
      message: null
    });
  };

  const keepEvent = () => {
    setCancelState(initialCancelState);
  };

  const confirmCancel = async (eventId: string) => {
    if (cancelState.status === "submitting") {
      return;
    }

    setCancelState({
      status: "submitting",
      eventId,
      message: null
    });

    try {
      // Cancel uses the deployed POST /events/{event_id}/cancel route. The
      // frontend offers the workflow, but backend ownership/admin rules decide
      // whether the action is allowed.
      const response = await cancelEvent(eventId);

      setLoadState((currentState) => ({
        ...currentState,
        items: currentState.items.map((item) =>
          item.event_id === response.item.event_id ? response.item : item
        )
      }));
      setCancelState({
        status: "success",
        eventId: null,
        message: "Event cancelled."
      });
    } catch (error) {
      setCancelState({
        status: "error",
        eventId,
        message: getApiErrorMessage(error)
      });
    }
  };

  // My events uses the same client-side control rules as public discovery, but
  // its default keeps all owned events visible for management.
  const visibleEvents = applyEventListControls(loadState.items, controls);
  const hasActiveControls = hasActiveEventListControls(
    controls,
    myEventsDefaultControls
  );

  if (status === "loading") {
    return <LoadingState message="Checking session..." />;
  }

  if (status !== "authenticated") {
    return (
      <>
        <h1>My events</h1>
        {/* This is only a helpful UI boundary. API Gateway still protects the
            real GET /events/mine request. */}
        <StatusMessage message="You need to sign in before viewing your events." />
        <p>
          <Link to="/login">Login</Link> or{" "}
          <Link to="/register">register</Link> to continue.
        </p>
      </>
    );
  }

  return (
    <>
      <h1>My events</h1>
      <p>
        <Link to="/create-event">Create event</Link>
      </p>

      <MyEventsControlsForm controls={controls} setControls={setControls} />

      {hasActiveControls ? (
        <button
          type="button"
          onClick={() => setControls(myEventsDefaultControls)}
        >
          Reset controls
        </button>
      ) : null}

      {loadState.status === "loading" ? (
        <LoadingState message="Loading your events..." />
      ) : null}

      {loadState.status === "error" ? (
        <ErrorMessage message={loadState.message} />
      ) : null}

      {cancelState.status === "success" ? (
        <SuccessMessage message={cancelState.message} />
      ) : null}

      {cancelState.status === "error" ? (
        <ErrorMessage message={cancelState.message} />
      ) : null}

      {loadState.status !== "loading" ? (
        <p>
          Showing {visibleEvents.length} of {loadState.items.length} loaded events.
        </p>
      ) : null}

      {loadState.items.length === 0 && loadState.status !== "loading" ? (
        <StatusMessage message="No events yet." />
      ) : null}

      {loadState.items.length > 0 && visibleEvents.length === 0 ? (
        <StatusMessage message="No events match the current controls." />
      ) : null}

      <ul>
        {visibleEvents.map((event) => (
          <li key={event.event_id}>
            <EventCard event={event} />
            <p>
              <Link to={`/events/${event.event_id}/edit`}>Edit</Link> {" | "}
              {/* RSVP-list access is checked by the backend. This owner page
                  only provides a convenient management shortcut. */}
              <Link to={`/events/${event.event_id}/rsvps`}>View RSVPs</Link>
            </p>

            {event.status === "CANCELLED" ? (
              <StatusMessage message="This event is cancelled." />
            ) : cancelState.status === "confirming" &&
              cancelState.eventId === event.event_id ? (
              <p>
                Confirm cancellation?{" "}
                <button
                  type="button"
                  onClick={() => void confirmCancel(event.event_id)}
                >
                  Confirm cancel
                </button>{" "}
                <button type="button" onClick={keepEvent}>
                  Keep event
                </button>
              </p>
            ) : (
              <button type="button" onClick={() => startCancel(event.event_id)}>
                Cancel event
              </button>
            )}
          </li>
        ))}
      </ul>

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

interface MyEventsControlsFormProps {
  controls: EventListControls;
  setControls: (controls: EventListControls) => void;
}

function MyEventsControlsForm({
  controls,
  setControls
}: MyEventsControlsFormProps) {
  return (
    <section aria-labelledby="my-events-controls">
      <h2 id="my-events-controls">Find my events</h2>

      <div>
        <label htmlFor="my-events-search">Search</label>
        <input
          id="my-events-search"
          name="search"
          value={controls.search}
          onChange={(event) =>
            setControls({
              ...controls,
              search: event.target.value
            })
          }
          placeholder="Title, description, or location"
        />
      </div>

      <div>
        <label htmlFor="my-events-state-filter">Event state</label>
        <select
          id="my-events-state-filter"
          name="eventState"
          value={controls.eventState}
          onChange={(event) =>
            setControls({
              ...controls,
              eventState: event.target.value as EventListControls["eventState"]
            })
          }
        >
          <option value="all">All</option>
          <option value="ongoing">Ongoing</option>
          <option value="cancelled">Cancelled</option>
          <option value="outdated">Outdated</option>
        </select>
      </div>

      <div>
        <label htmlFor="my-events-visibility-filter">Visibility</label>
        <select
          id="my-events-visibility-filter"
          name="visibility"
          value={controls.visibility}
          onChange={(event) =>
            setControls({
              ...controls,
              visibility: event.target.value as EventListControls["visibility"]
            })
          }
        >
          <option value="all">All</option>
          <option value="public">Public</option>
          <option value="protected">Protected</option>
          <option value="admin">Admin-only</option>
        </select>
      </div>

      <div>
        <label htmlFor="my-events-capacity-filter">RSVP availability</label>
        <select
          id="my-events-capacity-filter"
          name="capacity"
          value={controls.capacity}
          onChange={(event) =>
            setControls({
              ...controls,
              capacity: event.target.value as EventListControls["capacity"]
            })
          }
        >
          <option value="all">All</option>
          <option value="unlimited">Unlimited capacity</option>
          <option value="limited">Has capacity limit</option>
          <option value="full">Full</option>
          <option value="available">Spots available</option>
        </select>
      </div>

      <div>
        <label htmlFor="my-events-sort">Sort</label>
        <select
          id="my-events-sort"
          name="sort"
          value={controls.sort}
          onChange={(event) =>
            setControls({
              ...controls,
              sort: event.target.value as EventListControls["sort"]
            })
          }
        >
          <option value="date-asc">Event date: soonest first</option>
          <option value="date-desc">Event date: latest first</option>
          <option value="title-asc">Title: A-Z</option>
          <option value="title-desc">Title: Z-A</option>
          <option value="status-active-first">Status: active first</option>
          <option value="status-cancelled-first">Status: cancelled first</option>
          <option value="created-desc">Created: newest first</option>
          <option value="created-asc">Created: oldest first</option>
        </select>
      </div>
    </section>
  );
}
