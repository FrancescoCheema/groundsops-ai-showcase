export type Customer = {
  id: string;
  name: string;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
};
export type Organization = {
  id: string;
  name: string;
  logo_media_type?: string | null;
  invoice_logo_media_type?: string | null;
  created_at: string;
};
export type Property = {
  id: string;
  customer_id?: string | null;
  name: string;
  location?: string | null;
};
export type Design = {
  id: string;
  property_id: string;
  name: string;
  goal?: string | null;
  status: string;
};
export type Capture = {
  id: string;
  design_project_id: string;
  original_filename: string;
  media_type: string;
  byte_size: number;
  width: number;
  height: number;
  status: string;
  created_at: string;
};
export type InvoiceItem = {
  id?: string;
  description: string;
  quantity: string;
  rate: string;
  line_total?: string;
  position?: number;
};
export type Invoice = {
  id: string;
  customer_id?: string | null;
  work_order_id?: string | null;
  number: string;
  items: InvoiceItem[];
  subtotal: string;
  currency: string;
  status: string;
  notes?: string | null;
  customer_name?: string | null;
  customer_email?: string | null;
  customer_phone?: string | null;
  customer_address?: string | null;
  company_email?: string | null;
  company_phone?: string | null;
  company_address?: string | null;
  gst_rate: string;
  pst_rate: string;
  gst_amount: string;
  pst_amount: string;
  total: string;
  paid_amount: string;
  balance_due: string;
  payments: Array<{
    id: string;
    amount: string;
    method: string;
    reference?: string | null;
    received_at: string;
  }>;
  created_at: string;
};
export type Timesheet = {
  id: string;
  user_id: string;
  employee_name: string;
  property_id?: string | null;
  property_name?: string | null;
  started_at: string;
  ended_at?: string | null;
  status: string;
  notes?: string | null;
};
export type CurrentUser = {
  id: string;
  organization_id: string;
  email: string;
  role: "admin" | "manager" | "designer" | "crew";
  platform_admin: boolean;
};
export type GenerationMetrics = {
  total_generations: number;
  completed_generations: number;
  evaluated_generations: number;
  passed_generations: number;
  failed_evaluations: number;
  unevaluated_generations: number;
  pass_rate?: number | null;
  average_generation_latency_ms?: number | null;
  average_evaluation_latency_ms?: number | null;
  estimated_cost_usd: string;
  failure_reasons: { reason: string; count: number }[];
  models: {
    model_version: string;
    total: number;
    evaluated: number;
    passed: number;
    pass_rate?: number | null;
    average_latency_ms?: number | null;
    estimated_cost_usd: string;
  }[];
  trends: {
    date: string;
    total: number;
    evaluated: number;
    passed: number;
    failed: number;
    pass_rate?: number | null;
  }[];
  review_queue: {
    job_id: string;
    design_project_id: string;
    prompt: string;
    model_version: string;
    created_at: string;
    evaluation_id: string;
    masked_change_ratio: string;
    protected_change_ratio: string;
    failure_reasons: string[];
  }[];
};
export type GenerationJob = {
  id: string;
  organization_id: string;
  design_project_id: string;
  capture_id: string;
  prompt: string;
  provider: string;
  model_version: string;
  status: "queued" | "running" | "succeeded" | "failed";
  measurement_method?: "mask_pixels" | "reference_line" | null;
  selected_pixel_count?: number | null;
  total_pixel_count?: number | null;
  calibration_pixel_length?: string | null;
  calibration_real_length?: string | null;
  calibration_unit?: "ft" | "m" | null;
  estimated_area?: string | null;
  estimated_perimeter?: string | null;
  measurement_confidence?: "uncalibrated" | "photo_estimate" | null;
  latency_ms?: number | null;
  estimated_cost_usd?: string | null;
  error_message?: string | null;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
};
export type GenerationReview = {
  id: string;
  organization_id: string;
  generation_job_id: string;
  reviewer_user_id: string;
  decision: "approved" | "rejected" | "revision_requested";
  notes?: string | null;
  created_at: string;
};
export type GenerationMaterialEstimate = {
  id: string;
  generation_job_id: string;
  material_type: "sod" | "pavers" | "mulch" | "gravel" | "topsoil";
  measurement_unit: "ft" | "m";
  measured_area: string;
  measured_perimeter: string;
  waste_percent: string;
  depth?: string | null;
  order_quantity: string;
  material_unit: string;
  edging_quantity: string;
  labour_hours: string;
  unit_price: string;
  labour_rate: string;
  delivery_cost: string;
  material_cost: string;
  labour_cost: string;
  subtotal: string;
  tax_rate: string;
  tax_amount: string;
  total: string;
  currency: string;
  assumptions: string[];
  created_at: string;
  updated_at: string;
};
export type QuoteItem = { id?: string; description: string; category: "material" | "labour" | "equipment" | "delivery" | "other"; quantity: string; unit: string; unit_price: string; line_total?: string; position?: number; };
export type Quote = { id: string; design_project_id: string; generation_job_id?: string | null; number: string; title: string; status: "draft" | "sent" | "approved" | "rejected" | "expired"; items: QuoteItem[]; subtotal: string; markup_rate: string; markup_amount: string; discount_amount: string; tax_rate: string; tax_amount: string; total: string; currency: string; assumptions?: string | null; created_at: string; updated_at: string; };
export type OrganizationUser = {
  id: string;
  organization_id: string;
  email: string;
  display_name: string;
  role: "admin" | "manager" | "designer" | "crew";
  active: boolean;
};
export type OrganizationInvitation = {
  id: string;
  organization_id: string;
  email: string;
  role: "admin" | "manager" | "designer" | "crew";
  expires_at: string;
  accepted_at?: string | null;
  revoked_at?: string | null;
  created_at: string;
  acceptance_token?: string;
};
export type PlatformOrganization = {
  id: string;
  name: string;
  created_at: string;
  user_count: number;
  active_user_count: number;
};
export type PlatformUser = OrganizationUser & {
  organization_name: string;
  created_at: string;
};
export type WorkOrder = {
  id: string;
  property_id: string;
  quote_id?: string | null;
  design_project_id?: string | null;
  title: string;
  description: string;
  status: string;
  assigned_user_id?: string | null;
  scheduled_start?: string | null;
  scheduled_end?: string | null;
  priority: "low" | "normal" | "high" | "urgent";
  quoted_total?: string | null;
  quote_currency?: string | null;
  material_checklist?: Array<{ description: string; category: string; quantity: string; unit: string }> | null;
  customer_instructions?: string | null;
  actual_labour_hours?: string | null;
  actual_labour_rate?: string | null;
  actual_materials?: Array<{
    description: string;
    quantity: string;
    unit: string;
    unit_price: string;
    line_total: string;
  }> | null;
  actual_total?: string | null;
  completion_notes?: string | null;
  completed_at?: string | null;
  created_at: string;
};
export type VaultFile = {
  id: string;
  uploaded_by_user_id: string;
  folder_id?: string | null;
  site_id?: string | null;
  original_filename: string;
  media_type: string;
  byte_size: number;
  access_scope: "organization" | "management" | "private";
  deleted_at?: string | null;
  created_at: string;
};
export type VaultFolder = {
  id: string;
  name: string;
  site_id?: string | null;
  created_by_user_id: string;
  access_scope: "organization" | "management" | "private";
  deleted_at?: string | null;
  created_at: string;
};
export type VaultSite = {
  id: string;
  name: string;
  description?: string | null;
  created_by_user_id: string;
  access_scope: "organization" | "management" | "private";
  deleted_at?: string | null;
  created_at: string;
};
export type VaultStorage = {
  used_bytes: number;
  quota_bytes: number;
  available_bytes: number;
};

