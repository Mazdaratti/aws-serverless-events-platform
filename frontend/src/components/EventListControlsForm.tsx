import type { EventListControls } from "../utils/eventListControls";
import { selectInputClassName, textInputClassName } from "./uiStyles";

export interface EventListControlOption<TValue extends string> {
  label: string;
  value: TValue;
}

interface EventListControlsFormProps {
  controls: EventListControls;
  eventStateOptions: Array<
    EventListControlOption<EventListControls["eventState"]>
  >;
  heading: string;
  headingId: string;
  idPrefix: string;
  onChange: (controls: EventListControls) => void;
  sortOptions: Array<EventListControlOption<EventListControls["sort"]>>;
}

const visibilityOptions: Array<
  EventListControlOption<EventListControls["visibility"]>
> = [
  { label: "All", value: "all" },
  { label: "Public", value: "public" },
  { label: "Protected", value: "protected" },
  { label: "Admin-only", value: "admin" }
];

const capacityOptions: Array<
  EventListControlOption<EventListControls["capacity"]>
> = [
  { label: "All", value: "all" },
  { label: "Unlimited capacity", value: "unlimited" },
  { label: "Has capacity limit", value: "limited" },
  { label: "Full", value: "full" },
  { label: "Spots available", value: "available" }
];

export function EventListControlsForm({
  controls,
  eventStateOptions,
  heading,
  headingId,
  idPrefix,
  onChange,
  sortOptions
}: EventListControlsFormProps) {
  return (
    <section aria-labelledby={headingId} className="grid max-w-4xl gap-3">
      <h2 id={headingId} className="sr-only">
        {heading}
      </h2>

      <div className="grid gap-3 md:grid-cols-2">
        <div className="grid gap-1.5 md:col-span-2">
          <label htmlFor={`${idPrefix}-search`}>Search</label>
          <input
            id={`${idPrefix}-search`}
            name="search"
            value={controls.search}
            onChange={(event) =>
              onChange({
                ...controls,
                search: event.target.value
              })
            }
            className={textInputClassName}
            placeholder="Title, description, or location"
          />
        </div>

        <div className="grid gap-1.5">
          <label htmlFor={`${idPrefix}-state-filter`}>Event state</label>
          <select
            id={`${idPrefix}-state-filter`}
            name="eventState"
            value={controls.eventState}
            onChange={(event) =>
              onChange({
                ...controls,
                eventState: event.target.value as EventListControls["eventState"]
              })
            }
            className={selectInputClassName}
          >
            {eventStateOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="grid gap-1.5">
          <label htmlFor={`${idPrefix}-visibility-filter`}>Visibility</label>
          <select
            id={`${idPrefix}-visibility-filter`}
            name="visibility"
            value={controls.visibility}
            onChange={(event) =>
              onChange({
                ...controls,
                visibility: event.target.value as EventListControls["visibility"]
              })
            }
            className={selectInputClassName}
          >
            {visibilityOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="grid gap-1.5">
          <label htmlFor={`${idPrefix}-capacity-filter`}>
            RSVP availability
          </label>
          <select
            id={`${idPrefix}-capacity-filter`}
            name="capacity"
            value={controls.capacity}
            onChange={(event) =>
              onChange({
                ...controls,
                capacity: event.target.value as EventListControls["capacity"]
              })
            }
            className={selectInputClassName}
          >
            {capacityOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="grid gap-1.5">
          <label htmlFor={`${idPrefix}-sort`}>Sort</label>
          <select
            id={`${idPrefix}-sort`}
            name="sort"
            value={controls.sort}
            onChange={(event) =>
              onChange({
                ...controls,
                sort: event.target.value as EventListControls["sort"]
              })
            }
            className={selectInputClassName}
          >
            {sortOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>
    </section>
  );
}
