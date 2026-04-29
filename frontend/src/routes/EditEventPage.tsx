import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { getApiErrorMessage } from "../api/errors";
import { getEvent, updateEvent } from "../api/events";
import type {
  CreateEventRequest,
  PublicEvent,
  UpdateEventRequest
} from "../api/types";
import { useAuth } from "../auth/AuthProvider";
import { ErrorMessage } from "../components/ErrorMessage";
import {
  EventForm,
  eventToFormValues
} from "../components/EventForm";
import { LoadingState } from "../components/LoadingState";
import { StatusMessage } from "../components/StatusMessage";

type LoadState =
  | { status: "loading"; event: null }
  | { status: "ready"; event: PublicEvent }
  | { status: "error"; event: null; message: string };

type SubmitState =
  | { status: "idle"; message: null }
  | { status: "submitting"; message: null }
  | { status: "notice"; message: string }
  | { status: "error"; message: string };

const initialLoadState: LoadState = {
  status: "loading",
  event: null
};

const initialSubmitState: SubmitState = {
  status: "idle",
  message: null
};

export function EditEventPage() {
  const navigate = useNavigate();
  const { eventId } = useParams<{ eventId: string }>();
  const { status } = useAuth();
  const [loadState, setLoadState] = useState<LoadState>(initialLoadState);
  const [submitState, setSubmitState] = useState<SubmitState>(initialSubmitState);

  const isSubmitting = submitState.status === "submitting";

  useEffect(() => {
    if (status !== "authenticated") {
      return;
    }

    const controller = new AbortController();

    setLoadState(initialLoadState);
    setSubmitState(initialSubmitState);

    async function loadEvent() {
      if (!eventId) {
        setLoadState({
          status: "error",
          event: null,
          message: "Event ID is missing from the route."
        });
        return;
      }

      try {
        // The detail read still uses the public get-event contract. The later
        // PATCH call is where API Gateway and the backend enforce edit access.
        const response = await getEvent(eventId, controller.signal);

        setLoadState({
          status: "ready",
          event: response.item
        });
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }

        setLoadState({
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
  }, [eventId, status]);

  const handleSubmit = async (request: CreateEventRequest) => {
    if (isSubmitting || loadState.status !== "ready" || !eventId) {
      return;
    }

    setSubmitState(initialSubmitState);

    const changes = buildUpdateRequest(loadState.event, request);

    if (Object.keys(changes).length === 0) {
      setSubmitState({
        status: "notice",
        message: "No changes to save."
      });
      return;
    }

    setSubmitState({
      status: "submitting",
      message: null
    });

    try {
      // PATCH should describe what changed, not resend every form field. That
      // keeps the request smaller and avoids accidental overwrites later.
      const response = await updateEvent(eventId, changes);

      // BrowserRouter handles the /app basename. Internal navigation stays
      // relative to the React route tree.
      navigate(`/events/${response.item.event_id}`);
    } catch (error) {
      setSubmitState({
        status: "error",
        message: getApiErrorMessage(error)
      });
    }
  };

  if (status === "loading") {
    return <LoadingState message="Checking session..." />;
  }

  if (status !== "authenticated") {
    return (
      <>
        <h1>Edit event</h1>
        {/* This is only a UX guard. The backend remains the source of truth for
            whether the current caller can edit the specific event. */}
        <StatusMessage message="You need to sign in before editing events." />
        <p>
          <Link to="/login">Login</Link> or{" "}
          <Link to="/register">register</Link> to continue.
        </p>
      </>
    );
  }

  if (loadState.status === "loading") {
    return <LoadingState message="Loading event..." />;
  }

  if (loadState.status === "error") {
    return (
      <>
        <h1>Edit event</h1>
        <ErrorMessage message={loadState.message} />
        <Link to="/events">Back to events</Link>
      </>
    );
  }

  return (
    <>
      <Link to={`/events/${loadState.event.event_id}`}>Back to event</Link>
      <h1>Edit event</h1>

      <EventForm
        initialValues={eventToFormValues(loadState.event)}
        submitButtonLabel="Save changes"
        submittingButtonLabel="Saving..."
        isSubmitting={isSubmitting}
        onSubmit={handleSubmit}
      />

      {submitState.status === "notice" ? (
        <StatusMessage message={submitState.message} />
      ) : null}

      {submitState.status === "error" ? (
        <ErrorMessage message={submitState.message} />
      ) : null}
    </>
  );
}

function buildUpdateRequest(
  original: PublicEvent,
  request: CreateEventRequest
): UpdateEventRequest {
  const changes: UpdateEventRequest = {};

  if (request.title !== original.title) {
    changes.title = request.title;
  }

  if (!areSameInstant(request.date, original.date)) {
    changes.date = request.date;
  }

  if (request.description !== original.description) {
    changes.description = request.description;
  }

  if (request.location !== original.location) {
    changes.location = request.location;
  }

  if (request.capacity !== original.capacity) {
    changes.capacity = request.capacity;
  }

  if (request.is_public !== original.is_public) {
    changes.is_public = request.is_public;
  }

  if (request.requires_admin !== original.requires_admin) {
    changes.requires_admin = request.requires_admin;
  }

  return changes;
}

function areSameInstant(firstValue: string, secondValue: string): boolean {
  const firstTime = Date.parse(firstValue);
  const secondTime = Date.parse(secondValue);

  if (Number.isNaN(firstTime) || Number.isNaN(secondTime)) {
    return firstValue === secondValue;
  }

  // Backend timestamps and browser timestamps can be equivalent while using
  // different string forms, such as Z versus .000Z. Compare the instant.
  return firstTime === secondTime;
}
