import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LoadingState } from "./LoadingState";

describe("LoadingState", () => {
  it("renders the default loading message", () => {
    render(<LoadingState />);

    expect(screen.getByRole("status")).toHaveTextContent("Loading...");
  });

  it("renders a custom loading message", () => {
    render(<LoadingState message="Loading events..." />);

    expect(screen.getByRole("status")).toHaveTextContent("Loading events...");
  });

  it("exposes polite live-region semantics for assistive technology", () => {
    render(<LoadingState message="Loading events..." />);

    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
    expect(screen.getByRole("status")).toHaveAttribute("aria-atomic", "true");
  });
});
