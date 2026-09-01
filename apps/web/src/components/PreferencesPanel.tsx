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
import { actorForRole, type TenantSession } from "../data/session";
import { useLocale } from "../i18n";

interface PreferencesPanelProps {
  role: Role;
  source: DataSourceMode;
  availability: DataAvailability;
  session: TenantSession | null;
}

export function PreferencesPanel({ role, source, availability, session }: PreferencesPanelProps) {
  const { locale, t } = useLocale();
  const [open, setOpen] = useState(false);
  const [namespace, setNamespace] = useState<PreferenceNamespace>("accessibility");
  const [state, setState] = useState<PreferenceState>(() =>
    createPreferenceState("accessibility", source === "live" ? "live" : "other"),
  );
  const [requestSequence, setRequestSequence] = useState(0);
  const actor = session?.roles.includes(role) ? actorForRole(session, role) : role;
  const readOnly = source !== "live" || availability !== "ready" || !session;

  const refresh = async (target = namespace) => {
    setState((current) => ({
      ...current,
      status: "loading",
      detail: t("role.preferencesLoading"),
    }));
    if (source !== "live") {
      setState(createPreferenceState(target, "other"));
      return;
    }
    if (!session || !session.roles.includes(role)) {
      setState({
        ...createPreferenceState(target),
        status: "unavailable",
        detail: t("role.preferencesIdentityRequired"),
      });
      return;
    }
    setState((await loadPreference(target, session, role)).state);
  };

  useEffect(() => {
    if (!open) return;
    void refresh();
    // A focused workspace may have changed in another tab; reload marks stale before replacing data.
    const markStale = () =>
      setState((current) =>
        current.status === "ready"
          ? { ...current, status: "stale", detail: t("role.preferencesChangedElsewhere") }
          : current,
      );
    window.addEventListener("focus", markStale);
    return () => window.removeEventListener("focus", markStale);
  }, [open, namespace, source, actor, role, session]);

  const update = (field: string, value: string | boolean | number) =>
    setState((current) => ({
      ...current,
      draft: { ...current.draft, [field]: value },
      status: current.status === "stale" ? "stale" : "ready",
      detail: t("role.preferencesUnsaved"),
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
    setState((current) => ({
      ...current,
      status: "loading",
      detail: t("role.preferencesLoading"),
    }));
    if (!session) return;
    setState(
      (await savePreference({ ...state, status: "ready" }, session, role, idempotencyKey)).state,
    );
    setRequestSequence((sequence) => sequence + 1);
  };

  return (
    <>
      <button
        className="icon-button"
        type="button"
        title={t("role.openPreferences")}
        aria-label={t("role.openPreferences")}
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
                <p className="eyebrow">
                  {locale === "zh-CN" ? "RouteMind 工作区" : `${actor} workspace`}
                </p>
                <h2 id="preferences-title">
                  {locale === "zh-CN" ? "持久化偏好" : "Durable preferences"}
                </h2>
              </div>
              <button
                className="icon-button"
                type="button"
                title={t("role.closePreferences")}
                aria-label={t("role.closePreferences")}
                onClick={() => setOpen(false)}
              >
                <X size={17} />
              </button>
            </div>
            <label className="preference-field">
              <span>{t("role.preferenceArea")}</span>
              <select
                aria-label={t("role.preferenceArea")}
                value={namespace}
                onChange={(event) => {
                  const next = event.target.value as PreferenceNamespace;
                  setNamespace(next);
                  setState(createPreferenceState(next, source === "live" ? "live" : "other"));
                }}
              >
                {preferenceNamespaces.map((item) => (
                  <option value={item} key={item}>
                    {item === "accessibility"
                      ? t("role.preferenceAccessibility")
                      : item === "locale"
                        ? t("role.preferenceLocale")
                        : item === "notifications"
                          ? t("role.preferenceNotifications")
                          : t("role.preferenceQuietHours")}
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
                  ? t("role.statusCurrent")
                  : state.status === "stale"
                    ? t("role.statusStale")
                    : state.status === "conflict"
                      ? t("role.statusConflict")
                      : state.status === "rollback"
                        ? t("role.statusRolledBack")
                        : state.status === "loading"
                          ? t("role.statusLoading")
                          : t("role.unavailable")}
              </strong>
              <span>{state.detail}</span>
            </div>
            {namespace === "locale" && (
              <>
                <label className="preference-field">
                  <span>{t("role.locale")}</span>
                  <input
                    value={String(state.draft.locale ?? "")}
                    onChange={(event) => update("locale", event.target.value)}
                  />
                </label>
                <label className="preference-field">
                  <span>{t("role.timeZone")}</span>
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
                  <span>{t("role.enableQuietHours")}</span>
                </label>
                <label className="preference-field">
                  <span>{t("role.startLocal")}</span>
                  <input
                    type="time"
                    value={String(state.draft.startLocal ?? "22:00")}
                    onChange={(event) => update("startLocal", event.target.value)}
                  />
                </label>
                <label className="preference-field">
                  <span>{t("role.endLocal")}</span>
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
                  <span>{t("role.theme")}</span>
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
                  <span>{t("role.visibleFocus")}</span>
                </label>
                <label className="preference-checkbox">
                  <input
                    type="checkbox"
                    checked={Boolean(state.draft.colorOnlyStatus)}
                    onChange={(event) => update("colorOnlyStatus", event.target.checked)}
                  />
                  <span>{t("role.allowColorOnlyStatus")}</span>
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
                <RotateCcw size={15} /> {t("role.refresh")}
              </button>
              <button
                className="button button-primary"
                type="button"
                onClick={() => void save()}
                disabled={!canSave}
              >
                <Check size={15} /> {t("role.save")}
              </button>
            </div>
            {readOnly && <p className="command-note">{t("role.preferenceWriteDisabled")}</p>}
          </section>
        </div>
      )}
    </>
  );
}
