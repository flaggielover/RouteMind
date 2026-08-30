import type { UrbanFieldState } from "../visuals/urbanFieldState";

export function UrbanFieldFallback({ state }: { state: UrbanFieldState }) {
  const modeLabel =
    state.mode === "live"
      ? "Live"
      : `${state.mode[0].toUpperCase()}${state.mode.slice(1)} · non-production`;
  return (
    <section
      className="urban-field-fallback"
      role="img"
      aria-label="RouteMind urban field fallback summary"
    >
      <div className="urban-fallback-header">
        <span className="scene-kicker">Urban field / static capability fallback</span>
        <strong>{modeLabel}</strong>
      </div>
      <div className="urban-fallback-grid" aria-hidden="true">
        {Array.from({ length: 36 }, (_, index) => {
          const value = 22 + ((index * 17) % 62) + state.pressure * 14;
          return <i key={index} style={{ height: `${value}%`, opacity: 0.35 + value / 150 }} />;
        })}
      </div>
      <div className="urban-fallback-metrics">
        <span>
          <small>Pressure</small>
          <strong>{Math.round(state.pressure * 100)}%</strong>
        </span>
        <span>
          <small>Supply</small>
          <strong>{Math.round(state.supply * 100)}%</strong>
        </span>
        <span>
          <small>SLA risk</small>
          <strong className="metric-risk">{Math.round(state.risk * 100)}%</strong>
        </span>
        <span>
          <small>Twin fidelity</small>
          <strong>{Math.round(state.twinFidelity * 100)}%</strong>
        </span>
      </div>
      <p>
        WebGL is unavailable in this environment. Semantic metrics remain available from the
        selected source.
      </p>
    </section>
  );
}
