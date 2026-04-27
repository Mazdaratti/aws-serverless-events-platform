import type { IsoDateTime } from "../api/types";

const eventDateFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short"
});

export function formatEventDate(value: IsoDateTime): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  // Backend DTOs provide ISO timestamps. Formatting in one helper keeps event
  // list/detail pages consistent and avoids every page choosing its own locale
  // behavior.
  return eventDateFormatter.format(date);
}
