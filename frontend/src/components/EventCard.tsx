import { Link } from "react-router-dom";

import type { PublicEvent } from "../api/types";
import { formatEventDate } from "../utils/dates";

interface EventCardProps {
  event: PublicEvent;
}

function getVisibilityLabel(event: PublicEvent): string {
  if (event.requires_admin) {
    return "Admin-only";
  }

  if (!event.is_public) {
    return "Protected";
  }

  return "Public";
}

export function EventCard({ event }: EventCardProps) {
  const visibilityLabel = getVisibilityLabel(event);

  return (
    <article className="grid h-full gap-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm hover:border-blue-200 hover:shadow-md">
      {/* EventCard receives only the public backend DTO. It should not know
          anything about DynamoDB item shape or private backend fields. */}
      <h2 className="m-0 text-xl font-semibold leading-tight text-slate-950">
        <Link
          className="text-slate-950 hover:text-blue-700"
          to={`/events/${event.event_id}`}
        >
          {event.title || "Untitled event"}
        </Link>
      </h2>

      {/* Visibility labels explain the public DTO flags in user-facing terms.
          Backend authorization is still the source of truth for what actions
          are actually allowed. */}
      <p aria-label="Event visibility" className="m-0">
        <strong className="inline-flex w-fit rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-800">
          {visibilityLabel}
        </strong>
      </p>

      <dl className="m-0 grid grid-cols-[minmax(6rem,max-content)_minmax(0,1fr)] gap-x-4 gap-y-2 text-sm">
        <dt className="font-semibold text-slate-500">Date</dt>
        <dd className="m-0 min-w-0 break-words text-slate-800">
          {formatEventDate(event.date)}
        </dd>

        <dt className="font-semibold text-slate-500">Location</dt>
        <dd className="m-0 min-w-0 break-words text-slate-800">
          {event.location || "Location not specified"}
        </dd>

        <dt className="font-semibold text-slate-500">Created</dt>
        {/* Public event DTOs expose created_at, not updated_at. Show the real
            available timestamp instead of inventing a last-updated field. */}
        <dd className="m-0 min-w-0 break-words text-slate-800">
          {formatEventDate(event.created_at)}
        </dd>

        <dt className="font-semibold text-slate-500">RSVPs</dt>
        <dd className="m-0 min-w-0 break-words text-slate-800">
          {event.attending_count} attending / {event.rsvp_count} total
        </dd>
      </dl>
    </article>
  );
}
