import type { ComponentProps } from "react";
import { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import {
  EventListControlsForm,
  type EventListControlOption
} from "./EventListControlsForm";
import {
  myEventsDefaultControls,
  publicEventListDefaultControls,
  type EventListControls
} from "../utils/eventListControls";

const publicEventStateOptions: Array<
  EventListControlOption<EventListControls["eventState"]>
> = [
  { label: "All", value: "all" },
  { label: "Ongoing", value: "ongoing" },
  { label: "Outdated", value: "outdated" }
];

const myEventsEventStateOptions: Array<
  EventListControlOption<EventListControls["eventState"]>
> = [
  { label: "All", value: "all" },
  { label: "Ongoing", value: "ongoing" },
  { label: "Cancelled", value: "cancelled" },
  { label: "Outdated", value: "outdated" }
];

const publicSortOptions: Array<
  EventListControlOption<EventListControls["sort"]>
> = [
  { label: "Event date: soonest first", value: "date-asc" },
  { label: "Event date: latest first", value: "date-desc" },
  { label: "Title: A to Z", value: "title-asc" },
  { label: "Title: Z to A", value: "title-desc" },
  { label: "Created: newest first", value: "created-desc" }
];

function renderForm(
  overrides: Partial<ComponentProps<typeof EventListControlsForm>> = {}
) {
  const onChangeSpy =
    overrides.onChange ?? vi.fn<(controls: EventListControls) => void>();
  const initialControls = overrides.controls ?? publicEventListDefaultControls;

  function TestHarness() {
    const [controls, setControls] = useState(initialControls);

    return (
      <EventListControlsForm
        controls={controls}
        eventStateOptions={publicEventStateOptions}
        heading="Find events"
        headingId="event-list-controls"
        idPrefix="event-list"
        onChange={(nextControls) => {
          onChangeSpy(nextControls);
          setControls(nextControls);
        }}
        sortOptions={publicSortOptions}
        {...overrides}
      />
    );
  }

  render(<TestHarness />);

  return { onChange: onChangeSpy };
}

describe("EventListControlsForm", () => {
  it("renders accessible labels for all controls", () => {
    renderForm();

    expect(screen.getByLabelText("Search")).toBeInTheDocument();
    expect(screen.getByLabelText("Event state")).toBeInTheDocument();
    expect(screen.getByLabelText("Visibility")).toBeInTheDocument();
    expect(screen.getByLabelText("RSVP availability")).toBeInTheDocument();
    expect(screen.getByLabelText("Sort")).toBeInTheDocument();
  });

  it("does not show the Cancelled option in the public event-state filter", () => {
    renderForm();

    expect(
      screen.getByRole("option", { name: "Ongoing" })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("option", { name: "Cancelled" })
    ).not.toBeInTheDocument();
  });

  it("can show the Cancelled option for owner event-state controls", () => {
    renderForm({
      controls: myEventsDefaultControls,
      eventStateOptions: myEventsEventStateOptions,
      heading: "Filter my events",
      headingId: "my-events-controls",
      idPrefix: "my-events"
    });

    expect(
      screen.getByRole("option", { name: "Cancelled" })
    ).toBeInTheDocument();
  });

  it("calls onChange with updated controls when search changes", async () => {
    const user = userEvent.setup();
    const { onChange } = renderForm();

    await user.type(screen.getByLabelText("Search"), "berlin");

    expect(onChange).toHaveBeenLastCalledWith({
      ...publicEventListDefaultControls,
      search: "berlin"
    });
  });

  it("calls onChange with updated controls when event state changes", async () => {
    const user = userEvent.setup();
    const { onChange } = renderForm();

    await user.selectOptions(screen.getByLabelText("Event state"), "outdated");

    expect(onChange).toHaveBeenLastCalledWith({
      ...publicEventListDefaultControls,
      eventState: "outdated"
    });
  });
});
