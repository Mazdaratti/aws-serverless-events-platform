import { Link } from "react-router-dom";

import {
  PageActions,
  PageHeader,
  PageLayout,
  Panel
} from "../components/LayoutPrimitives";
import { pageTitleClassName, primaryButtonClassName } from "../components/uiStyles";

export function NotFoundPage() {
  return (
    <PageLayout>
      {/* This is a frontend route miss under /app, not an API 404 from /events.
          Keeping that distinction visible prevents UI routing from masking
          backend error responses. */}
      <PageHeader>
        <div>
          <h1 className={pageTitleClassName}>Page not found</h1>
          <p className="m-0 max-w-2xl text-sm leading-6 text-slate-600">
            The requested app page does not exist.
          </p>
        </div>
      </PageHeader>

      <Panel className="text-center">
        <p className="m-0 text-sm text-slate-600">
          Return to the event list to continue.
        </p>
        <PageActions className="mt-3 justify-center">
          <Link
            className={primaryButtonClassName}
            to="/events"
          >
            Back to events
          </Link>
        </PageActions>
      </Panel>
    </PageLayout>
  );
}
