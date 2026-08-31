import {
  Activity,
  Bike,
  ChevronRight,
  ClipboardList,
  FlaskConical,
  LayoutDashboard,
  Menu,
  Store,
  UserRound,
} from "lucide-react";
import { NavLink, useLocation } from "react-router-dom";
import { useEffect, useRef, useState, type ReactNode } from "react";
import type { DataAvailability, DataSourceMode, Role, ServiceHealth } from "../domain/model";
import type { RealtimeConnectionState } from "../data/realtime";
import type { TenantSession } from "../data/session";
import { StatusPill } from "./StatusPill";
import { PreferencesPanel } from "./PreferencesPanel";
import { useLocale } from "../i18n";

const navigation: Array<{ role: Role; labelKey: string; icon: typeof LayoutDashboard }> = [
  { role: "operations", labelKey: "nav.operations", icon: LayoutDashboard },
  { role: "strategy", labelKey: "nav.strategy", icon: FlaskConical },
  { role: "customer", labelKey: "nav.customer", icon: UserRound },
  { role: "merchant", labelKey: "nav.merchant", icon: Store },
  { role: "courier", labelKey: "nav.courier", icon: Bike },
];

interface AppShellProps {
  health: readonly ServiceHealth[];
  source: DataSourceMode;
  availability: DataAvailability;
  sourceDetail: string;
  realtime: RealtimeConnectionState;
  onSourceChange: (source: DataSourceMode) => void;
  onRefreshHealth: () => void;
  session: TenantSession | null;
  sessionDetail: string;
  allowedRoles: readonly Role[];
  children: ReactNode;
}

