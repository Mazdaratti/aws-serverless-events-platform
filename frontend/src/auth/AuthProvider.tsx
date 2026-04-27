import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode
} from "react";
import { fetchAuthSession, getCurrentUser, signOut } from "aws-amplify/auth";

export type AuthStatus = "loading" | "anonymous" | "authenticated" | "expired";

export interface AuthUser {
  username: string;
  userId: string;
}

interface AuthContextValue {
  status: AuthStatus;
  user: AuthUser | null;
  refreshSession: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<AuthUser | null>(null);

  const refreshSession = useCallback(async () => {
    setStatus("loading");

    try {
      const [currentUser, session] = await Promise.all([
        getCurrentUser(),
        fetchAuthSession()
      ]);

      // The backend authorizers validate the Cognito ID-token path today. If
      // Amplify can identify a current user but no ID token is available, treat
      // the session as expired instead of pretending the user is anonymous.
      if (!session.tokens?.idToken) {
        setUser(null);
        setStatus("expired");
        return;
      }

      // userId is the Cognito sub. UI may display username, but backend-facing
      // identity remains Cognito-managed and must not be invented in the app.
      setUser({
        username: currentUser.username,
        userId: currentUser.userId
      });
      setStatus("authenticated");
    } catch {
      // No current Cognito user is a normal state for public browsing. Public
      // pages and anonymous RSVP can still work without an auth session.
      setUser(null);
      setStatus("anonymous");
    }
  }, []);

  const logout = useCallback(async () => {
    await signOut();
    setUser(null);
    setStatus("anonymous");
  }, []);

  useEffect(() => {
    void refreshSession();
  }, [refreshSession]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      refreshSession,
      logout
    }),
    [logout, refreshSession, status, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);

  if (!value) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }

  return value;
}
