import { expect, test } from "@playwright/test";

const apiURL = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";

test("shows the secure workspace sign-in screen", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: "Sign in to continue" }),
  ).toBeVisible();
  await expect(page.getByLabel("Organization ID")).toBeVisible();
  await expect(page.getByLabel("Email")).toBeVisible();
  await expect(page.getByRole("button", { name: "Open workspace" })).toBeVisible();
});

test("rejects anonymous access to organization data", async ({ request }) => {
  const response = await request.get(`${apiURL}/api/v1/customers`);

  expect(response.status()).toBe(401);
});

test("opens a bootstrapped development workspace", async ({ page, request }) => {
  const unique = `${Date.now()}-${test.info().workerIndex}`;
  const email = `e2e-${unique}@example.com`;
  const bootstrap = await request.post(
    `${apiURL}/api/v1/auth/development-bootstrap`,
    {
      data: {
        organization_name: `E2E Landscaping ${unique}`,
        admin_email: email,
        admin_display_name: "E2E Administrator",
      },
    },
  );

  expect(bootstrap.status()).toBe(201);
  const identity = (await bootstrap.json()) as { organization_id: string };

  await page.goto("/");
  await page.getByLabel("Organization ID").fill(identity.organization_id);
  await page.getByLabel("Email").fill(email);
  await page.getByRole("button", { name: "Open workspace" }).click();

  await expect(page.getByText("Overview", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Sign out", { exact: true })).toBeVisible();
  await expect(page.getByText("Customers", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Properties", { exact: true }).first()).toBeVisible();
});

test("keeps grouped tools available while navigating between them", async ({ page, request }) => {
  const unique = `${Date.now()}-${test.info().workerIndex}`;
  const email = `tools-${unique}@example.com`;
  const bootstrap = await request.post(
    `${apiURL}/api/v1/auth/development-bootstrap`,
    {
      data: {
        organization_name: `Tools Landscaping ${unique}`,
        admin_email: email,
        admin_display_name: "Tools Administrator",
      },
    },
  );
  expect(bootstrap.status()).toBe(201);
  const identity = (await bootstrap.json()) as { organization_id: string };

  await page.goto("/");
  await page.getByLabel("Organization ID").fill(identity.organization_id);
  await page.getByLabel("Email").fill(email);
  await page.getByRole("button", { name: "Open workspace" }).click();

  await page.getByRole("button", { name: "Invoices" }).click();
  await expect(page.getByRole("heading", { name: "Invoices" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Timesheets" })).toBeVisible();
  await page.getByRole("button", { name: "Timesheets" }).click();
  await expect(
    page.getByRole("heading", { name: "Timesheets", exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Field tools" })).toBeVisible();
});

test("shows camera measurement in Design Studio without a load error", async ({ page, request }) => {
  test.setTimeout(60_000);
  await page.addInitScript(() => {
    const original = navigator.mediaDevices;
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        ...original,
        getUserMedia: async () => {
          const canvas = document.createElement("canvas");
          canvas.width = 640;
          canvas.height = 480;
          const context = canvas.getContext("2d");
          context?.fillRect(0, 0, canvas.width, canvas.height);
          return canvas.captureStream(10);
        },
      },
    });
  });
  const unique = `${Date.now()}-${test.info().workerIndex}`;
  const email = `design-${unique}@example.com`;
  const bootstrap = await request.post(
    `${apiURL}/api/v1/auth/development-bootstrap`,
    {
      data: {
        organization_name: `Design Landscaping ${unique}`,
        admin_email: email,
        admin_display_name: "Design Administrator",
      },
    },
  );
  expect(bootstrap.status()).toBe(201);
  const identity = (await bootstrap.json()) as {
    organization_id: string;
    access_token: string;
  };
  const headers = { Authorization: `Bearer ${identity.access_token}` };
  const customer = await request.post(`${apiURL}/api/v1/customers`, {
    headers,
    data: { name: "Camera Customer" },
  });
  expect(customer.status()).toBe(201);
  const customerRow = (await customer.json()) as { id: string };
  const property = await request.post(`${apiURL}/api/v1/properties`, {
    headers,
    data: { customer_id: customerRow.id, name: "Camera Property" },
  });
  expect(property.status()).toBe(201);
  const propertyRow = (await property.json()) as { id: string };
  const design = await request.post(`${apiURL}/api/v1/design-projects`, {
    headers,
    data: { property_id: propertyRow.id, name: "Camera Design", status: "draft" },
  });
  expect(design.status()).toBe(201);

  await page.route("**/api/v1/design-projects/*/generations", async (route) => {
    await route.fulfill({
      status: 502,
      contentType: "text/html",
      body: "Bad gateway",
    });
  });

  await page.goto("/");
  await page.getByLabel("Organization ID").fill(identity.organization_id);
  await page.getByLabel("Email").fill(email);
  await page.getByRole("button", { name: "Open workspace" }).click();
  await page.getByRole("button", { name: "Design studio", exact: true }).click();

  await expect(page.getByRole("button", { name: "Measure with camera" })).toBeVisible();
  await expect(page.getByText("Not Found", { exact: true })).toHaveCount(0);
  await expect(
    page.getByText("The request could not be completed.", { exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Overview" }).click();
  await page.getByRole("button", { name: "Design studio", exact: true }).click();
  await expect(
    page.getByText("The request could not be completed.", { exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Measure with camera" }).click();
  await expect(page.getByRole("dialog", { name: "Camera measurement" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Capture measurement frame" })).toBeEnabled();
  await page.getByRole("button", { name: "Close camera measurement" }).click();
  await page.reload();
  await expect(page.getByText("Not Found", { exact: true })).toHaveCount(0);
});

test("places workspace navigation at the top on mobile", async ({ page, request }) => {
  const unique = `${Date.now()}-${test.info().workerIndex}`;
  const email = `mobile-${unique}@example.com`;
  const bootstrap = await request.post(`${apiURL}/api/v1/auth/development-bootstrap`, {
    data: {
      organization_name: `Mobile Landscaping ${unique}`,
      admin_email: email,
      admin_display_name: "Mobile Administrator",
    },
  });
  expect(bootstrap.status()).toBe(201);
  const identity = (await bootstrap.json()) as { organization_id: string };
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByLabel("Organization ID").fill(identity.organization_id);
  await page.getByLabel("Email").fill(email);
  await page.getByRole("button", { name: "Open workspace" }).click();
  const menu = page.getByRole("button", { name: "Menu" });
  await expect(menu).toBeVisible();
  const menuBox = await menu.boundingBox();
  expect(menuBox?.y ?? 9999).toBeLessThan(120);
  await menu.click();
  await expect(page.getByRole("button", { name: "Customers", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Customers", exact: true }).click();
  await expect(page.getByRole("button", { name: "Menu" })).toBeVisible();
});

