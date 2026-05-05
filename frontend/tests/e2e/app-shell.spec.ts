import { expect, test } from "@playwright/test";

test.describe("app shell", () => {
  test("loads the app shell from /app root", async ({ page }) => {
    // The public events page fetches /events on first render. Mock it here so
    // this smoke test stays local and deterministic instead of depending on a
    // deployed backend.
    await page.route("**/events", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], next_cursor: null })
      });
    });

    await page.goto("/app");

    await expect(page).toHaveURL(/\/app\/events$/);
    await expect(page.getByRole("banner")).toBeVisible();
    await expect(page.getByRole("main")).toBeVisible();
  });

  test("renders the public events page shell", async ({ page }) => {
    await page.route("**/events", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], next_cursor: null })
      });
    });

    await page.goto("/app");

    await expect(page.getByRole("main")).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Events", exact: true })
    ).toBeVisible();
  });

  test("renders a protected prompt for my events instead of crashing", async ({
    page
  }) => {
    await page.goto("/app/my-events");

    const main = page.getByRole("main");

    await expect(main).toBeVisible();
    await expect(page.getByRole("heading", { name: "My events" })).toBeVisible();
    await expect(
      page.getByText("You need to sign in before viewing your events.")
    ).toBeVisible();
    await expect(main.getByRole("link", { name: "Login" })).toBeVisible();
  });
});
