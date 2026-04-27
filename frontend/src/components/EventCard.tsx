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
    <article>
      {/* EventCard receives only the public backend DTO. It should not know
          anything about DynamoDB item shape or private backend fields. */}
      <h2>
        <Link to={`/events/${event.event_id}`}>
          {event.title || "Untitled event"}
        </Link>
      </h2>

      {/* Visibility labels explain the public DTO flags in user-facing terms.
          Backend authorization is still the source of truth for what actions
          are actually allowed. */}
      <p aria-label="Event visibility">
        <strong>{visibilityLabel}</strong>
      </p>

      <dl>
        <dt>Date</dt>
        <dd>{formatEventDate(event.date)}</dd>

        <dt>Location</dt>
        <dd>{event.location || "Location not specified"}</dd>

        <dt>RSVPs</dt>
        <dd>
          {event.attending_count} attending / {event.rsvp_count} total
        </dd>
      </dl>
    </article>
  );
}
