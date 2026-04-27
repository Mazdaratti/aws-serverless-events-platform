import { apiRequest } from "./client";
import type {
  GetEventResponse,
  ListEventsResponse,
  RsvpRequest,
  RsvpResponse
} from "./types";

export interface ListEventsParams {
  nextCursor?: string;
}

// PR 16B only uses the public list/detail routes and the mixed-mode RSVP route.
// The create/edit/cancel/my-events/RSVP-list API wrappers will be added with
// the authenticated management UI in PR 16C.
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
