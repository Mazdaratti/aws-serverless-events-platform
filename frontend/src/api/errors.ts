export type ApiErrorStatus = number;

// ApiError keeps the HTTP status and parsed response body together. The UI can
// then tell the difference between validation errors, auth failures, forbidden
// actions, missing resources, and unexpected server failures.
export class ApiError extends Error {
  readonly status: ApiErrorStatus;
  readonly body: unknown;

  constructor({
    status,
    message,
    body
  }: {
    status: ApiErrorStatus;
    message: string;
    body: unknown;
  }) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;

    // Preserve instanceof ApiError checks even if the code is transpiled.
    Object.setPrototypeOf(this, ApiError.prototype);
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

// Components should use this helper when they need a safe string for display.
// It preserves backend messages for ApiError and avoids leaking unknown values.
export function getApiErrorMessage(error: unknown): string {
  if (isApiError(error)) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Unexpected error.";
}

// These are fallbacks only. When the backend returns a JSON { message }, the
// API client should prefer that exact message so business errors stay precise.
export function defaultMessageForStatus(status: number): string {
  if (status === 400) return "The request was not valid.";
  if (status === 401) return "You need to sign in before continuing.";
  if (status === 403) return "You are not allowed to perform this action.";
  if (status === 404) return "The requested resource was not found.";

  return "Something went wrong. Please try again.";
}
