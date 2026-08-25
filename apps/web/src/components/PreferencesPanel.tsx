import { Check, RotateCcw, Settings2, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  createPreferenceState,
  loadPreference,
  preferenceNamespaces,
  savePreference,
  type PreferenceNamespace,
  type PreferenceState,
} from "../data/preferences";
import type { DataAvailability, DataSourceMode, Role } from "../domain/model";

interface PreferencesPanelProps {
  role: Role;
  source: DataSourceMode;
  availability: DataAvailability;
}

const actorByRole: Record<Role, string> = {
  operations: "operator",
  strategy: "analyst",
  customer: "customer",
  merchant: "merchant",
  courier: "courier",
};

const labels: Record<PreferenceNamespace, string> = {
  accessibility: "Accessibility",
  locale: "Locale",
  notifications: "Notifications",
  quiet_hours: "Quiet hours",
};

export function PreferencesPanel({ role, source, availability }: PreferencesPanelProps) {
  const [open, setOpen] = useState(false);
  const [namespace, setNamespace] = useState<PreferenceNamespace>("accessibility");
  const [state, setState] = useState<PreferenceState>(() =>
    createPreferenceState("accessibility", source === "live" ? "live" : "other"),
  );
  const [requestSequence, setRequestSequence] = useState(0);
  const actor = actorByRole[role];
  const readOnly = source !== "live" || availability !== "ready";

  const refresh = async (target = namespace) => {
    setState((current) => ({
      ...current,
      status: "loading",
      detail: "Loading durable preferences",
    }));
    if (source !== "live") {
      setState(createPreferenceState(target, "other"));
      return;
    }
    setState((await loadPreference(target, actor)).state);
  };

  useEffect(() => {
    if (!open) return;
    void refresh();
    // A focused workspace may have changed in another tab; reload marks stale before replacing data.
    const markStale = () =>
      setState((current) =>
        current.status === "ready"
          ? { ...current, status: "stale", detail: "Preferences may have changed elsewhere" }
          : current,
      );
    window.addEventListener("focus", markStale);
    return () => window.removeEventListener("focus", markStale);
  }, [open, namespace, source, actor]);

  const update = (field: string, value: string | boolean | number) =>
    setState((current) => ({
      ...current,
      draft: { ...current.draft, [field]: value },
      status: current.status === "stale" ? "stale" : "ready",
      detail: "Unsaved changes",
    }));
  const canSave =
    !readOnly &&
    state.status !== "loading" &&
    state.status !== "conflict" &&
    state.status !== "unavailable" &&
    state.status !== "rollback";
  const idempotencyKey = useMemo(
    () => `web-preference-${actor}-${namespace}-${requestSequence}`,
    [actor, namespace, requestSequence],
  );
  const save = async () => {
    if (!canSave) return;
    setState((current) => ({ ...current, status: "loading", detail: "Saving durable preference" }));
    setState((await savePreference({ ...state, status: "ready" }, actor, idempotencyKey)).state);
    setRequestSequence((sequence) => sequence + 1);
  };

  return (
    <>
      <button
        className="icon-button"
        type="button"
        title="Open durable preferences"
        aria-label="Open durable preferences"
        onClick={() => setOpen(true)}
      >
        <Settings2 size={17} />
      </button>
      {open && (
        <div
          className="preferences-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setOpen(false);
          }}
        >
          <section
            className="preferences-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="preferences-title"
          >
            <div className="panel-heading">
              <div>
                <p className="eyebrow">{actor} workspace</p>
                <h2 id="preferences-title">Durable preferences</h2>
              </div>
              <button
                className="icon-button"
                type="button"
                title="Close preferences"
                aria-label="Close preferences"
                onClick={() => setOpen(false)}
              >
                <X size={17} />
              </button>
            </div>
            <label className="preference-field">
              <span>Preference area</span>
              <select
                aria-label="Preference area"
                value={namespace}
                onChange={(event) => {
                  const next = event.target.value as PreferenceNamespace;
                  setNamespace(next);
                  setState(createPreferenceState(next, source === "live" ? "live" : "other"));
                }}
              >
                {preferenceNamespaces.map((item) => (
                  <option value={item} key={item}>
                    {labels[item]}
                  </option>
                ))}
              </select>
            </label>
            <div
              className={`preference-status preference-status-${state.status}`}
              role={state.status === "conflict" || state.status === "rollback" ? "alert" : "status"}
            >
              <strong>
                {state.status === "ready"
                  ? "Current"
                  : state.status === "stale"
                    ? "Stale"
                    : state.status === "conflict"
                      ? "Conflict"
                      : state.status === "rollback"
                        ? "Rolled back"
                        : state.status === "loading"
                          ? "Loading"
                          : "Unavailable"}
              </strong>
              <span>{state.detail}</span>
            </div>
            {namespace === "locale" && (
              <>
                <label className="preference-field">
                  <span>Locale</span>
                  <input
                    value={String(state.draft.locale ?? "")}
                    onChange={(event) => update("locale", event.target.value)}
                  />
                </label>
                <label className="preference-field">
                  <span>Time zone</span>
                  <input
                    value={String(state.draft.timeZone ?? "")}
                    onChange={(event) => update("timeZone", event.target.value)}
                  />
                </label>
              </>
            )}
            {namespace === "quiet_hours" && (
              <>
                <label className="preference-checkbox">
                  <input
                    type="checkbox"
                    checked={Boolean(state.draft.enabled)}
                    onChange={(event) => update("enabled", event.target.checked)}
                  />
                  <span>Enable quiet hours</span>
                </label>
                <label className="preference-field">
                  <span>Start local</span>
                  <input
                    type="time"
                    value={String(state.draft.startLocal ?? "22:00")}
                    onChange={(event) => update("startLocal", event.target.value)}
                  />
                </label>
                <label className="preference-field">
                  <span>End local</span>
                  <input
                    type="time"
                    value={String(state.draft.endLocal ?? "07:00")}
                    onChange={(event) => update("endLocal", event.target.value)}
                  />
                </label>
              </>
            )}
            {namespace === "notifications" && (
              <div className="preference-checkboxes">
                {["in_app", "email", "sms", "push"].map((channel) => (
                  <label className="preference-checkbox" key={channel}>
                    <input
                      type="checkbox"
                      checked={Boolean(state.draft[channel])}
                      onChange={(event) => update(channel, event.target.checked)}
                    />
                    <span>{channel.replace("_", " ")}</span>
                  </label>
                ))}
              </div>
            )}
            {namespace === "accessibility" && (
              <>
                <label className="preference-field">
                  <span>Theme</span>
                  <select
                    value={String(state.draft.theme ?? "system")}
                    onChange={(event) => update("theme", event.target.value)}
                  >
                    <option>system</option>
                    <option>light</option>
                    <option>dark</option>
                  </select>
                </label>
                <label className="preference-checkbox">
                  <input
                    type="checkbox"
                    checked={Boolean(state.draft.visibleFocus)}
                    onChange={(event) => update("visibleFocus", event.target.checked)}
                  />
                  <span>Visible focus</span>
                </label>
                <label className="preference-checkbox">
                  <input
                    type="checkbox"
                    checked={Boolean(state.draft.colorOnlyStatus)}
                    onChange={(event) => update("colorOnlyStatus", event.target.checked)}
                  />
                  <span>Allow color-only status</span>
                </label>
              </>
            )}
            <p className="preference-version">
              Version {state.snapshot.version} ·{" "}
              {state.snapshot.persisted ? "Java/PostgreSQL" : "default"}
            </p>
            <div className="preference-actions">
              <button
                className="button button-secondary"
                type="button"
                onClick={() => void refresh()}
                disabled={state.status === "loading"}
              >
                <RotateCcw size={15} /> Refresh
              </button>
              <button
                className="button button-primary"
                type="button"
                onClick={() => void save()}
                disabled={!canSave}
              >
                <Check size={15} /> Save
              </button>
            </div>
            {readOnly && (
              <p className="command-note">
                Writing is disabled for demo, replay, or degraded sources.
              </p>
            )}
          </section>
        </div>
      )}
    </>
  );
}
