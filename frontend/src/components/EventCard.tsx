import { Link } from "react-router-dom";

import type { PublicEvent } from "../api/types";
import { formatEventDate } from "../utils/dates";

interface EventCardProps {
  event: PublicEvent;
}

export function EventCard({ event }: EventCardProps) {
  return (
    <article>
      {/* EventCard receives only the public backend DTO. It should not know
          anything about DynamoDB item shape or private backend fields. */}
      <h2>
        <Link to={`/events/${event.event_id}`}>
          {event.title || "Untitled event"}
        </Link>
      </h2>

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