export async function downloadVaultFile(
  id: string,
  token: string,
  preview = false,
): Promise<Blob> {
  if (process.env.NEXT_PUBLIC_STORAGE_DIRECT_URLS === "true") {
    const signed = await fetch(
      `${apiBase()}/api/v1/vault/files/${id}/signed-url?preview=${preview}`,
      { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" },
    );
    if (signed.ok) {
      const body = await signed.json() as { url: string };
      const objectResponse = await fetch(body.url, { cache: "no-store" });
      if (!objectResponse.ok) throw new Error("The private file could not be downloaded.");
      return objectResponse.blob();
    }
  }
  const response = await fetch(
    `${apiBase()}/api/v1/vault/files/${id}/content?preview=${preview}`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  if (!response.ok) throw new Error(await errorMessage(response));
  return response.blob();
}

export async function downloadAuthenticated(path: string, token: string): Promise<Blob> {
  const response = await fetch(`${apiBase()}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error(await errorMessage(response));
  return response.blob();
}

export function apiBase(): string {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  if (typeof window === "undefined") return "http://localhost:8000";
  return `${window.location.protocol}//${window.location.hostname}:8000`;
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json();
    return body.detail || "The request could not be completed.";
  } catch {
    return "The request could not be completed.";
  }
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function request<T>(
  path: string,
  token: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${apiBase()}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(init?.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
      ...init?.headers,
    },
  });
  if (!response.ok)
    throw new ApiError(await errorMessage(response), response.status);
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function developmentToken(
  organizationId: string,
  email: string,
): Promise<string> {
  const response = await fetch(`${apiBase()}/api/v1/auth/development-token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ organization_id: organizationId, email }),
  });
  if (!response.ok) throw new Error(await errorMessage(response));
  const body = await response.json();
  return body.access_token;
}

export type CognitoSession = { idToken: string; accessToken: string };
export type CognitoLoginResult =
  CognitoSession | { challenge: "SOFTWARE_TOKEN_MFA"; session: string };

async function cognitoCall(target: string, payload: Record<string, unknown>) {
  const region = process.env.NEXT_PUBLIC_COGNITO_REGION;
  if (!region) throw new Error("Cognito region is missing.");
  const response = await fetch(`https://cognito-idp.${region}.amazonaws.com/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-amz-json-1.1",
      "X-Amz-Target": `AWSCognitoIdentityProviderService.${target}`,
    },
    body: JSON.stringify(payload),
  });
  const body = await response.json();
  if (!response.ok) throw new Error(body.message || "Cognito request failed.");
  return body;
}

