import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getApiErrorMessage } from "../api/errors";
import { cancelEvent, listMyEvents } from "../api/events";
import type { NextCursor, PublicEvent } from "../api/types";
import { useAuth } from "../auth/AuthProvider";
import { ErrorMessage } from "../components/ErrorMessage";
import { EventCard } from "../components/EventCard";
import {
  ItemGrid,
  PageActions,
  PageHeader,
  PageLayout,
  Panel
} from "../components/LayoutPrimitives";
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
      <PageLayout>
        <PageHeader>
          <div>
            <h1>My events</h1>
            <p className="m-0 max-w-2xl text-sm leading-6 text-slate-600">
              Sign in to manage events you created and review RSVP activity.
            </p>
          </div>
        </PageHeader>
        {/* This is only a helpful UI boundary. API Gateway still protects the
            real GET /events/mine request. */}
        <StatusMessage message="You need to sign in before viewing your events." />
        <p>
          <Link to="/login">Login</Link> or{" "}
          <Link to="/register">register</Link> to continue.
        </p>
      </PageLayout>
    );
  }

  return (
    <PageLayout>
      <PageHeader>
        <div>
          <h1>My events</h1>
          <p className="m-0 max-w-2xl text-sm leading-6 text-slate-600">
            Manage events you created and review their RSVP activity.
          </p>
        </div>

        <PageActions>
          <Link
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 hover:border-slate-400 hover:bg-slate-100 hover:text-slate-950 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-2"
            to="/create-event"
          >
            Create event
          </Link>

          {hasActiveControls ? (
            <button
              type="button"
              onClick={() => setControls(myEventsDefaultControls)}
            >
              Reset controls
            </button>
          ) : null}
        </PageActions>
      </PageHeader>

      <MyEventsControlsForm controls={controls} setControls={setControls} />

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
        <>
          <div className="border-t border-slate-200" />
          <div className="mt-5 grid gap-4">
            <p className="m-0 text-sm text-slate-500">
              Showing {visibleEvents.length} of {loadState.items.length} loaded
              events.
            </p>
          </div>
        </>
      ) : null}

      {loadState.items.length === 0 && loadState.status !== "loading" ? (
        <Panel className="text-center">
          <p className="m-0 text-sm font-semibold text-slate-700">
            No events yet.
          </p>
          <p className="mt-2 text-sm text-slate-500">
            Create an event to start managing RSVPs.
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

      {loadState.items.length > 0 && visibleEvents.length === 0 ? (
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
          <li className="grid gap-3" key={event.event_id}>
            <EventCard event={event} />
            <PageActions>
              <Link
                className="text-sm font-medium text-slate-700 hover:text-slate-950"
                to={`/events/${event.event_id}/edit`}
              >
                Edit
              </Link>
              {/* RSVP-list access is checked by the backend. This owner page
                  only provides a convenient management shortcut. */}
              <Link
                className="text-sm font-medium text-slate-700 hover:text-slate-950"
                to={`/events/${event.event_id}/rsvps`}
              >
                View RSVPs
              </Link>
            </PageActions>

            {event.status === "CANCELLED" ? (
              <StatusMessage message="This event is cancelled." />
            ) : cancelState.status === "confirming" &&
              cancelState.eventId === event.event_id ? (
              <div>
                Confirm cancellation?{" "}
                <PageActions>
                  <button
                    type="button"
                    onClick={() => void confirmCancel(event.event_id)}
                  >
                    Confirm cancel
                  </button>
                  <button type="button" onClick={keepEvent}>
                    Keep event
                  </button>
                </PageActions>
              </div>
            ) : (
              <PageActions>
                <button type="button" onClick={() => startCancel(event.event_id)}>
                  Cancel event
                </button>
              </PageActions>
            )}
          </li>
        ))}
      </ItemGrid>

      {loadState.nextCursor ? (
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

interface MyEventsControlsFormProps {
  controls: EventListControls;
  setControls: (controls: EventListControls) => void;
}

function MyEventsControlsForm({
  controls,
  setControls
}: MyEventsControlsFormProps) {
  return (
    <section
      aria-labelledby="my-events-filters"
      className="grid max-w-4xl gap-3"
    >
      <h2 id="my-events-filters" className="sr-only">
        Find my events
      </h2>

      <div className="grid gap-3 md:grid-cols-2">
        <div className="grid gap-1.5 md:col-span-2">
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
            className="min-h-10 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-slate-500 focus:ring-1 focus:ring-slate-400"
            placeholder="Title, description, or location"
          />
        </div>

        <div className="grid gap-1.5">
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
            className="min-h-10 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-900 focus:border-slate-500 focus:ring-1 focus:ring-slate-400"
          >
            <option value="all">All</option>
            <option value="ongoing">Ongoing</option>
            <option value="cancelled">Cancelled</option>
            <option value="outdated">Outdated</option>
          </select>
        </div>

        <div className="grid gap-1.5">
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
            className="min-h-10 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-900 focus:border-slate-500 focus:ring-1 focus:ring-slate-400"
          >
            <option value="all">All</option>
            <option value="public">Public</option>
            <option value="protected">Protected</option>
            <option value="admin">Admin-only</option>
          </select>
        </div>

        <div className="grid gap-1.5">
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
            className="min-h-10 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-900 focus:border-slate-500 focus:ring-1 focus:ring-slate-400"
          >
            <option value="all">All</option>
            <option value="unlimited">Unlimited capacity</option>
            <option value="limited">Has capacity limit</option>
            <option value="full">Full</option>
            <option value="available">Spots available</option>
          </select>
        </div>

        <div className="grid gap-1.5">
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
            className="min-h-10 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-900 focus:border-slate-500 focus:ring-1 focus:ring-slate-400"
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
      </div>
    </section>
  );
}
