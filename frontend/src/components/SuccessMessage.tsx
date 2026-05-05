interface SuccessMessageProps {
  message: string;
}

export function SuccessMessage({ message }: SuccessMessageProps) {
  return (
    // role="status" announces successful non-error feedback politely. This is
    // intentionally less urgent than ErrorMessage, which uses role="alert".
    <p
      role="status"
      className="m-0 max-w-2xl rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800"
    >
      {message}
    </p>
  );
}
