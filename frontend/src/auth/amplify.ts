import { Amplify } from "aws-amplify";
import { cognitoUserPoolsTokenProvider } from "aws-amplify/auth/cognito";
import { sessionStorage } from "aws-amplify/utils";

interface FrontendConfig {
  region: string;
  userPoolId: string;
  userPoolClientId: string;
}

const env = (
  import.meta as ImportMeta & {
    readonly env: Record<string, string | undefined>;
  }
).env;

export const frontendConfig: FrontendConfig = {
  region: getRequiredEnv("VITE_AWS_REGION"),
  userPoolId: getRequiredEnv("VITE_COGNITO_USER_POOL_ID"),
  userPoolClientId: getRequiredEnv("VITE_COGNITO_USER_POOL_CLIENT_ID")
};

export function configureAmplify(): void {
  // Amplify is only the browser SDK here. Terraform still owns the Cognito User
  // Pool and app client; these VITE_* values are public identifiers needed by
  // the frontend to talk to that already-created Cognito baseline.
  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId: frontendConfig.userPoolId,
        userPoolClientId: frontendConfig.userPoolClientId
      }
    }
  });

  // Amplify defaults Cognito tokens to localStorage. This app deliberately uses
  // sessionStorage so auth tokens disappear when the browser session ends. This
  // rule is separate from anonymous RSVP tokens, which are not auth credentials.
  cognitoUserPoolsTokenProvider.setKeyValueStorage(sessionStorage);
}

function getRequiredEnv(name: string): string {
  const value = env[name];

  if (!value) {
    throw new Error(`Missing required frontend environment variable: ${name}`);
  }

  return value;
}
