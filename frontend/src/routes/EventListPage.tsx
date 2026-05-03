import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getApiErrorMessage } from "../api/errors";
import { listEvents } from "../api/events";
import type { NextCursor, PublicEvent } from "../api/types";
import { EventCard } from "../components/EventCard";
import {
  EventListControlsForm,
  type EventListControlOption
} from "../components/EventListControlsForm";
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
  pageTitleClassName,
  primaryButtonClassName,
  secondaryButtonClassName
} from "../components/uiStyles";
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

const publicEventStateOptions: Array<
  EventListControlOption<EventListControls["eventState"]>
> = [
  { label: "All", value: "all" },
  { label: "Ongoing", value: "ongoing" },
  { label: "Outdated", value: "outdated" }
];

const publicSortOptions: Array<
  EventListControlOption<EventListControls["sort"]>
> = [
  { label: "Event date: soonest first", value: "date-asc" },
  { label: "Event date: latest first", value: "date-desc" },
  { label: "Title: A-Z", value: "title-asc" },
  { label: "Title: Z-A", value: "title-desc" },
  { label: "Created: newest first", value: "created-desc" }
];

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
          <h1 className={pageTitleClassName}>Events</h1>
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
              className={secondaryButtonClassName}
            >
              Reset controls
            </button>
          ) : null}
        </PageActions>
      </PageHeader>

      <EventListControlsForm
        controls={controls}
        eventStateOptions={publicEventStateOptions}
        heading="Find events"
        headingId="event-list-filters"
        idPrefix="event"
        onChange={setControls}
        sortOptions={publicSortOptions}
      />

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
              className={primaryButtonClassName}
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
            className={secondaryButtonClassName}
          >
            {isLoadingMore ? "Loading..." : "Load more"}
          </button>
        </PageActions>
      ) : null}
    </PageLayout>
  );
}
