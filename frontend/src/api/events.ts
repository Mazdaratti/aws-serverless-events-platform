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

export function listEvents(
  params: ListEventsParams = {},
  signal?: AbortSignal
): Promise<ListEventsResponse> {
  const searchParams = new URLSearchParams();

  if (params.nextCursor) {
    searchParams.set("next_cursor", params.nextCursor);
  }

  const query = searchParams.toString();
  const path = query ? `/events?${query}` : "/events";

  return apiRequest<ListEventsResponse>(path, {
    authMode: "none",
    signal
  });
}

export function getEvent(
  eventId: string,
  signal?: AbortSignal
): Promise<GetEventResponse> {
  return apiRequest<GetEventResponse>(`/events/${encodeURIComponent(eventId)}`, {
    authMode: "none",
    signal
  });
}

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
