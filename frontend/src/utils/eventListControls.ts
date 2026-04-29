import type { PublicEvent } from "../api/types";

export type EventStateFilter = "all" | "ongoing" | "cancelled" | "outdated";
export type VisibilityFilter = "all" | "public" | "protected" | "admin";
export type CapacityFilter =
  | "all"
  | "unlimited"
  | "limited"
  | "full"
  | "available";

export type EventSort =
  | "date-asc"
  | "date-desc"
  | "title-asc"
  | "title-desc"
  | "status-active-first"
  | "status-cancelled-first"
  | "created-desc"
  | "created-asc";

export interface EventListControls {
  search: string;
  eventState: EventStateFilter;
  visibility: VisibilityFilter;
  capacity: CapacityFilter;
  sort: EventSort;
}

export const publicEventListDefaultControls: EventListControls = {
  search: "",
  // Public discovery should start with upcoming active events so cancelled or
  // old records do not dominate the default browsing experience.
  eventState: "ongoing",
  visibility: "all",
  capacity: "all",
  sort: "date-asc"
};

export const myEventsDefaultControls: EventListControls = {
  search: "",
  // Owner management should show every owned event by default, including past
  // and cancelled records that may still need review.
  eventState: "all",
  visibility: "all",
  capacity: "all",
  sort: "date-asc"
};

export function applyEventListControls(
  events: PublicEvent[],
  controls: EventListControls,
  nowMs: number = Date.now()
): PublicEvent[] {
  return [...events]
    .filter((event) => matchesSearch(event, controls.search))
    .filter((event) => matchesEventState(event, controls.eventState, nowMs))
    .filter((event) => matchesVisibility(event, controls.visibility))
    .filter((event) => matchesCapacity(event, controls.capacity))
    .sort((firstEvent, secondEvent) =>
      compareEvents(firstEvent, secondEvent, controls.sort)
    );
}

export function hasActiveEventListControls(
  controls: EventListControls,
  defaults: EventListControls
): boolean {
  return (
    controls.search !== defaults.search ||
    controls.eventState !== defaults.eventState ||
    controls.visibility !== defaults.visibility ||
    controls.capacity !== defaults.capacity ||
    controls.sort !== defaults.sort
  );
}

function matchesSearch(event: PublicEvent, rawSearch: string): boolean {
  const search = rawSearch.trim().toLocaleLowerCase();
  if (!search) {
    return true;
  }

  // Search only fields that are meaningful to users today. created_by is a
  // Cognito sub, so it is intentionally excluded until the backend exposes a
  // safe display name.
  return [event.title, event.description, event.location].some((value) =>
    (value ?? "").toLocaleLowerCase().includes(search)
  );
}

function matchesEventState(
  event: PublicEvent,
  filter: EventStateFilter,
  nowMs: number
): boolean {
  if (filter === "all") {
    return true;
  }

  if (filter === "cancelled") {
    return event.status === "CANCELLED";
  }

  if (event.status !== "ACTIVE") {
    return false;
  }

  const eventTime = getTimeValue(event.date);
  if (eventTime === null) {
    return filter === "ongoing";
  }

  if (filter === "ongoing") {
    return eventTime > nowMs;
  }

  return eventTime <= nowMs;
}

function matchesVisibility(
  event: PublicEvent,
  filter: VisibilityFilter
): boolean {
  if (filter === "all") {
    return true;
  }

  if (filter === "admin") {
    return event.requires_admin;
  }

  if (filter === "protected") {
    return !event.is_public && !event.requires_admin;
  }

  return event.is_public && !event.requires_admin;
}

function matchesCapacity(event: PublicEvent, filter: CapacityFilter): boolean {
  if (filter === "all") {
    return true;
  }

  if (filter === "unlimited") {
    return event.capacity === null;
  }

  if (filter === "limited") {
    return event.capacity !== null;
  }

  if (filter === "full") {
    return event.capacity !== null && event.attending_count >= event.capacity;
  }

  return event.capacity === null || event.attending_count < event.capacity;
}

function compareEvents(
  firstEvent: PublicEvent,
  secondEvent: PublicEvent,
  sort: EventSort
): number {
  if (sort === "date-asc") {
    return compareDates(firstEvent.date, secondEvent.date, "asc");
  }

  if (sort === "date-desc") {
    return compareDates(firstEvent.date, secondEvent.date, "desc");
  }

  if (sort === "title-asc") {
    return compareText(firstEvent.title, secondEvent.title, "asc");
  }

  if (sort === "title-desc") {
    return compareText(firstEvent.title, secondEvent.title, "desc");
  }

  if (sort === "status-active-first") {
    return compareStatus(firstEvent, secondEvent, "ACTIVE");
  }

  if (sort === "status-cancelled-first") {
    return compareStatus(firstEvent, secondEvent, "CANCELLED");
  }

  if (sort === "created-asc") {
    return compareDates(firstEvent.created_at, secondEvent.created_at, "asc");
  }

  return compareDates(firstEvent.created_at, secondEvent.created_at, "desc");
}

function compareDates(
  firstValue: string,
  secondValue: string,
  direction: "asc" | "desc"
): number {
  const firstTime = getTimeValue(firstValue);
  const secondTime = getTimeValue(secondValue);

  if (firstTime === null && secondTime === null) {
    return compareText(firstValue, secondValue, direction);
  }

  if (firstTime === null) {
    return 1;
  }

  if (secondTime === null) {
    return -1;
  }

  return direction === "asc"
    ? firstTime - secondTime
    : secondTime - firstTime;
}

function compareText(
  firstValue: string,
  secondValue: string,
  direction: "asc" | "desc"
): number {
  const result = firstValue.localeCompare(secondValue, undefined, {
    sensitivity: "base"
  });

  return direction === "asc" ? result : -result;
}

function compareStatus(
  firstEvent: PublicEvent,
  secondEvent: PublicEvent,
  firstStatus: PublicEvent["status"]
): number {
  if (firstEvent.status === secondEvent.status) {
    return compareDates(firstEvent.date, secondEvent.date, "asc");
  }

  if (firstEvent.status === firstStatus) {
    return -1;
  }

  return 1;
}

function getTimeValue(value: string): number | null {
  const time = new Date(value).getTime();

  if (Number.isNaN(time)) {
    return null;
  }

  return time;
}
