import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { getApiErrorMessage } from "../api/errors";
import { createEvent } from "../api/events";
import type { CreateEventRequest } from "../api/types";
import { useAuth } from "../auth/AuthProvider";
import { ErrorMessage } from "../components/ErrorMessage";
import {
  emptyEventFormValues,
  EventForm
} from "../components/EventForm";
import { LoadingState } from "../components/LoadingState";
import { StatusMessage } from "../components/StatusMessage";

type SubmitState =
  | { status: "idle"; message: null }
  | { status: "submitting"; message: null }
  | { status: "error"; message: string };

const initialSubmitState: SubmitState = {
  status: "idle",
  message: null
};

export function CreateEventPage() {
  const navigate = useNavigate();
  const { status } = useAuth();
  const [submitState, setSubmitState] = useState<SubmitState>(initialSubmitState);

  const isSubmitting = submitState.status === "submitting";

  const handleSubmit = async (request: CreateEventRequest) => {
    if (isSubmitting) {
      return;
    }

    setSubmitState({
      status: "submitting",
      message: null
    });

    try {
      // The backend owns event identity, creator ownership, and validation.
      // The frontend sends only the public event fields collected by the form.
      const response = await createEvent(request);

      // BrowserRouter already adds /app in the address bar. Internal route
      // navigation should stay basename-relative and use /events/{event_id}.
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
        <h1>Create event</h1>
        {/* This is a UX guard only. API Gateway and the backend still enforce
            authentication and creator ownership for the actual event write. */}
        <StatusMessage message="You need to sign in before creating events." />
        <p>
          <Link to="/login">Login</Link> or{" "}
          <Link to="/register">register</Link> to continue.
        </p>
      </>
    );
  }

  return (
    <>
      <Link to="/events">Back to events</Link>
      <h1>Create event</h1>

      <EventForm
        initialValues={emptyEventFormValues}
        submitButtonLabel="Create event"
        submittingButtonLabel="Creating..."
        isSubmitting={isSubmitting}
        onSubmit={handleSubmit}
      />

      {submitState.status === "error" ? (
        <ErrorMessage message={submitState.message} />
      ) : null}
    </>
  );
}
