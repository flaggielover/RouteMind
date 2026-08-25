import { describe, expect, it, vi } from "vitest";
import {
  actorForRole,
  authorizedHeaders,
  loadBrowserTenantSession,
  parseTenantSession,
  type TenantSession,
} from "./session";

const expiresAt = "2099-08-25T10:00:00Z";

describe("verified tenant session boundary", () => {
  it("maps only recognized server-verified authorities to product surfaces", () => {
    const result = parseTenantSession(
      {
        schemaVersion: "v1",
        subject: "user-42",
        tenantId: "10000000-0000-0000-0000-000000000001",
        roles: ["customer", "unknown", "operator"],
        expiresAt,
      },
      "access-token",
    );

    expect(result.ok).toBe(true);
    expect(result.session?.tenantId).toBe("10000000-0000-0000-0000-000000000001");
    expect(result.session?.roles).toEqual(["operations", "customer"]);
    expect(result.session?.accessToken).toBe("access-token");
  });

  it("fails closed for invalid tenants, expired sessions, and unknown roles", () => {
    expect(
      parseTenantSession(
        {
          schemaVersion: "v1",
          subject: "user-42",
          tenantId: "00000000-0000-0000-0000-000000000000",
          roles: ["customer"],
          expiresAt,
        },
        "token",
      ).ok,
    ).toBe(false);
    expect(
      parseTenantSession(
        {
          schemaVersion: "v1",
          subject: "user-42",
          tenantId: "10000000-0000-4000-8000-000000000001",
          roles: ["administrator"],
          expiresAt,
        },
        "token",
      ).ok,
    ).toBe(false);
    expect(
      parseTenantSession(
        {
          schemaVersion: "v1",
          subject: "user-42",
          tenantId: "10000000-0000-4000-8000-000000000001",
          roles: ["customer"],
          expiresAt: "2020-01-01T00:00:00Z",
        },
        "token",
      ).detail,
    ).toContain("expired");
  });

  it("verifies the token with Java and never puts it in a URL", async () => {
    const fetchImpl = vi.fn(async (_input: string | URL | Request, init?: RequestInit) => {
      expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer access-token");
      return new Response(
        JSON.stringify({
          schemaVersion: "v1",
          subject: "courier-7",
          tenantId: "10000000-0000-4000-8000-000000000001",
          roles: ["courier"],
          expiresAt,
        }),
        { status: 200 },
      );
    });
    const result = await loadBrowserTenantSession(fetchImpl, async () => "access-token");

    expect(result.ok).toBe(true);
    expect(String(fetchImpl.mock.calls[0][0])).not.toContain("access-token");
  });

  it("binds actor headers to an authorized session role", () => {
    const session: TenantSession = {
      tenantId: "10000000-0000-4000-8000-000000000001",
      subject: "courier-7",
      roles: ["courier"],
      accessToken: "access-token",
      expiresAt,
    };
    expect(actorForRole(session, "courier")).toBe("courier");
    expect(authorizedHeaders(session, "courier")).toEqual({
      Authorization: "Bearer access-token",
      "X-Actor": "courier",
    });
    expect(() => authorizedHeaders(session, "customer")).toThrow("not authorized");
  });
});
