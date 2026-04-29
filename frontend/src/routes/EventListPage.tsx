import { useEffect, useState } from "react";

import { getApiErrorMessage } from "../api/errors";
import { listEvents } from "../api/events";
import type { NextCursor, PublicEvent } from "../api/types";
import { EventCard } from "../components/EventCard";
import { ErrorMessage } from "../components/ErrorMessage";
import { LoadingState } from "../components/LoadingState";
import {
  applyEventListControls,
  hasActiveEventListControls,
  publicEventListDefaultControls,
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

const initialState: LoadState = {
  status: "loading",
  items: [],
  nextCursor: null
};

export function EventListPage() {
  const [state, setState] = useState<LoadState>(initialState);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [controls, setControls] = useState<EventListControls>(publicEventListDefaultControls);

  useEffect(() => {
    const controller = new AbortController();

    async function loadInitialEvents() {
      try {
        // This route is public, so listEvents uses authMode: "none" under the
        // hood and never sends a Cognito token.
        const response = await listEvents({}, controller.signal);

        setState({
          status: "ready",
          items: response.items,
          nextCursor: response.next_cursor
        });
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }

        setState({
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
  }, []);

  const loadMore = async () => {
    if (!state.nextCursor || isLoadingMore) {
      return;
    }

    setIsLoadingMore(true);

    try {
      // next_cursor is opaque. This page only stores it and sends it back
      // through listEvents(); it never tries to decode backend pagination state.
      const response = await listEvents({ nextCursor: state.nextCursor });

      setState({
        status: "ready",
        items: [...state.items, ...response.items],
        nextCursor: response.next_cursor
      });
    } catch (error) {
      setState({
        status: "error",
        items: state.items,
        nextCursor: state.nextCursor,
        message: getApiErrorMessage(error)
      });
    } finally {
      setIsLoadingMore(false);
    }
  };

  // Filtering and sorting are intentionally client-side only. The API request
  // still loads the same public event pages; these controls only rearrange the
  // events already present in local component state.
  const visibleEvents = applyEventListControls(state.items, controls);
  const hasActiveControls = hasActiveEventListControls(
    controls,
    publicEventListDefaultControls
  );

  return (
    <>
      <h1>Events</h1>

      <EventListControlsForm controls={controls} setControls={setControls} />

      {hasActiveControls ? (
        <button
          type="button"
          onClick={() => setControls(publicEventListDefaultControls)}
        >
          Reset controls
        </button>
      ) : null}

      {state.status === "loading" ? (
        <LoadingState message="Loading events..." />
      ) : null}

      {state.status === "error" ? (
        <ErrorMessage message={state.message} />
      ) : null}

      {state.status !== "loading" ? (
        <p>
          Showing {visibleEvents.length} of {state.items.length} loaded events.
        </p>
      ) : null}

      {state.items.length === 0 && state.status !== "loading" ? (
        <p>No events found.</p>
      ) : null}

      {state.items.length > 0 && visibleEvents.length === 0 ? (
        <p>No events match the current controls.</p>
      ) : null}

      <ul>
        {visibleEvents.map((event) => (
          <li key={event.event_id}>
            <EventCard event={event} />
          </li>
        ))}
      </ul>

      {state.nextCursor ? (
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

interface EventListControlsFormProps {
  controls: EventListControls;
  setControls: (controls: EventListControls) => void;
}

function EventListControlsForm({
  controls,
  setControls
}: EventListControlsFormProps) {
  return (
    <section aria-labelledby="event-list-controls">
      <h2 id="event-list-controls">Find events</h2>

      <div>
        <label htmlFor="event-search">Search</label>
        <input
          id="event-search"
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
        <label htmlFor="event-state-filter">Event state</label>
        <select
          id="event-state-filter"
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
        <label htmlFor="event-visibility-filter">Visibility</label>
        <select
          id="event-visibility-filter"
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
        <label htmlFor="event-capacity-filter">RSVP availability</label>
        <select
          id="event-capacity-filter"
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
        <label htmlFor="event-sort">Sort</label>
        <select
          id="event-sort"
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
