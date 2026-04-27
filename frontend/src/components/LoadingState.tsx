interface LoadingStateProps {
  message?: string;
}

export function LoadingState({
  message = "Loading..."
}: LoadingStateProps) {
  return (
    // role="status" and aria-live tell assistive technology that this text is
    // a non-disruptive status update. Keep this component small so pages can
    // reuse it for API reads, auth checks, and submit transitions.
    <p role="status" aria-live="polite">
      {message}
    </p>
  );
}
