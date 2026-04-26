import { getValidatedBearerToken, requireValidatedBearerToken } from "../auth/session";
import { ApiError, defaultMessageForStatus } from "./errors";

export type AuthMode = "none" | "optional" | "required";

export interface ApiRequestOptions {
  authMode: AuthMode;
  method?: "GET" | "POST" | "PATCH";
  body?: unknown;
  signal?: AbortSignal;
}

interface ErrorBody {
  message?: unknown;
}

// All browser API traffic goes through CloudFront using same-origin relative
// paths. Callers pass only the locked /events route family here; no raw API
// Gateway URL, /api prefix, or frontend /app path belongs in this client.
export async function apiRequest<TResponse>(
  path: string,
  options: ApiRequestOptions
): Promise<TResponse> {
  validateRelativeApiPath(path);

  const headers = new Headers();
  const token = await resolveToken(options.authMode);

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const hasBody = options.body !== undefined;

  if (hasBody) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(path, {
    method: options.method ?? "GET",
    headers,
    body: hasBody ? JSON.stringify(options.body) : undefined,
    signal: options.signal
  });

  const responseBody = await parseResponseBody(response);

  if (!response.ok) {
    throw new ApiError({
      status: response.status,
      message: resolveErrorMessage(response.status, responseBody),
      body: responseBody
    });
  }

  return responseBody as TResponse;
}

async function resolveToken(authMode: AuthMode): Promise<string | null> {
  if (authMode === "none") {
    return null;
  }

  if (authMode === "required") {
    return requireValidatedBearerToken();
  }

  // Optional auth is used by mixed-mode RSVP. If there is no valid session, the
  // request stays anonymous. If the backend rejects a presented token, callers
  // must surface that failure instead of retrying anonymously.
  return getValidatedBearerToken();
}

// Successful backend responses are JSON today, but this keeps the client
// tolerant of empty bodies and still preserves unexpected text for debugging.
async function parseResponseBody(response: Response): Promise<unknown> {
  if (response.status === 204) {
    return null;
  }

  const text = await response.text();

  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

function resolveErrorMessage(status: number, body: unknown): string {
  if (isErrorBody(body) && typeof body.message === "string" && body.message) {
    return body.message;
  }

  return defaultMessageForStatus(status);
}

function isErrorBody(body: unknown): body is ErrorBody {
  return typeof body === "object" && body !== null && "message" in body;
}

// Validate the path portion separately from the query string. /events with
// ?next_cursor=... is valid, but /eventsXYZ and /events-not-real are not part
// of the locked backend route family.
function validateRelativeApiPath(path: string): void {
  const url = new URL(path, window.location.origin);
  const pathname = url.pathname;

  if (url.origin !== window.location.origin) {
    throw new Error("API requests must use same-origin relative paths.");
  }

  if (pathname.startsWith("/app")) {
    throw new Error("API requests must not use the frontend /app namespace.");
  }

  if (pathname !== "/events" && !pathname.startsWith("/events/")) {
    throw new Error("API requests must use the locked /events route family.");
  }
}
