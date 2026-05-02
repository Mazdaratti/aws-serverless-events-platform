interface StatusMessageProps {
  message: string;
}

export function StatusMessage({ message }: StatusMessageProps) {
  return (
    // role="status" is for neutral, non-error updates such as session state or
    // background progress. Errors should use ErrorMessage, and completed
    // positive outcomes should use SuccessMessage.
    <p
      role="status"
      className="m-0 max-w-2xl rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700"
    >
      {message}
    </p>
  );
}
