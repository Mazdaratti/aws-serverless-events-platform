import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getApiErrorMessage } from "../api/errors";
import { cancelEvent, listMyEvents } from "../api/events";
import type { NextCursor, PublicEvent } from "../api/types";
import { useAuth } from "../auth/AuthProvider";
import { ErrorMessage } from "../components/ErrorMessage";
import {
  EventListControlsForm,
  type EventListControlOption
} from "../components/EventListControlsForm";
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
  destructiveButtonClassName,
  pageTitleClassName,
  primaryButtonClassName,
  secondaryButtonClassName,
  textLinkClassName
} from "../components/uiStyles";
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

const myEventsEventStateOptions: Array<
  EventListControlOption<EventListControls["eventState"]>
> = [
  { label: "All", value: "all" },
  { label: "Ongoing", value: "ongoing" },
  { label: "Cancelled", value: "cancelled" },
  { label: "Outdated", value: "outdated" }
];

const myEventsSortOptions: Array<
  EventListControlOption<EventListControls["sort"]>
> = [
  { label: "Event date: soonest first", value: "date-asc" },
  { label: "Event date: latest first", value: "date-desc" },
  { label: "Title: A-Z", value: "title-asc" },
  { label: "Title: Z-A", value: "title-desc" },
  { label: "Status: active first", value: "status-active-first" },
  {
    label: "Status: cancelled first",
    value: "status-cancelled-first"
  },
  { label: "Created: newest first", value: "created-desc" },
  { label: "Created: oldest first", value: "created-asc" }
];

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
          items: response.items ?? [],
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

  const loadedEvents = loadState.items ?? [];

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

      setLoadState((prev) => ({
        status: "ready",
        items: [...(prev.items ?? []), ...(response.items ?? [])],
        nextCursor: response.next_cursor
      }));
    } catch (error) {
      setLoadState((prev) => ({
        status: "error",
        items: prev.items ?? [],
        nextCursor: prev.nextCursor,
        message: getApiErrorMessage(error)
      }));
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
        items: (currentState.items ?? []).map((item) =>
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
  const visibleEvents = applyEventListControls(loadedEvents, controls);
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
            <h1 className={pageTitleClassName}>My events</h1>
            <p className="m-0 max-w-2xl text-sm leading-6 text-slate-600">
              Sign in to manage events you created and review RSVP activity.
            </p>
          </div>
        </PageHeader>
        {/* This is only a helpful UI boundary. API Gateway still protects the
            real GET /events/mine request. */}
        <StatusMessage message="You need to sign in before viewing your events." />
        <p className="m-0 text-sm text-slate-600">
          <Link className={textLinkClassName} to="/login">
            Login
          </Link>{" "}
          or{" "}
          <Link className={textLinkClassName} to="/register">
            register
          </Link>{" "}
          to continue.
        </p>
      </PageLayout>
    );
  }

  return (
    <PageLayout>
      <PageHeader>
        <div>
          <h1 className={pageTitleClassName}>My events</h1>
          <p className="m-0 max-w-2xl text-sm leading-6 text-slate-600">
            Manage events you created and review their RSVP activity.
          </p>
        </div>

        <PageActions>
          {hasActiveControls ? (
            <button
              type="button"
              onClick={() => setControls(myEventsDefaultControls)}
              className={secondaryButtonClassName}
            >
              Reset controls
            </button>
          ) : null}
        </PageActions>
      </PageHeader>

      <EventListControlsForm
        controls={controls}
        eventStateOptions={myEventsEventStateOptions}
        heading="Find my events"
        headingId="my-events-filters"
        idPrefix="my-events"
        onChange={setControls}
        sortOptions={myEventsSortOptions}
      />

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
              Showing {visibleEvents.length} of {loadedEvents.length} loaded
              events.
            </p>
          </div>
        </>
      ) : null}

      {loadedEvents.length === 0 && loadState.status !== "loading" ? (
        <Panel className="text-center">
          <p className="m-0 text-sm font-semibold text-slate-700">
            No events yet.
          </p>
          <p className="mt-2 text-sm text-slate-500">
            Create an event to start managing RSVPs.
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
            <EventCard event={event}>
              <div className="grid gap-3">
                <PageActions className="gap-4">
                  <Link
                    className={`text-sm ${textLinkClassName}`}
                    to={`/events/${event.event_id}/edit`}
                  >
                    Edit
                  </Link>
                  {/* RSVP-list access is checked by the backend. This owner page
                      only provides a convenient management shortcut. */}
                  <Link
                    className={`text-sm ${textLinkClassName}`}
                    to={`/events/${event.event_id}/rsvps`}
                  >
                    View RSVPs
                  </Link>
                </PageActions>

                {event.status === "CANCELLED" ? (
                  <p role="status" className="m-0 text-sm text-slate-500">
                    This event is cancelled.
                  </p>
                ) : cancelState.status === "confirming" &&
                  cancelState.eventId === event.event_id ? (
                  <div
                    aria-describedby={`cancel-confirmation-${event.event_id}`}
                    className="grid gap-2"
                  >
                    <p
                      id={`cancel-confirmation-${event.event_id}`}
                      role="status"
                      className="m-0 text-sm text-slate-600"
                    >
                      Confirm cancellation?
                    </p>
                    <PageActions>
                      <button
                        type="button"
                        onClick={() => void confirmCancel(event.event_id)}
                        className={destructiveButtonClassName}
                      >
                        Confirm cancel
                      </button>
                      <button
                        type="button"
                        onClick={keepEvent}
                        className={secondaryButtonClassName}
                      >
                        Keep event
                      </button>
                    </PageActions>
                  </div>
                ) : (
                  <PageActions>
                    <button
                      type="button"
                      onClick={() => startCancel(event.event_id)}
                      className={destructiveButtonClassName}
                    >
                      Cancel event
                    </button>
                  </PageActions>
                )}
              </div>
            </EventCard>
          </li>
        ))}
      </ItemGrid>

      {loadState.nextCursor ? (
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
