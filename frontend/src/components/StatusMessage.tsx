interface StatusMessageProps {
  message: string;
}

export function StatusMessage({ message }: StatusMessageProps) {
  return (
    // role="status" is for neutral, non-error updates such as session state or
    // background progress. Errors should use ErrorMessage, and completed
    // positive outcomes should use SuccessMessage.
    <p role="status">
      {message}
    </p>
  );
}
