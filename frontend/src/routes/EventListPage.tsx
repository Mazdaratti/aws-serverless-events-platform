import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getApiErrorMessage } from "../api/errors";
import { listEvents } from "../api/events";
import type { NextCursor, PublicEvent } from "../api/types";
import { EventCard } from "../components/EventCard";
import { ErrorMessage } from "../components/ErrorMessage";
import {
  ItemGrid,
  PageActions,
  PageHeader,
  PageLayout,
  Panel
} from "../components/LayoutPrimitives";
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

  const loadedEvents = state.items ?? [];

  const loadMore = async () => {
    if (!state.nextCursor || isLoadingMore) {
      return;
    }

    setIsLoadingMore(true);

    try {
      // next_cursor is opaque. This page only stores it and sends it back
      // through listEvents(); it never tries to decode backend pagination state.
      const response = await listEvents({ nextCursor: state.nextCursor });

      setState((prev) => ({
        status: "ready",
        items: [...(prev.items ?? []), ...(response.items ?? [])],
        nextCursor: response.next_cursor
      }));
    } catch (error) {
      setState((prev) => ({
        status: "error",
        items: prev.items ?? [],
        nextCursor: prev.nextCursor,
        message: getApiErrorMessage(error)
      }));
    } finally {
      setIsLoadingMore(false);
    }
  };

  // Filtering and sorting are intentionally client-side only. The API request
  // still loads the same public event pages; these controls only rearrange the
  // events already present in local component state.
  const visibleEvents = applyEventListControls(loadedEvents, controls);
  const hasActiveControls = hasActiveEventListControls(
    controls,
    publicEventListDefaultControls
  );

  if (state.status === "loading") {
    return <LoadingState message="Loading events..." />;
  }

  return (
    <PageLayout>
      <PageHeader>
        <div>
          <h1>Events</h1>
          <p className="m-0 max-w-2xl text-sm leading-6 text-slate-600">
            Discover upcoming events and narrow the list by status, visibility,
            availability, or date.
          </p>
        </div>

        <PageActions>
          {hasActiveControls ? (
            <button
              type="button"
              onClick={() => setControls(publicEventListDefaultControls)}
            >
              Reset controls
            </button>
          ) : null}
        </PageActions>
      </PageHeader>

      <EventListControlsForm controls={controls} setControls={setControls} />

      {state.status === "error" ? (
        <ErrorMessage message={state.message} />
      ) : null}

      <div className="border-t border-slate-200" />

      <div className="mt-5 grid gap-4">
        <p className="m-0 text-sm text-slate-500">
          Showing {visibleEvents.length} of {loadedEvents.length} loaded events.
        </p>
      </div>

      {loadedEvents.length === 0 ? (
        <Panel className="text-center">
          <p className="m-0 text-sm font-semibold text-slate-700">
            No events found.
          </p>
          <p className="mt-2 text-sm text-slate-500">
            Try adjusting your filters or create a new event.
          </p>
          <div className="mt-3">
            <Link
              className="inline-block rounded-md bg-slate-900 px-3 py-1.5 text-sm font-semibold text-white hover:bg-slate-800 hover:text-white focus:outline-none focus:ring-2 focus:ring-slate-500 focus:ring-offset-2"
              to="/create-event"
            >
              Create event
            </Link>
          </div>
        </Panel>
      ) : null}

      {loadedEvents.length > 0 && visibleEvents.length === 0 ? (
        <Panel className="text-center">
          <p className="m-0 text-sm font-semibold text-slate-700">
            No events match the current controls.
          </p>
          <p className="mt-2 text-sm text-slate-500">
            Try changing your search, filters, or sort order.
          </p>
        </Panel>
      ) : null}

      <ItemGrid>
        {visibleEvents.map((event) => (
          <li key={event.event_id}>
            <EventCard event={event} />
          </li>
        ))}
      </ItemGrid>

      {state.nextCursor ? (
        <PageActions>
          <button
            type="button"
            disabled={isLoadingMore}
            onClick={() => void loadMore()}
          >
            {isLoadingMore ? "Loading..." : "Load more"}
          </button>
        </PageActions>
      ) : null}
    </PageLayout>
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
    <section
      aria-labelledby="event-list-filters"
      className="grid max-w-4xl gap-3"
    >
      <h2 id="event-list-filters" className="sr-only">
        Find events
      </h2>

      <div className="grid gap-3 md:grid-cols-2">
        <div className="grid gap-1.5 md:col-span-2">
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
            className="h-9 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-slate-500 focus:ring-1 focus:ring-slate-400"
            placeholder="Title, description, or location"
          />
        </div>

        <div className="grid gap-1.5">
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
            className="h-9 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-900 focus:border-slate-500 focus:ring-1 focus:ring-slate-400"
          >
            <option value="all">All</option>
            <option value="ongoing">Ongoing</option>
            <option value="cancelled">Cancelled</option>
            <option value="outdated">Outdated</option>
          </select>
        </div>

        <div className="grid gap-1.5">
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
            className="h-9 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-900 focus:border-slate-500 focus:ring-1 focus:ring-slate-400"
          >
            <option value="all">All</option>
            <option value="public">Public</option>
            <option value="protected">Protected</option>
            <option value="admin">Admin-only</option>
          </select>
        </div>

        <div className="grid gap-1.5">
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
            className="h-9 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-900 focus:border-slate-500 focus:ring-1 focus:ring-slate-400"
          >
            <option value="all">All</option>
            <option value="unlimited">Unlimited capacity</option>
            <option value="limited">Has capacity limit</option>
            <option value="full">Full</option>
            <option value="available">Spots available</option>
          </select>
        </div>

        <div className="grid gap-1.5">
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
            className="h-9 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-900 focus:border-slate-500 focus:ring-1 focus:ring-slate-400"
          >
            <option value="date-asc">Event date: soonest first</option>
            <option value="date-desc">Event date: latest first</option>
            <option value="title-asc">Title: A-Z</option>
            <option value="title-desc">Title: Z-A</option>
            <option value="status-active-first">Status: active first</option>
            <option value="status-cancelled-first">
              Status: cancelled first
            </option>
            <option value="created-desc">Created: newest first</option>
            <option value="created-asc">Created: oldest first</option>
          </select>
        </div>
      </div>
    </section>
  );
}
