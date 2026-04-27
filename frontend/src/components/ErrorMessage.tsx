interface ErrorMessageProps {
  message: string;
}

export function ErrorMessage({ message }: ErrorMessageProps) {
  return (
    // role="alert" makes the error announce immediately for assistive
    // technology. Pages should pass already-safe user-facing text here, not raw
    // exception objects or backend internals.
    <p role="alert">
      {message}
    </p>
  );
}
