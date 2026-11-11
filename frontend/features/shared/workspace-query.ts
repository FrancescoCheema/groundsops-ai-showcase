import {
  ApiError,
  Customer,
  CurrentUser,
  Design,
  GenerationMetrics,
  Invoice,
  Organization,
  OrganizationUser,
  PlatformOrganization,
  PlatformUser,
  Property,
  Timesheet,
  VaultFile,
  WorkOrder,
  request,
} from "@/lib/api";

async function optionalRequest<T>(path: string, token: string, fallback: T): Promise<T> {
  try {
    return await request<T>(path, token);
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) throw error;
    console.warn(`Optional workspace request failed: ${path}`, error);
    return fallback;
  }
}

export type WorkspaceSnapshot = {
  currentUser: CurrentUser;
  organization: Organization;
  customers: Customer[];
  properties: Property[];
  designs: Design[];
  invoices: Invoice[];
  timesheets: Timesheet[];
  workOrders: WorkOrder[];
  users: OrganizationUser[];
  generationMetrics?: GenerationMetrics;
  platformOrganizations: PlatformOrganization[];
  platformUsers: PlatformUser[];
  vaultFiles: VaultFile[];
};

export async function loadWorkspaceSnapshot(token: string): Promise<WorkspaceSnapshot> {
  const [currentUser, organization] = await Promise.all([
    request<CurrentUser>("/api/v1/auth/me", token),
    request<Organization>("/api/v1/organization", token),
  ]);
  const manager = currentUser.role === "admin" || currentUser.role === "manager";
  const designer = manager || currentUser.role === "designer";
  const [properties, timesheets, workOrders, vaultFiles, customers, designs, invoices, generationMetrics, users] = await Promise.all([
    optionalRequest<Property[]>("/api/v1/properties", token, []),
    optionalRequest<Timesheet[]>("/api/v1/timesheets", token, []),
    optionalRequest<WorkOrder[]>("/api/v1/work-orders", token, []),
    optionalRequest<VaultFile[]>("/api/v1/vault/files", token, []),
    manager ? optionalRequest<Customer[]>("/api/v1/customers", token, []) : Promise.resolve([]),
    designer ? optionalRequest<Design[]>("/api/v1/design-projects", token, []) : Promise.resolve([]),
    manager ? optionalRequest<Invoice[]>("/api/v1/invoices", token, []) : Promise.resolve([]),
    manager ? optionalRequest<GenerationMetrics | undefined>("/api/v1/generation-metrics", token, undefined) : Promise.resolve(undefined),
    manager ? optionalRequest<OrganizationUser[]>(currentUser.role === "admin" ? "/api/v1/users?include_inactive=true" : "/api/v1/users", token, []) : Promise.resolve([]),
  ]);
  const [platformOrganizations, platformUsers] = currentUser.platform_admin
    ? await Promise.all([
        optionalRequest<PlatformOrganization[]>("/api/v1/platform/organizations", token, []),
        optionalRequest<PlatformUser[]>("/api/v1/platform/users", token, []),
      ])
    : [[], []];
  return { currentUser, organization, customers, properties, designs, invoices, timesheets, workOrders, users, generationMetrics, platformOrganizations, platformUsers, vaultFiles };
}
