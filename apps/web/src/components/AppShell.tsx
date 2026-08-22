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
import { NavLink } from "react-router-dom";
import type { ReactNode } from "react";
import type { DataAvailability, DataSourceMode, Role, ServiceHealth } from "../domain/model";
import type { RealtimeConnectionState } from "../data/realtime";
import { StatusPill } from "./StatusPill";

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
  const unavailable = health.filter((item) => item.status === "unavailable").length;
  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="RouteMind sidebar">
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true">
            <Activity size={19} />
          </div>
          <div>
            <strong>RouteMind</strong>
            <span>delivery control</span>
          </div>
        </div>
        <div className="sidebar-section-label">Workspace</div>
        <nav className="role-nav" aria-label="RouteMind navigation">
          {navigation.map(({ role, label, icon: Icon }) => (
            <NavLink
              className={({ isActive }) => `role-link ${isActive ? "active" : ""}`}
              to={`/${role}`}
              key={role}
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
          <button
            className="icon-button sidebar-menu"
            type="button"
            title="Open workspace settings"
            aria-label="Open workspace settings"
          >
            <Menu size={17} />
          </button>
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
              </select>
            </label>
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
