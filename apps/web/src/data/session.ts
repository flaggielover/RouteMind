import { roles, type Role } from "../domain/model";

export interface TenantSession {
  tenantId: string;
  subject: string;
  roles: readonly Role[];
  accessToken: string;
  expiresAt: string;
}

export interface TenantSessionResult {
  ok: boolean;
  session: TenantSession | null;
  detail: string;
}

export type AccessTokenProvider = () => Promise<string | null>;
export type TenantSessionProvider = () => Promise<TenantSessionResult>;

declare global {
  interface Window {
    __ROUTEMIND_OIDC_ACCESS_TOKEN__?: AccessTokenProvider;
  }
}

interface SessionResponse {
  schemaVersion?: unknown;
  subject?: unknown;
  tenantId?: unknown;
  roles?: unknown;
  expiresAt?: unknown;
}

const businessApi = import.meta.env.VITE_BUSINESS_API_URL ?? "http://localhost:18080";
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const nilTenant = "00000000-0000-0000-0000-000000000000";
const surfaceRoleByAuthority: Record<string, Role> = {
  operator: "operations",
  analyst: "strategy",
  customer: "customer",
  merchant: "merchant",
  courier: "courier",
};
const authorityBySurfaceRole: Record<Role, string> = {
  operations: "operator",
  strategy: "analyst",
  customer: "customer",
  merchant: "merchant",
  courier: "courier",
};

function unavailable(detail: string): TenantSessionResult {
  return { ok: false, session: null, detail };
}

export function actorForRole(session: TenantSession, role: Role): string {
  if (!session.roles.includes(role)) throw new Error(`role ${role} is not authorized`);
  return authorityBySurfaceRole[role];
}

export function authorizedHeaders(session: TenantSession, role?: Role): Record<string, string> {
  return {
    Authorization: `Bearer ${session.accessToken}`,
    ...(role ? { "X-Actor": actorForRole(session, role) } : {}),
  };
}

export function sessionScope(session: TenantSession): string {
  return `${session.tenantId}:${session.subject}:${[...session.roles].sort().join(",")}`;
}

export function parseTenantSession(
  body: SessionResponse,
  accessToken: string,
): TenantSessionResult {
  if (
    body.schemaVersion !== "v1" ||
    typeof body.subject !== "string" ||
    body.subject.trim().length === 0 ||
    body.subject.length > 200 ||
    typeof body.tenantId !== "string" ||
    !uuid.test(body.tenantId) ||
    body.tenantId === nilTenant ||
    !Array.isArray(body.roles) ||
    typeof body.expiresAt !== "string"
  ) {
    return unavailable("Verified session response is invalid");
  }
  const expiresAt = new Date(body.expiresAt);
  if (Number.isNaN(expiresAt.getTime()) || expiresAt.getTime() <= Date.now()) {
    return unavailable("Verified session has expired");
  }
  const mappedRoles = body.roles
    .filter((value): value is string => typeof value === "string")
    .map((value) => surfaceRoleByAuthority[value.toLowerCase()])
    .filter((value): value is Role => Boolean(value));
  const uniqueRoles = roles.filter((role) => mappedRoles.includes(role));
  if (uniqueRoles.length === 0) return unavailable("Verified session has no RouteMind role");
  return {
    ok: true,
    session: {
      tenantId: body.tenantId.toLowerCase(),
      subject: body.subject.trim(),
      roles: uniqueRoles,
      accessToken,
      expiresAt: body.expiresAt,
    },
    detail: "Verified tenant session is active",
  };
}

export async function loadBrowserTenantSession(
  fetchImpl: typeof fetch = fetch,
  tokenProvider: AccessTokenProvider | undefined = window.__ROUTEMIND_OIDC_ACCESS_TOKEN__,
): Promise<TenantSessionResult> {
  if (!tokenProvider) return unavailable("OIDC session provider is unavailable");
  try {
    const accessToken = await tokenProvider();
    if (!accessToken || accessToken.trim().length === 0) {
      return unavailable("OIDC access token is unavailable");
    }
    const response = await fetchImpl(`${businessApi}/api/v1/session`, {
      headers: { Accept: "application/json", Authorization: `Bearer ${accessToken}` },
    });
    if (!response.ok) return unavailable(`Session verification failed (HTTP ${response.status})`);
    return parseTenantSession((await response.json()) as SessionResponse, accessToken);
  } catch {
    return unavailable("Session verification is unavailable");
  }
}
