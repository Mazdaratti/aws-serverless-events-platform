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
import {
  PageActions,
  PageHeader,
  PageLayout,
  Panel
} from "../components/LayoutPrimitives";
import { LoadingState } from "../components/LoadingState";
import { StatusMessage } from "../components/StatusMessage";
import {
  pageTitleClassName,
  secondaryButtonClassName,
  textLinkClassName
} from "../components/uiStyles";
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
  const returnPath = eventId ? `/events/${eventId}/rsvps` : "/events";
  const authLinkState = { from: returnPath };

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
      <PageLayout>
        <PageHeader>
          <div>
            <h1 className={pageTitleClassName}>Event RSVPs</h1>
            <p className="m-0 max-w-2xl text-sm leading-6 text-slate-600">
              Sign in to review attendee responses for your events.
            </p>
          </div>
        </PageHeader>
        {/* This is a UI prompt only. The protected API route is still the real
            source of truth for RSVP-list access. */}
        <StatusMessage message="You need to sign in before viewing RSVPs." />
        <p className="m-0 text-sm text-slate-600">
          <Link
            className={textLinkClassName}
            state={authLinkState}
            to="/login"
          >
            Login
          </Link>{" "}
          or{" "}
          <Link
            className={textLinkClassName}
            state={authLinkState}
            to="/register"
          >
            register
          </Link>{" "}
          to continue.
        </p>
      </PageLayout>
    );
  }

  if (loadState.status === "loading") {
    return <LoadingState message="Loading RSVPs..." />;
  }

  if (loadState.status === "error" && !loadState.response) {
    return (
      <PageLayout>
        <PageHeader>
          <div>
            <h1 className={pageTitleClassName}>Event RSVPs</h1>
            <p className="m-0 max-w-2xl text-sm leading-6 text-slate-600">
              We could not load RSVP activity for this event.
            </p>
          </div>
        </PageHeader>
        <ErrorMessage message={loadState.message} />
        <PageActions>
          <Link
            className={`text-sm ${textLinkClassName}`}
            to={eventId ? `/events/${eventId}` : "/events"}
          >
            Back to event
          </Link>
        </PageActions>
      </PageLayout>
    );
  }

  const response = loadState.response;

  if (!response) {
    return (
      <PageLayout>
        <ErrorMessage message="RSVP response is missing." />
      </PageLayout>
    );
  }

  return (
    <PageLayout>
      <PageHeader>
        <div>
          <p className="m-0">
            <Link
              className={`text-sm ${textLinkClassName}`}
              to={`/events/${response.event.event_id}`}
            >
              Back to event
            </Link>
          </p>
          <h1 className={pageTitleClassName}>Event RSVPs</h1>
          <p className="m-0 max-w-2xl text-sm leading-6 text-slate-600">
            Review RSVP activity for {response.event.title || "this event"}.
          </p>
        </div>
      </PageHeader>

      <div className="grid max-w-4xl gap-6">
        <Panel aria-labelledby="rsvp-event-summary">
          <h2
            id="rsvp-event-summary"
            className="m-0 text-lg font-semibold leading-tight text-slate-900"
          >
            {response.event.title || "Untitled event"}
          </h2>
          <dl className="m-0 mt-4 grid gap-y-2.5 text-sm sm:grid-cols-[minmax(7rem,max-content)_minmax(0,1fr)] sm:gap-x-4">
            <dt className="font-semibold text-slate-500">Date</dt>
            <dd className="m-0 min-w-0 break-words text-slate-700">
              {formatEventDate(response.event.date)}
            </dd>
            <dt className="font-semibold text-slate-500">Status</dt>
            <dd className="m-0 min-w-0 break-words text-slate-700">
              {response.event.status}
            </dd>
            <dt className="font-semibold text-slate-500">Capacity</dt>
            <dd className="m-0 min-w-0 break-words text-slate-700">
              {response.event.capacity === null
                ? "Unlimited"
                : response.event.capacity}
            </dd>
            <dt className="font-semibold text-slate-500">RSVPs</dt>
            <dd className="m-0 min-w-0 break-words text-slate-700">
              {response.stats.attending} attending / {response.stats.total} total
            </dd>
          </dl>
        </Panel>

        {loadState.status === "error" ? (
          <ErrorMessage message={loadState.message} />
        ) : null}

        {response.items.length === 0 ? (
          <Panel className="text-center">
            <p className="m-0 text-sm font-semibold text-slate-700">
              No RSVPs yet.
            </p>
            <p className="mt-2 text-sm text-slate-500">
              Attendee responses will appear here after guests RSVP.
            </p>
          </Panel>
        ) : (
          <section aria-labelledby="rsvp-responses-heading">
            <h2 id="rsvp-responses-heading" className="sr-only">
              RSVP responses
            </h2>
            <ul className="grid gap-4">
              {response.items.map((item) => (
                <li key={`${getSubjectKey(item.subject)}-${item.updated_at}`}>
                  <RsvpListItemView item={item} />
                </li>
              ))}
            </ul>
          </section>
        )}

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
      </div>
    </PageLayout>
  );
}

function RsvpListItemView({ item }: { item: RsvpListItem }) {
  return (
    <article className="grid h-full gap-4 rounded-lg border border-slate-200 bg-white p-4 shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition-colors transition-shadow hover:border-slate-300 hover:shadow-md">
      <h3 className="m-0 text-base font-semibold leading-tight text-slate-900">
        {getSubjectLabel(item.subject)}
      </h3>
      <dl className="m-0 grid gap-y-2 text-sm sm:grid-cols-[minmax(5rem,max-content)_minmax(0,1fr)] sm:gap-x-4">
        <dt className="font-semibold text-slate-500">Status</dt>
        <dd className="m-0 min-w-0 break-words text-slate-700">
          <span className="inline-flex w-fit rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-700">
            {item.attending ? "Attending" : "Not attending"}
          </span>
        </dd>
        <dt className="font-semibold text-slate-500">Created</dt>
        <dd className="m-0 min-w-0 break-words text-slate-700">
          {formatEventDate(item.created_at)}
        </dd>
        <dt className="font-semibold text-slate-500">Updated</dt>
        <dd className="m-0 min-w-0 break-words text-slate-700">
          {formatEventDate(item.updated_at)}
        </dd>
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
