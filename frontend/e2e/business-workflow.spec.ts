import { expect, test } from "@playwright/test";

const apiURL = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";
const sitePng = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAIAAAAlC+aJAAAAYUlEQVR4nO3PMQ0AIADAMEAm6pCKCI6GZFWwzX32+NnSAa8a0BrQGtAa0BrQGtAa0BrQGtAa0BrQGtAa0BrQGtAa0BrQGtAa0BrQGtAa0BrQGtAa0BrQGtAa0BrQGtAa0C5XDAHUO4QDkwAAAABJRU5ErkJggg==",
  "base64",
);
const maskPng = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAAAAACPAi4CAAAAM0lEQVR4nO3OIQ4AMAgEQej//1xEU4MjNRUz8hI2RAAc2Yc9PFivHwgICAgICAj8FgC4CjPiAUBmicBaAAAAAElFTkSuQmCC",
  "base64",
);

test("runs the complete customer-to-invoice business workflow", async ({ request }) => {
  test.setTimeout(120_000);
  const unique = `${Date.now()}-${test.info().workerIndex}`;
  const email = `workflow-${unique}@example.com`;
  const bootstrap = await request.post(`${apiURL}/api/v1/auth/development-bootstrap`, {
    data: {
      organization_name: `Workflow Landscaping ${unique}`,
      admin_email: email,
      admin_display_name: "Workflow Administrator",
    },
  });
  expect(bootstrap.status()).toBe(201);
  const identity = (await bootstrap.json()) as { access_token: string };
  const headers = { Authorization: `Bearer ${identity.access_token}` };

  const customerResponse = await request.post(`${apiURL}/api/v1/customers`, {
    headers,
    data: { name: "Complete Flow Customer", email: email, address: "100 Demo Way" },
  });
  expect(customerResponse.status()).toBe(201);
  const customer = (await customerResponse.json()) as { id: string };

  try {
    const propertyResponse = await request.post(`${apiURL}/api/v1/properties`, {
      headers,
      data: { customer_id: customer.id, name: "Demo Residence", location: "100 Demo Way" },
    });
    expect(propertyResponse.status()).toBe(201);
    const property = (await propertyResponse.json()) as { id: string };

    const designResponse = await request.post(`${apiURL}/api/v1/design-projects`, {
      headers,
      data: { property_id: property.id, name: "Front lawn transformation", status: "draft" },
    });
    expect(designResponse.status()).toBe(201);
    const design = (await designResponse.json()) as { id: string };

    const captureResponse = await request.post(
      `${apiURL}/api/v1/design-projects/${design.id}/captures`,
      {
        headers,
        multipart: { file: { name: "demo-yard.png", mimeType: "image/png", buffer: sitePng } },
      },
    );
    expect(captureResponse.status()).toBe(201);
    const capture = (await captureResponse.json()) as { id: string };

    const generationResponse = await request.post(
      `${apiURL}/api/v1/design-projects/${design.id}/generations`,
      {
        headers,
        multipart: {
          capture_id: capture.id,
          prompt: "Create a photorealistic landscape concept for the selected area.",
          mask: { name: "mask.png", mimeType: "image/png", buffer: maskPng },
          selected_pixel_count: "1024",
          total_pixel_count: "4096",
          calibration_pixel_length: "1",
          calibration_real_length: "20",
          calibration_unit: "ft",
          estimated_area: "400",
          estimated_perimeter: "80",
          measurement_method: "reference_line",
        },
      },
    );
    expect(generationResponse.status()).toBe(202);
    let generation = (await generationResponse.json()) as { id: string; status: string };
    await expect.poll(async () => {
      const response = await request.get(`${apiURL}/api/v1/generations/${generation.id}`, { headers });
      generation = await response.json();
      return generation.status;
    }, { timeout: 30_000 }).toBe("succeeded");

    const review = await request.post(`${apiURL}/api/v1/generations/${generation.id}/reviews`, {
      headers,
      data: { decision: "approved", notes: "Approved by the automated business workflow." },
    });
    expect(review.status()).toBe(201);

    const estimate = await request.put(
      `${apiURL}/api/v1/generations/${generation.id}/material-estimate`,
      {
        headers,
        data: {
          material_type: "sod",
          waste_percent: "10",
          unit_price: "2.50",
          labour_rate: "55",
          labour_hours: "12",
          delivery_cost: "125",
          tax_rate: "5",
        },
      },
    );
    expect(estimate.status()).toBe(200);
    const estimateRow = (await estimate.json()) as {
      order_quantity: string; material_unit: string; labour_hours: string; delivery_cost: string;
    };

    const quoteResponse = await request.post(`${apiURL}/api/v1/quotes`, {
      headers,
      data: {
        design_project_id: design.id,
        generation_job_id: generation.id,
        title: "Automated landscape installation",
        items: [
          { description: "Sod materials", category: "material", quantity: estimateRow.order_quantity, unit: estimateRow.material_unit, unit_price: "2.50" },
          { description: "Installation labour", category: "labour", quantity: estimateRow.labour_hours, unit: "hour", unit_price: "55" },
          { description: "Delivery", category: "delivery", quantity: "1", unit: "delivery", unit_price: estimateRow.delivery_cost },
        ],
        markup_rate: "10",
        discount_amount: "0",
        tax_rate: "5",
        currency: "CAD",
        assumptions: "Measurements were verified for the automated workflow.",
      },
    });
    expect(quoteResponse.status()).toBe(201);
    const quote = (await quoteResponse.json()) as { id: string; total: string };
    expect((await request.patch(`${apiURL}/api/v1/quotes/${quote.id}/status`, { headers, data: { status: "sent" } })).status()).toBe(200);
    expect((await request.patch(`${apiURL}/api/v1/quotes/${quote.id}/status`, { headers, data: { status: "approved" } })).status()).toBe(200);

    const crewResponse = await request.post(`${apiURL}/api/v1/users`, {
      headers,
      data: { email: `crew-${unique}@example.com`, display_name: "Demo Crew Member", role: "crew" },
    });
    expect(crewResponse.status()).toBe(201);
    const crew = (await crewResponse.json()) as { id: string };
    const start = new Date(Date.now() + 86_400_000);
    const end = new Date(start.getTime() + 28_800_000);
    const workOrderResponse = await request.post(`${apiURL}/api/v1/quotes/${quote.id}/work-order`, {
      headers,
      data: {
        assigned_user_id: crew.id,
        scheduled_start: start.toISOString(),
        scheduled_end: end.toISOString(),
        priority: "high",
        customer_instructions: "Use the side gate and protect the driveway.",
      },
    });
    expect(workOrderResponse.status()).toBe(201);
    const workOrder = (await workOrderResponse.json()) as Record<string, unknown> & { id: string };
    const updateWorkOrder = async (status: "in_progress") => request.put(
      `${apiURL}/api/v1/work-orders/${workOrder.id}`,
      { headers, data: { ...workOrder, status } },
    );
    expect((await updateWorkOrder("in_progress")).status()).toBe(200);
    const completion = await request.post(`${apiURL}/api/v1/work-orders/${workOrder.id}/complete`, {
      headers,
      data: {
        labour_hours: "8",
        labour_rate: "42.50",
        materials: [{ description: "Landscape installation materials", quantity: "1", unit: "job", unit_price: quote.total }],
        notes: "Completed by the automated business workflow.",
      },
    });
    expect(completion.status()).toBe(200);

    const invoice = await request.post(`${apiURL}/api/v1/work-orders/${workOrder.id}/invoice`, { headers });
    expect(invoice.status()).toBe(201);
    const invoiceRecord = (await invoice.json()) as { id: string; total: string };
    const total = Number(invoiceRecord.total);
    expect(total).toBeGreaterThan(0);

    const partialAmount = Math.floor(total * 50) / 100;
    const partial = await request.post(`${apiURL}/api/v1/invoices/${invoiceRecord.id}/payments`, {
      headers,
      data: { amount: partialAmount.toFixed(2), method: "etransfer", reference: "E2E-DEPOSIT" },
    });
    expect(partial.status()).toBe(201);

    const afterPartialResponse = await request.get(`${apiURL}/api/v1/invoices`, { headers });
    const afterPartial = ((await afterPartialResponse.json()) as Array<{ id: string; balance_due: string; status: string }>).find((row) => row.id === invoiceRecord.id);
    expect(afterPartial?.status).toBe("sent");
    expect(Number(afterPartial?.balance_due)).toBeGreaterThan(0);

    const final = await request.post(`${apiURL}/api/v1/invoices/${invoiceRecord.id}/payments`, {
      headers,
      data: { amount: Number(afterPartial?.balance_due).toFixed(2), method: "bank", reference: "E2E-FINAL" },
    });
    expect(final.status()).toBe(201);

    const settledResponse = await request.get(`${apiURL}/api/v1/invoices`, { headers });
    const settled = ((await settledResponse.json()) as Array<{ id: string; balance_due: string; status: string }>).find((row) => row.id === invoiceRecord.id);
    expect(settled?.status).toBe("paid");
    expect(Number(settled?.balance_due)).toBe(0);
  } finally {
    await request.delete(`${apiURL}/api/v1/customers/${customer.id}`, { headers });
  }
});
