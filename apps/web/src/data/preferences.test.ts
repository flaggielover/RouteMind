import { describe, expect, it } from "vitest";
import { createPreferenceState, loadPreference, savePreference } from "./preferences";

function response(body: unknown, status: number, traceId = "trace-preference-1"): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", "X-Trace-Id": traceId },
  });
}

describe("durable preference boundary", () => {
  it("starts loading with explicit defaults and marks non-live sources unavailable", () => {
    expect(createPreferenceState("locale").status).toBe("loading");
    expect(createPreferenceState("locale", "other").status).toBe("unavailable");
    expect(createPreferenceState("locale").snapshot.version).toBe(0);
  });

  it("loads a persisted snapshot and sends only the selected actor scope", async () => {
    let request: RequestInit | undefined;
    const result = await loadPreference("locale", "customer", async (_url, init) => {
      request = init;
      return response(
        {
          namespace: "locale",
          values: { locale: "zh-CN", timeZone: "Asia/Shanghai" },
          version: 2,
          persisted: true,
          replayed: false,
        },
        200,
      );
    });
    expect(result.ok).toBe(true);
    expect(result.state.snapshot.version).toBe(2);
    expect(new Headers(request?.headers).get("X-Actor")).toBe("customer");
  });

  it("keeps a draft on conflict and classifies service failure as rollback", async () => {
    const state = {
      ...createPreferenceState("notifications"),
      status: "ready" as const,
      draft: { ...createPreferenceState("notifications").draft, email: true },
    };
    const conflict = await savePreference(state, "customer", "preference-key-1", async () =>
      response({ code: "preference_version_conflict" }, 409),
    );
    expect(conflict.ok).toBe(false);
    expect(conflict.state.status).toBe("conflict");
    expect(conflict.state.draft.email).toBe(true);
    const rollback = await savePreference(state, "customer", "preference-key-2", async () => {
      throw new Error("offline");
    });
    expect(rollback.state.status).toBe("rollback");
    expect(rollback.state.detail).toContain("draft retained");
  });
});
