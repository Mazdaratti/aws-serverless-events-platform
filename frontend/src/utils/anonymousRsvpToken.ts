const ANONYMOUS_RSVP_TOKEN_KEY =
  "aws-serverless-events-platform:anonymous-rsvp-token";

function getStorage(): Storage | undefined {
  return typeof window !== "undefined" ? window.localStorage : undefined;
}

// This token is not a Cognito auth token and does not prove identity. It is a
// stable browser-local subject key so the backend can recognize the same
// anonymous RSVP on later visits from this browser.
//
// localStorage is acceptable here because anonymous_token is not a bearer
// credential. Cognito auth tokens must stay in sessionStorage instead.
export function getAnonymousRsvpToken(): string {
  const storage = getStorage();

  if (!storage) {
    return crypto.randomUUID();
  }

  const existingToken = storage.getItem(ANONYMOUS_RSVP_TOKEN_KEY);

  if (existingToken) {
    return existingToken;
  }

  const token = crypto.randomUUID();

  storage.setItem(ANONYMOUS_RSVP_TOKEN_KEY, token);

  return token;
}

// This is mainly useful for future account/logout UX or manual troubleshooting.
// Clearing it means the next anonymous RSVP from this browser becomes a new
// anonymous subject.
export function clearAnonymousRsvpToken(): void {
  getStorage()?.removeItem(ANONYMOUS_RSVP_TOKEN_KEY);
}
