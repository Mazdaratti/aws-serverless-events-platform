interface SuccessMessageProps {
  message: string;
}

export function SuccessMessage({ message }: SuccessMessageProps) {
  return (
    // role="status" announces successful non-error feedback politely. This is
    // intentionally less urgent than ErrorMessage, which uses role="alert".
    <p role="status">
      {message}
    </p>
  );
}
