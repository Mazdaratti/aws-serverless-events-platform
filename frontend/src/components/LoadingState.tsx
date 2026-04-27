import { StatusMessage } from "./StatusMessage";

interface LoadingStateProps {
  message?: string;
}

export function LoadingState({
  message = "Loading..."
}: LoadingStateProps) {
  return (
    // Loading is a specific kind of neutral status, so keep the accessibility
    // semantics in StatusMessage and let this component name the loading intent.
    <StatusMessage message={message} />
  );
}
