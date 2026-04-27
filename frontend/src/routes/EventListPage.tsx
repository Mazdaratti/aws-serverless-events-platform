import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getApiErrorMessage } from "../api/errors";
import { listEvents } from "../api/events";
import type { NextCursor, PublicEvent } from "../api/types";
import { ErrorMessage } from "../components/ErrorMessage";
import { LoadingState } from "../components/LoadingState";
import { formatEventDate } from "../utils/dates";

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

  return (
    <>
      <h1>Events</h1>

      {state.status === "loading" ? (
        <LoadingState message="Loading events..." />
      ) : null}

      {state.status === "error" ? (
        <ErrorMessage message={state.message} />
      ) : null}

      {state.items.length === 0 && state.status !== "loading" ? (
        <p>No events found.</p>
      ) : null}

      <ul>
        {state.items.map((event) => (
          <li key={event.event_id}>
            <Link to={`/events/${event.event_id}`}>{event.title}</Link>
            <div>{formatEventDate(event.date)}</div>
            <div>{event.location}</div>
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
