import { apiRequest } from "./client";
import type {
  CreateEventRequest,
  EventRsvpsResponse,
  GetEventResponse,
  ListEventsResponse,
  RsvpRequest,
  RsvpResponse,
  UpdateEventRequest
} from "./types";

export interface ListEventsParams {
  nextCursor?: string;
}

export interface ListMyEventsParams {
  nextCursor?: string;
  limit?: number;
}

export interface GetEventRsvpsParams {
  nextCursor?: string;
  limit?: number;
}

export function listEvents(
  params: ListEventsParams = {},
  signal?: AbortSignal
): Promise<ListEventsResponse> {
  const searchParams = new URLSearchParams();

  if (params.nextCursor) {
    // next_cursor is opaque. The frontend must pass it back exactly as the API
    // returned it instead of trying to decode backend pagination state.
    searchParams.set("next_cursor", params.nextCursor);
  }

  const query = searchParams.toString();
  const path = query ? `/events?${query}` : "/events";

  return apiRequest<ListEventsResponse>(path, {
    authMode: "none",
    signal
  });
}

// Event detail reads are public in the current backend contract, even for
// protected/admin-only events. RSVP and mutation rules enforce access later.
export function getEvent(
  eventId: string,
  signal?: AbortSignal
): Promise<GetEventResponse> {
  return apiRequest<GetEventResponse>(`/events/${encodeURIComponent(eventId)}`, {
    authMode: "none",
    signal
  });
}

// RSVP is mixed-mode: anonymous users may RSVP to public events, while signed-in
// users should RSVP with their Cognito token. The API client attaches a token
// only when a valid session exists and must not retry anonymously after a
// backend auth rejection.
export function rsvpToEvent(
  eventId: string,
  request: RsvpRequest
): Promise<RsvpResponse> {
  return apiRequest<RsvpResponse>(`/events/${encodeURIComponent(eventId)}/rsvp`, {
    authMode: "optional",
    method: "POST",
    body: request
  });
}

export function createEvent(
  request: CreateEventRequest
): Promise<GetEventResponse> {
  return apiRequest<GetEventResponse>("/events", {
    authMode: "required",
    method: "POST",
    body: request
  });
}

export function updateEvent(
  eventId: string,
  request: UpdateEventRequest
): Promise<GetEventResponse> {
  return apiRequest<GetEventResponse>(`/events/${encodeURIComponent(eventId)}`, {
    authMode: "required",
    method: "PATCH",
    body: request
  });
}

export function cancelEvent(eventId: string): Promise<GetEventResponse> {
  return apiRequest<GetEventResponse>(
    `/events/${encodeURIComponent(eventId)}/cancel`,
    {
      authMode: "required",
      method: "POST"
    }
  );
}

export function listMyEvents(
  params: ListMyEventsParams = {},
  signal?: AbortSignal
): Promise<ListEventsResponse> {
  const path = buildListPath("/events/mine", params);

  return apiRequest<ListEventsResponse>(path, {
    authMode: "required",
    signal
  });
}

export function getEventRsvps(
  eventId: string,
  params: GetEventRsvpsParams = {},
  signal?: AbortSignal
): Promise<EventRsvpsResponse> {
  const path = buildListPath(
    `/events/${encodeURIComponent(eventId)}/rsvps`,
    params
  );

  return apiRequest<EventRsvpsResponse>(path, {
    authMode: "required",
    signal
  });
}

function buildListPath(
  basePath: string,
  params: { nextCursor?: string; limit?: number }
): string {
  const searchParams = new URLSearchParams();

  if (params.nextCursor) {
    searchParams.set("next_cursor", params.nextCursor);
  }

  if (params.limit !== undefined) {
    searchParams.set("limit", String(params.limit));
  }

  const query = searchParams.toString();
  return query ? `${basePath}?${query}` : basePath;
}
