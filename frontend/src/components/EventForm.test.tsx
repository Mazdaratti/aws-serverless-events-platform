import type { ComponentProps } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { EventForm, emptyEventFormValues } from "./EventForm";

function renderForm(overrides?: Partial<ComponentProps<typeof EventForm>>) {
  const onSubmit =
    overrides?.onSubmit ?? vi.fn().mockResolvedValue(undefined);

  render(
    <EventForm
      initialValues={emptyEventFormValues}
      submitButtonLabel="Create event"
      submittingButtonLabel="Creating event..."
      isSubmitting={false}
      onSubmit={onSubmit}
      {...overrides}
    />
  );

  return { onSubmit };
}

describe("EventForm", () => {
  it("shows the validation alert when capacity is 0", async () => {
    const user = userEvent.setup();
    const { onSubmit } = renderForm();

    await user.type(screen.getByLabelText("Title"), "React Meetup");
    await user.type(screen.getByLabelText("Date and time"), "2026-06-15T19:30");
    await user.type(screen.getByLabelText("Capacity"), "0");
    await user.click(screen.getByRole("button", { name: "Create event" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Capacity must be a whole number greater than or equal to 1, or blank for unlimited."
    );
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("sets aria-invalid on the capacity field for capacity validation errors", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText("Title"), "React Meetup");
    await user.type(screen.getByLabelText("Date and time"), "2026-06-15T19:30");
    await user.type(screen.getByLabelText("Capacity"), "0");
    await user.click(screen.getByRole("button", { name: "Create event" }));

    expect(screen.getByLabelText("Capacity")).toHaveAttribute(
      "aria-invalid",
      "true"
    );
  });

  it("calls onSubmit with a normalized payload for a valid submit", async () => {
    const user = userEvent.setup();
    const { onSubmit } = renderForm();

    await user.type(screen.getByLabelText("Title"), "  React Meetup  ");
    await user.type(screen.getByLabelText("Date and time"), "2026-06-15T19:30");
    await user.type(screen.getByLabelText("Location"), "  Berlin  ");
    await user.type(screen.getByLabelText("Description"), "  Community event  ");
    await user.selectOptions(screen.getByLabelText("Visibility"), "admin");
    await user.click(screen.getByRole("button", { name: "Create event" }));

    expect(onSubmit).toHaveBeenCalledWith({
      title: "React Meetup",
      date: new Date("2026-06-15T19:30").toISOString(),
      description: "Community event",
      location: "Berlin",
      capacity: null,
      is_public: false,
      requires_admin: true
    });
  });
});
