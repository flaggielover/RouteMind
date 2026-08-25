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
import { StatusPill } from "./StatusPill";
import { PreferencesPanel } from "./PreferencesPanel";

const navigation: Array<{ role: Role; label: string; icon: typeof LayoutDashboard }> = [
  { role: "operations", label: "Operations", icon: LayoutDashboard },
  { role: "strategy", label: "Strategy lab", icon: FlaskConical },
  { role: "customer", label: "Customer", icon: UserRound },
  { role: "merchant", label: "Merchant", icon: Store },
  { role: "courier", label: "Courier", icon: Bike },
];

interface AppShellProps {
  health: readonly ServiceHealth[];
  source: DataSourceMode;
  availability: DataAvailability;
  sourceDetail: string;
  realtime: RealtimeConnectionState;
  onSourceChange: (source: DataSourceMode) => void;
  onRefreshHealth: () => void;
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
  children,
}: AppShellProps) {
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
    <div className="app-shell">
      <aside className="sidebar" aria-label="RouteMind sidebar">
        <div className="sidebar-header">
          <div className="brand-lockup">
            <div className="brand-mark" aria-hidden="true">
              <Activity size={19} />
            </div>
            <div>
              <strong>RouteMind</strong>
              <span>delivery control</span>
            </div>
          </div>
          <button
            className="mobile-nav-toggle"
            ref={mobileNavToggleRef}
            type="button"
            aria-expanded={mobileNavOpen}
            aria-controls="role-navigation"
            aria-label={mobileNavOpen ? "Close workspace navigation" : "Open workspace navigation"}
            onClick={() => setMobileNavOpen((open) => !open)}
          >
            <Menu size={17} aria-hidden="true" />
            <span>{mobileNavOpen ? "Close" : "Menu"}</span>
          </button>
        </div>
        <div className="sidebar-section-label">Workspace</div>
        <nav
          className={`role-nav ${mobileNavOpen ? "mobile-nav-open" : ""}`}
          ref={mobileNavRef}
          id="role-navigation"
          aria-label="RouteMind navigation"
        >
          {navigation.map(({ role, label, icon: Icon }) => (
            <NavLink
              className={({ isActive }) => `role-link ${isActive ? "active" : ""}`}
              to={`/${role}`}
              key={role}
              onClick={() => setMobileNavOpen(false)}
            >
              <Icon size={17} aria-hidden="true" />
              <span>{label}</span>
              <ChevronRight className="nav-chevron" size={15} aria-hidden="true" />
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="sidebar-section-label">Environment</div>
          <div className="environment-chip">
            <span className="live-dot" /> local control plane
          </div>
        </div>
      </aside>
      <main className="main-column">
        <header className="topbar">
          <div className="topbar-title">
            <p className="eyebrow">RouteMind / workspace</p>
            <h1>Delivery control center</h1>
          </div>
          <div className="topbar-actions">
            <div className="source-status" title={sourceDetail}>
              <span className={`source-dot source-${source}`} />
              <span>
                {source === "demo"
                  ? "Demo snapshot"
                  : source === "replay"
                    ? "Replay"
                    : source === "simulation"
                      ? "Simulation"
                      : `Live ${availability}`}
              </span>
            </div>
            {source === "live" && (
              <span
                className={`realtime-state realtime-${realtime.status}`}
                role="status"
                title={realtime.staleReason ?? realtime.detail}
              >
                {realtime.status === "connected"
                  ? "Stream connected"
                  : realtime.status === "reconnecting"
                    ? "Stream reconnecting"
                    : realtime.status === "stale"
                      ? "Stream stale"
                      : realtime.status === "degraded"
                        ? "Stream degraded"
                        : "Stream connecting"}
              </span>
            )}
            <label className="source-selector">
              <span className="sr-only">Data source mode</span>
              <select
                aria-label="Data source mode"
                value={source}
                onChange={(event) => onSourceChange(event.target.value as DataSourceMode)}
              >
                <option value="live">Live</option>
                <option value="demo">Demo</option>
                <option value="replay">Replay</option>
                <option value="simulation">Simulation</option>
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
            />
            <div className="health-summary" role="status" aria-label="Service health summary">
              {health.map((item) => (
                <StatusPill key={item.service} status={item.status} label={item.label} />
              ))}
              {unavailable > 0 && <span className="health-note">{unavailable} unavailable</span>}
            </div>
            <button
              className="icon-button"
              type="button"
              onClick={onRefreshHealth}
              title="Refresh service health"
              aria-label="Refresh service health"
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
