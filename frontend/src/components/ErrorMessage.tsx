interface ErrorMessageProps {
  message: string;
}

export function ErrorMessage({ message }: ErrorMessageProps) {
  return (
    // role="alert" makes the error announce immediately for assistive
    // technology. Pages should pass already-safe user-facing text here, not raw
    // exception objects or backend internals.
    <p
      role="alert"
      className="m-0 max-w-2xl rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
    >
      {message}
    </p>
  );
}
