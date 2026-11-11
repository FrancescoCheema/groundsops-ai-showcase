import { developmentToken } from "@/lib/api";

export type DemoWorkspaceAccess = {
  organizationId: string;
  email: string;
  token: string;
};

export function demoWorkspaceAvailable() {
  return Boolean(
    process.env.NEXT_PUBLIC_DEMO_ORGANIZATION_ID &&
      process.env.NEXT_PUBLIC_DEMO_EMAIL,
  );
}

export async function createDemoWorkspaceAccess(): Promise<DemoWorkspaceAccess> {
  const organizationId = process.env.NEXT_PUBLIC_DEMO_ORGANIZATION_ID;
  const email = process.env.NEXT_PUBLIC_DEMO_EMAIL;
  if (!organizationId || !email) {
    throw new Error("The demo workspace is not configured.");
  }
  return {
    organizationId,
    email,
    token: await developmentToken(organizationId, email),
  };
}