export function AppShell({
  health,
  source,
  availability,
  sourceDetail,
  realtime,
  onSourceChange,
  onRefreshHealth,
  session,
  sessionDetail,
  allowedRoles,
  children,
}: AppShellProps) {
  const { locale, setLocale, t } = useLocale();
  const location = useLocation();
  const activeRole = (location.pathname.split("/")[1] || "operations") as Role;
  const unavailable = health.filter((item) => item.status === "unavailable").length;
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const mobileNavToggleRef = useRef<HTMLButtonElement>(null);
  const mobileNavRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!mobileNavOpen) return;
    const firstLink = mobileNavRef.current?.querySelector<HTMLAnchorElement>("a");
    firstLink?.focus();
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMobileNavOpen(false);
    };
    const keepFocusInNavigation = (event: KeyboardEvent) => {
      if (event.key !== "Tab") return;
      const links = mobileNavRef.current?.querySelectorAll<HTMLAnchorElement>("a");
      if (!links?.length) return;
      const first = links[0];
      const last = links[links.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", closeOnEscape);
    window.addEventListener("keydown", keepFocusInNavigation);
    return () => {
      window.removeEventListener("keydown", closeOnEscape);
      window.removeEventListener("keydown", keepFocusInNavigation);
      mobileNavToggleRef.current?.focus();
    };
  }, [mobileNavOpen]);

  return (
    <div className={`app-shell app-shell-${activeRole}`}>
      <aside className="sidebar" aria-label={t("shell.sidebar")}>
        <div className="sidebar-header">
          <div className="brand-lockup">
            <div className="brand-mark" aria-hidden="true">
              <Activity size={19} />
            </div>
            <div>
              <strong>RouteMind</strong>
              <span>{t("shell.deliveryControl")}</span>
            </div>
          </div>
          <button
            className="mobile-nav-toggle"
            ref={mobileNavToggleRef}
            type="button"
            aria-expanded={mobileNavOpen}
            aria-controls="role-navigation"
            aria-label={mobileNavOpen ? t("shell.closeNavigation") : t("shell.openNavigation")}
            onClick={() => setMobileNavOpen((open) => !open)}
          >
            <Menu size={17} aria-hidden="true" />
            <span>{mobileNavOpen ? t("shell.close") : t("shell.menu")}</span>
          </button>
        </div>
        <div className="sidebar-section-label">{t("shell.workspace")}</div>
        <nav
          className={`role-nav ${mobileNavOpen ? "mobile-nav-open" : ""}`}
          ref={mobileNavRef}
          id="role-navigation"
          aria-label={t("shell.navigation")}
        >
          {navigation
            .filter(({ role }) => allowedRoles.includes(role))
            .map(({ role, labelKey, icon: Icon }) => (
              <NavLink
                className={({ isActive }) => `role-link ${isActive ? "active" : ""}`}
                to={`/${role}`}
                key={role}
                aria-label={t(labelKey)}
                data-label={t(labelKey)}
                title={t(labelKey)}
                onClick={() => setMobileNavOpen(false)}
              >
                <Icon size={17} aria-hidden="true" />
                <span>{t(labelKey)}</span>
                <ChevronRight className="nav-chevron" size={15} aria-hidden="true" />
              </NavLink>
            ))}
        </nav>
        <div className="sidebar-footer">
          <div className="sidebar-section-label">{t("shell.environment")}</div>
          <div className="environment-chip">
            <span className="live-dot" /> {t("shell.localControlPlane")}
          </div>
        </div>
      </aside>
      <main className="main-column">
        <header className="topbar">
          <div className="topbar-title">
            <p className="eyebrow">{t("shell.routeMindWorkspace")}</p>
            <h1>{t("shell.deliveryControlCenter")}</h1>
          </div>
          <div className="topbar-actions">
            <div className="identity-status" role="status" title={sessionDetail}>
              <span>
                {session
                  ? session.subject
                  : source === "live"
                    ? t("shell.identityUnavailable")
                    : t("shell.isolatedSource")}
              </span>
              <small>
                {session
                  ? `Tenant ${session.tenantId.slice(0, 8)}`
                  : source === "live"
                    ? t("shell.failClosed")
                    : t("shell.noProductionIdentity")}
              </small>
            </div>
            <div className="source-status" title={sourceDetail}>
              <span className={`source-dot source-${source}`} />
              <span>
                {source === "demo"
                  ? t("shell.demoSnapshot")
                  : source === "replay"
                    ? t("shell.replay")
                    : source === "simulation"
                      ? t("shell.simulation")
                      : t("shell.live", { availability })}
              </span>
            </div>
            {source === "live" && (
              <span
                className={`realtime-state realtime-${realtime.status}`}
                role="status"
                title={realtime.staleReason ?? realtime.detail}
              >
                {realtime.status === "connected"
                  ? t("shell.streamConnected")
                  : realtime.status === "reconnecting"
                    ? t("shell.streamReconnecting")
                    : realtime.status === "stale"
                      ? t("shell.streamStale")
                      : realtime.status === "degraded"
                        ? t("shell.streamDegraded")
                        : t("shell.streamConnecting")}
              </span>
            )}
            <label className="source-selector">
              <span className="sr-only">{t("shell.dataSourceMode")}</span>
              <select
                aria-label={t("shell.dataSourceMode")}
                value={source}
                onChange={(event) => onSourceChange(event.target.value as DataSourceMode)}
              >
                <option value="live">{t("shell.dataSourceLive")}</option>
                <option value="demo">{t("shell.dataSourceDemo")}</option>
                <option value="replay">{t("shell.dataSourceReplay")}</option>
                <option value="simulation">{t("shell.dataSourceSimulation")}</option>
              </select>
            </label>
            <PreferencesPanel
              role={
                activeRole in
                { operations: true, strategy: true, customer: true, merchant: true, courier: true }
                  ? activeRole
                  : "operations"
              }
              source={source}
              availability={availability}
              session={session}
            />
            <div className="locale-switcher" role="group" aria-label={t("shell.locale")}>
              <button
                type="button"
                className={locale === "zh-CN" ? "active" : ""}
                aria-pressed={locale === "zh-CN"}
                aria-label={t("shell.switchToChinese")}
                onClick={() => setLocale("zh-CN")}
              >
                中
              </button>
              <button
                type="button"
                className={locale === "en-US" ? "active" : ""}
                aria-pressed={locale === "en-US"}
                aria-label={t("shell.switchToEnglish")}
                onClick={() => setLocale("en-US")}
              >
                EN
              </button>
            </div>
            <div
              className="health-summary"
              role="status"
              aria-label={t("shell.serviceHealthSummary")}
            >
              {health.map((item) => (
                <StatusPill key={item.service} status={item.status} label={item.label} />
              ))}
              {unavailable > 0 && (
                <span className="health-note">
                  {t("shell.unavailable", { count: unavailable })}
                </span>
              )}
            </div>
            <button
              className="icon-button"
              type="button"
              onClick={onRefreshHealth}
              title={t("shell.refreshServiceHealth")}
              aria-label={t("shell.refreshServiceHealth")}
            >
              <ClipboardList size={17} />
            </button>
          </div>
        </header>
        <div className="content-wrap">{children}</div>
      </main>
    </div>
  );
}
