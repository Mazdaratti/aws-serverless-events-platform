import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <>
      {/* This is a frontend route miss under /app, not an API 404 from /events.
          Keeping that distinction visible prevents UI routing from masking
          backend error responses. */}
      <h1>Page not found</h1>
      <p>The requested app page does not exist.</p>
      <Link to="/events">Back to events</Link>
    </>
  );
}
