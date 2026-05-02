import { type FormEvent, useState } from "react";

import type { CreateEventRequest, PublicEvent } from "../api/types";
import { ErrorMessage } from "./ErrorMessage";

type EventVisibility = "public" | "protected" | "admin";

export interface EventFormValues {
  title: string;
  date: string;
  description: string;
  location: string;
  capacity: string;
  visibility: EventVisibility;
}

interface EventFormProps {
  initialValues: EventFormValues;
  submitButtonLabel: string;
  submittingButtonLabel: string;
  isSubmitting: boolean;
  onSubmit: (request: CreateEventRequest) => Promise<void>;
}

export const emptyEventFormValues: EventFormValues = {
  title: "",
  date: "",
  description: "",
  location: "",
  capacity: "",
  visibility: "public"
};

const fieldClassName = "grid gap-1.5";

const labelClassName = "text-sm font-semibold text-slate-700";

const controlClassName =
  "min-h-10 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-slate-500 focus:ring-1 focus:ring-slate-400";

const textareaClassName =
  "min-h-32 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-slate-500 focus:ring-1 focus:ring-slate-400";

const submitButtonClassName =
  "inline-flex w-fit rounded-md bg-slate-900 px-3 py-1.5 text-sm font-semibold text-white hover:bg-slate-800 hover:text-white focus:outline-none focus:ring-2 focus:ring-slate-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60";

export function eventToFormValues(event: PublicEvent): EventFormValues {
  return {
    title: event.title,
    date: toDateTimeLocalValue(event.date),
    description: event.description,
    location: event.location,
    capacity: event.capacity === null ? "" : String(event.capacity),
    visibility: getVisibilityValue(event)
  };
}

// EventForm always returns one complete, normalized event payload. Create pages
// can send it directly; edit pages can compare it with the original event and
// send only changed fields through PATCH.
export function EventForm({
  initialValues,
  submitButtonLabel,
  submittingButtonLabel,
  isSubmitting,
  onSubmit
}: EventFormProps) {
  const [values, setValues] = useState<EventFormValues>(initialValues);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (isSubmitting) {
      return;
    }

    const request = buildRequest(values);
    if (typeof request === "string") {
      setValidationMessage(request);
      return;
    }

    setValidationMessage(null);
    await onSubmit(request);
  };

  return (
    <form className="grid max-w-2xl gap-4" onSubmit={handleSubmit}>
      <div className={fieldClassName}>
        <label className={labelClassName} htmlFor="event-title">
          Title
        </label>
        <input
          id="event-title"
          name="title"
          value={values.title}
          onChange={(event) =>
            setValues({
              ...values,
              title: event.target.value
            })
          }
          required
          className={controlClassName}
        />
      </div>

      <div className={fieldClassName}>
        <label className={labelClassName} htmlFor="event-date">
          Date and time
        </label>
        <input
          id="event-date"
          name="date"
          type="datetime-local"
          value={values.date}
          onChange={(event) =>
            setValues({
              ...values,
              date: event.target.value
            })
          }
          required
          className={controlClassName}
        />
      </div>

      <div className={fieldClassName}>
        <label className={labelClassName} htmlFor="event-location">
          Location
        </label>
        <input
          id="event-location"
          name="location"
          value={values.location}
          onChange={(event) =>
            setValues({
              ...values,
              location: event.target.value
            })
          }
          className={controlClassName}
        />
      </div>

      <div className={fieldClassName}>
        <label className={labelClassName} htmlFor="event-description">
          Description
        </label>
        <textarea
          id="event-description"
          name="description"
          value={values.description}
          onChange={(event) =>
            setValues({
              ...values,
              description: event.target.value
            })
          }
          className={textareaClassName}
        />
      </div>

      <div className={fieldClassName}>
        <label className={labelClassName} htmlFor="event-capacity">
          Capacity
        </label>
        <input
          id="event-capacity"
          name="capacity"
          type="number"
          min="1"
          inputMode="numeric"
          value={values.capacity}
          onChange={(event) =>
            setValues({
              ...values,
              capacity: event.target.value
            })
          }
          placeholder="Unlimited"
          className={controlClassName}
        />
      </div>

      <div className={fieldClassName}>
        <label className={labelClassName} htmlFor="event-visibility">
          Visibility
        </label>
        <select
          id="event-visibility"
          name="visibility"
          value={values.visibility}
          onChange={(event) =>
            setValues({
              ...values,
              visibility: event.target.value as EventVisibility
            })
          }
          className={controlClassName}
        >
          <option value="public">Public</option>
          <option value="protected">Protected</option>
          <option value="admin">Admin-only</option>
        </select>
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className={submitButtonClassName}
      >
        {isSubmitting ? submittingButtonLabel : submitButtonLabel}
      </button>

      {validationMessage ? <ErrorMessage message={validationMessage} /> : null}
    </form>
  );
}

function buildRequest(values: EventFormValues): CreateEventRequest | string {
  const title = values.title.trim();
  if (!title) {
    return "Title is required.";
  }

  const date = normalizeDateValue(values.date);
  if (!date) {
    return "Date and time are required.";
  }

  const capacity = normalizeCapacityValue(values.capacity);
  if (typeof capacity === "string") {
    return capacity;
  }

  return {
    title,
    date,
    description: values.description.trim(),
    location: values.location.trim(),
    capacity,
    // The backend contract uses two booleans instead of one visibility string,
    // so the UI-friendly selection is mapped back into the API shape here.
    is_public: values.visibility === "public",
    requires_admin: values.visibility === "admin"
  };
}

function normalizeDateValue(value: string): string | null {
  if (!value) {
    return null;
  }

  const parsedDate = new Date(value);
  if (Number.isNaN(parsedDate.getTime())) {
    return null;
  }

  // datetime-local inputs do not include a timezone. Converting through Date
  // gives the backend the ISO UTC timestamp shape it already expects.
  return parsedDate.toISOString();
}

function normalizeCapacityValue(value: string): number | null | string {
  const trimmedValue = value.trim();
  if (!trimmedValue) {
    // Blank capacity means unlimited in the current API contract.
    return null;
  }

  const capacity = Number(trimmedValue);
  if (!Number.isInteger(capacity) || capacity < 1) {
    return "Capacity must be a whole number greater than or equal to 1, or blank for unlimited.";
  }

  return capacity;
}

function getVisibilityValue(event: PublicEvent): EventVisibility {
  if (event.requires_admin) {
    return "admin";
  }

  if (!event.is_public) {
    return "protected";
  }

  return "public";
}

function toDateTimeLocalValue(value: string): string {
  const parsedDate = new Date(value);
  if (Number.isNaN(parsedDate.getTime())) {
    return "";
  }

  // HTML datetime-local expects a local wall-clock value, not a UTC string.
  // Offset the stored UTC timestamp before trimming it to yyyy-MM-ddTHH:mm.
  const timezoneOffsetMs = parsedDate.getTimezoneOffset() * 60 * 1000;
  return new Date(parsedDate.getTime() - timezoneOffsetMs)
    .toISOString()
    .slice(0, 16);
}
