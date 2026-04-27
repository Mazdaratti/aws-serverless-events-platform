import { fetchAuthSession } from "aws-amplify/auth";

export type AuthToken = string;

// The deployed API Gateway JWT authorizer and the mixed-mode RSVP authorizer
// currently validate tokens against the Cognito app client ID audience.
// Cognito ID tokens carry that audience, so this helper intentionally returns
// the ID token rather than switching callers ad hoc between token types.
export async function getValidatedBearerToken(): Promise<AuthToken | null> {
  try {
    const session = await fetchAuthSession();
    const idToken = session.tokens?.idToken;

    if (!idToken) {
      return null;
    }

    return idToken.toString();
  } catch {
    return null;
  }
}

export async function requireValidatedBearerToken(): Promise<AuthToken> {
  const token = await getValidatedBearerToken();

  if (!token) {
    throw new Error("Authentication required.");
  }

  return token;
}
