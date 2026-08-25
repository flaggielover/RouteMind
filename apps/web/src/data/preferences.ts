import type { Role } from "../domain/model";
import { authorizedHeaders, type TenantSession } from "./session";

export const preferenceNamespaces = [
  "accessibility",
  "locale",
  "notifications",
  "quiet_hours",
] as const;
export type PreferenceNamespace = (typeof preferenceNamespaces)[number];
export type PreferenceStatus =
  "loading" | "ready" | "stale" | "conflict" | "unavailable" | "rollback";
export type PreferenceValues = Record<string, boolean | number | string>;

export interface PreferenceSnapshot {
  namespace: PreferenceNamespace;
  values: PreferenceValues;
  version: number;
  persisted: boolean;
  replayed: boolean;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface PreferenceState {
  status: PreferenceStatus;
  snapshot: PreferenceSnapshot;
  draft: PreferenceValues;
  detail: string;
  traceId: string | null;
}

export interface PreferenceResult {
  ok: boolean;
  state: PreferenceState;
}

const businessApi = import.meta.env.VITE_BUSINESS_API_URL ?? "http://localhost:18080";
const timeoutMs = 2_000;

export const preferenceDefaults: Record<PreferenceNamespace, PreferenceValues> = {
  accessibility: {
    theme: "system",
    contrast: "system",
    reducedMotion: "system",
    textScale: 1,
    screenReaderAnnouncements: "polite",
    visibleFocus: true,
    colorOnlyStatus: false,
  },
  locale: { locale: "en-US", timeZone: "UTC" },
  notifications: { in_app: true, email: false, sms: false, push: false },
  quiet_hours: { enabled: false, startLocal: "22:00", endLocal: "07:00" },
};

function emptyState(
  namespace: PreferenceNamespace,
  status: PreferenceStatus,
  detail: string,
): PreferenceState {
  const values = { ...preferenceDefaults[namespace] };
  return {
    status,
    snapshot: {
      namespace,
      values,
      version: 0,
      persisted: false,
      replayed: false,
      createdAt: null,
      updatedAt: null,
    },
    draft: values,
    detail,
    traceId: null,
  };
}

export function createPreferenceState(
  namespace: PreferenceNamespace,
  source: "live" | "other" = "live",
): PreferenceState {
  return source === "live"
    ? emptyState(namespace, "loading", "Loading durable preferences")
    : emptyState(
        namespace,
        "unavailable",
        "Preferences are unavailable for demo and replay sources",
      );
}

function traceId(response: Response, body: { traceId?: unknown }): string | null {
  const header = response.headers.get("X-Trace-Id");
  return header ?? (typeof body.traceId === "string" ? body.traceId : null);
}

function parseSnapshot(namespace: PreferenceNamespace, body: unknown): PreferenceSnapshot | null {
  if (!body || typeof body !== "object") return null;
  const candidate = body as Partial<PreferenceSnapshot>;
  if (
    candidate.namespace !== namespace ||
    typeof candidate.values !== "object" ||
    candidate.values === null ||
    typeof candidate.version !== "number"
  )
    return null;
  return {
    namespace,
    values: { ...(candidate.values as PreferenceValues) },
    version: candidate.version,
    persisted: candidate.persisted === true,
    replayed: candidate.replayed === true,
    createdAt: typeof candidate.createdAt === "string" ? candidate.createdAt : null,
    updatedAt: typeof candidate.updatedAt === "string" ? candidate.updatedAt : null,
  };
}

export async function loadPreference(
  namespace: PreferenceNamespace,
  session: TenantSession,
  role: Role,
  fetchImpl: typeof fetch = fetch,
): Promise<PreferenceResult> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetchImpl(`${businessApi}/api/v1/preferences/${namespace}`, {
      headers: { Accept: "application/json", ...authorizedHeaders(session, role) },
      signal: controller.signal,
    });
    const body = (await response.json().catch(() => ({}))) as { traceId?: unknown };
    const snapshot = parseSnapshot(namespace, body);
    if (response.ok && snapshot) {
      return {
        ok: true,
        state: {
          status: "ready",
          snapshot,
          draft: { ...snapshot.values },
          detail: "Preferences are current",
          traceId: traceId(response, body),
        },
      };
    }
    return {
      ok: false,
      state: {
        ...createPreferenceState(namespace),
        status: response.status === 409 ? "conflict" : "unavailable",
        detail:
          response.status === 409
            ? "Preference version is stale"
            : `Preference service unavailable (HTTP ${response.status})`,
        traceId: traceId(response, body),
      },
    };
  } catch (error) {
    const detail =
      error instanceof DOMException && error.name === "AbortError"
        ? "Preference request timed out"
        : "Preference service unavailable";
    return {
      ok: false,
      state: { ...createPreferenceState(namespace), status: "unavailable", detail, traceId: null },
    };
  } finally {
    clearTimeout(timeout);
  }
}

export async function savePreference(
  state: PreferenceState,
  session: TenantSession,
  role: Role,
  idempotencyKey: string,
  fetchImpl: typeof fetch = fetch,
): Promise<PreferenceResult> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetchImpl(
      `${businessApi}/api/v1/preferences/${state.snapshot.namespace}`,
      {
        method: "PUT",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          "Idempotency-Key": idempotencyKey,
          ...authorizedHeaders(session, role),
        },
        body: JSON.stringify({ expectedVersion: state.snapshot.version, values: state.draft }),
        signal: controller.signal,
      },
    );
    const body = (await response.json().catch(() => ({}))) as { traceId?: unknown };
    const snapshot = parseSnapshot(state.snapshot.namespace, body);
    if (response.ok && snapshot) {
      return {
        ok: true,
        state: {
          status: "ready",
          snapshot,
          draft: { ...snapshot.values },
          detail: snapshot.replayed ? "Saved change replayed safely" : "Preferences saved",
          traceId: traceId(response, body),
        },
      };
    }
    const conflict = response.status === 409;
    return {
      ok: false,
      state: {
        ...state,
        status: conflict ? "conflict" : "rollback",
        draft: { ...state.draft },
        detail: conflict
          ? "Another session changed this preference; refresh before saving"
          : `Save rolled back; service returned HTTP ${response.status}`,
        traceId: traceId(response, body),
      },
    };
  } catch (error) {
    const detail =
      error instanceof DOMException && error.name === "AbortError"
        ? "Save timed out; local draft retained"
        : "Save unavailable; local draft retained";
    return {
      ok: false,
      state: { ...state, status: "rollback", draft: { ...state.draft }, detail, traceId: null },
    };
  } finally {
    clearTimeout(timeout);
  }
}