export async function cognitoPasswordToken(
  email: string,
  password: string,
): Promise<CognitoLoginResult> {
  const region = process.env.NEXT_PUBLIC_COGNITO_REGION;
  const clientId = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID;
  if (!region || !clientId)
    throw new Error("Cognito frontend settings are missing.");
  const body = await cognitoCall("InitiateAuth", {
    AuthFlow: "USER_PASSWORD_AUTH",
    ClientId: clientId,
    AuthParameters: { USERNAME: email, PASSWORD: password },
  });
  if (body.ChallengeName === "SOFTWARE_TOKEN_MFA" && body.Session)
    return { challenge: "SOFTWARE_TOKEN_MFA", session: body.Session };
  if (body.ChallengeName)
    throw new Error(
      `Cognito requires ${body.ChallengeName}. Complete account setup before signing in.`,
    );
  const idToken = body.AuthenticationResult?.IdToken;
  const accessToken = body.AuthenticationResult?.AccessToken;
  if (!idToken || !accessToken)
    throw new Error("Cognito did not return a complete session.");
  return { idToken, accessToken };
}

export async function cognitoSignUp(
  email: string,
  password: string,
  displayName: string,
): Promise<void> {
  const clientId = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID;
  if (!clientId) throw new Error("Cognito client ID is missing.");
  await cognitoCall("SignUp", {
    ClientId: clientId,
    Username: email,
    Password: password,
    UserAttributes: [
      { Name: "email", Value: email },
      { Name: "name", Value: displayName },
    ],
  });
}

export async function cognitoConfirmSignUp(
  email: string,
  confirmationCode: string,
): Promise<void> {
  const clientId = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID;
  if (!clientId) throw new Error("Cognito client ID is missing.");
  await cognitoCall("ConfirmSignUp", {
    ClientId: clientId,
    Username: email,
    ConfirmationCode: confirmationCode,
  });
}

export async function cognitoMfaToken(
  email: string,
  code: string,
  session: string,
): Promise<CognitoSession> {
  const clientId = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID;
  if (!clientId) throw new Error("Cognito client ID is missing.");
  const body = await cognitoCall("RespondToAuthChallenge", {
    ChallengeName: "SOFTWARE_TOKEN_MFA",
    ClientId: clientId,
    Session: session,
    ChallengeResponses: { USERNAME: email, SOFTWARE_TOKEN_MFA_CODE: code },
  });
  const idToken = body.AuthenticationResult?.IdToken;
  const accessToken = body.AuthenticationResult?.AccessToken;
  if (!idToken || !accessToken)
    throw new Error("Cognito did not return a complete session.");
  return { idToken, accessToken };
}

export async function beginTotpEnrollment(
  accessToken: string,
): Promise<string> {
  const body = await cognitoCall("AssociateSoftwareToken", {
    AccessToken: accessToken,
  });
  if (!body.SecretCode)
    throw new Error("Cognito did not return an authenticator secret.");
  return body.SecretCode;
}

export async function confirmTotpEnrollment(
  accessToken: string,
  code: string,
): Promise<void> {
  await cognitoCall("VerifySoftwareToken", {
    AccessToken: accessToken,
    UserCode: code,
    FriendlyDeviceName: "GroundsOps authenticator",
  });
  await cognitoCall("SetUserMFAPreference", {
    AccessToken: accessToken,
    SoftwareTokenMfaSettings: { Enabled: true, PreferredMfa: true },
  });
}

export async function captureBlob(
  captureId: string,
  token: string,
): Promise<Blob> {
  const response = await fetch(
    `${apiBase()}/api/v1/captures/${captureId}/content`,
    {
      headers: { Authorization: `Bearer ${token}` },
    },
  );
  if (!response.ok) throw new Error(await errorMessage(response));
  return response.blob();
}

export async function organizationLogoBlob(token: string): Promise<Blob> {
  const response = await fetch(
    `${apiBase()}/api/v1/organization/logo/content`,
    {
      headers: { Authorization: `Bearer ${token}` },
    },
  );
  if (!response.ok) throw new Error(await errorMessage(response));
  return response.blob();
}

export async function invoiceLogoBlob(token: string): Promise<Blob> {
  const response = await fetch(
    `${apiBase()}/api/v1/organization/invoice-logo/content`,
    {
      headers: { Authorization: `Bearer ${token}` },
    },
  );
  if (!response.ok) throw new Error(await errorMessage(response));
  return response.blob();
}

