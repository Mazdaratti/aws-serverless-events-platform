export type EventStatus = "ACTIVE" | "CANCELLED";

// API timestamps are ISO 8601 UTC strings. The frontend can format them for
// display, but it should keep the API value unchanged when sending it back.
export type IsoDateTime = string;

// Pagination cursors are intentionally opaque. The frontend passes them back
// exactly as received and must not inspect or reconstruct backend key data.
export type NextCursor = string | null;

// This is the public event DTO returned by event read routes. It deliberately
// excludes DynamoDB keys, GSI helper attributes, and internal RSVP fields.
export interface PublicEvent {
  event_id: string;
  status: EventStatus;
  title: string;
  date: IsoDateTime;
  description: string;
  location: string;
  capacity: number | null;
  is_public: boolean;
  requires_admin: boolean;
  created_by: string;
  created_at: IsoDateTime;
  rsvp_count: number;
  attending_count: number;
}

export interface ListEventsResponse {
  items: PublicEvent[];
  next_cursor: NextCursor;
}

export interface GetEventResponse {
  item: PublicEvent;
}

export interface RsvpRequest {
  attending: boolean;
  // Required for anonymous RSVP; must be omitted for authenticated users.
  anonymous_token?: string;
}

// Included now so PR 16C can reuse the same API contract types for event
// creation without inventing a second request shape in the UI layer.
export interface CreateEventRequest {
  title: string;
  date: IsoDateTime;
  description: string;
  location: string;
  capacity: number | null;
  is_public: boolean;
  requires_admin: boolean;
}

export type RsvpOperation = "created" | "updated";
export type RsvpSubjectType = "USER" | "ANON";

// RSVP subjects are public response objects. They identify whether the RSVP
// belongs to a Cognito user or an anonymous browser token without exposing raw
// storage keys.
export interface RsvpSubject {
  type: RsvpSubjectType;
  user_id: string | null;
  anonymous: boolean;
}

export interface RsvpItem {
  event_id: string;
  subject: RsvpSubject;
  attending: boolean;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
}

// RSVP write responses include not_attending_count here, but normal public
// event read DTOs intentionally do not expose that field.
export interface RsvpEventSummary {
  status: EventStatus;
  capacity: number | null;
  rsvp_count: number;
  attending_count: number;
  not_attending_count: number;
}

export interface RsvpResponse {
  item: RsvpItem;
  event_summary: RsvpEventSummary;
  operation: RsvpOperation;
}

export interface EventRsvpsSummary {
  event_id: string;
  status: EventStatus;
  title: string;
  date: IsoDateTime;
  capacity: number | null;
  created_by: string;
  rsvp_count: number;
  attending_count: number;
}

export interface EventRsvpsStats {
  total: number;
  attending: number;
  not_attending: number;
}

export interface EventRsvpsResponse {
  event: EventRsvpsSummary;
  items: Omit<RsvpItem, "event_id">[];
  stats: EventRsvpsStats;
  next_cursor: NextCursor;
}
