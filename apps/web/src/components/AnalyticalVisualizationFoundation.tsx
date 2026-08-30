import type { OperationsSnapshot } from "../domain/model";
import { toUrbanFieldState } from "../visuals/urbanFieldState";
import type { ReactNode } from "react";

interface OperationsAnalyticalStripProps {
  snapshot: OperationsSnapshot;
}

interface SignalPoint {
  label: string;
  value: number;
  detail: string;
}

const chartWidth = 360;
const chartHeight = 142;

export function OperationsAnalyticalStrip({ snapshot }: OperationsAnalyticalStripProps) {
  const state = toUrbanFieldState(snapshot);
  const throughput = buildThroughputSeries(snapshot.orders.length, state.pressure);
  const risk = buildRiskSeries(state.risk, state.traffic);
  const strategy = buildStrategyDistribution(snapshot.dispatch.strategy, state.supply, state.risk);
  const heatmap = buildHeatmap(state.pressure, state.traffic, state.risk);
  const provenance =
    snapshot.source === "live" ? "Snapshot-derived" : "Visual demo · non-production";

  return (
    <section className="analytics-foundation" aria-labelledby="analytics-foundation-title">
      <div className="analytics-foundation-heading">
        <div>
          <p className="eyebrow">Analytical visualization foundation</p>
          <h2 id="analytics-foundation-title">
            Operational signals, rendered with one visual language.
          </h2>
        </div>
        <span className="analytics-provenance">{provenance}</span>
      </div>
      <div className="analytics-grid analytics-grid-primary">
        <ChartFrame title="Network throughput" meta="orders / 12 ticks">
          <LineChart
            label="Operational throughput trend"
            points={throughput}
            color="var(--chart-teal)"
            suffix=" orders"
          />
          <div className="chart-footline">
            <span>
              <i className="chart-dot chart-dot-teal" /> throughput
            </span>
            <strong>{throughput.at(-1)?.value ?? 0} orders / tick</strong>
          </div>
        </ChartFrame>
        <ChartFrame title="SLA / risk trend" meta="risk index / bounded">
          <LineChart
            label="SLA risk trend"
            points={risk}
            color="var(--chart-amber)"
            threshold={0.58}
            suffix="%"
            percentage
          />
          <div className="chart-footline">
            <span>
              <i className="chart-dot chart-dot-amber" /> risk index
            </span>
            <strong className="chart-value-risk">{Math.round(state.risk * 100)}% current</strong>
          </div>
        </ChartFrame>
        <ChartFrame title="Latency / throughput" meta="last decision">
          <div
            className="latency-throughput"
            role="img"
            aria-label="Latency and throughput compact comparison"
          >
            <CompactSignal
              label="Latency"
              value={snapshot.dispatch.latencyMs ?? 0}
              max={180}
              suffix="ms"
              tone="amber"
            />
            <CompactSignal
              label="Throughput"
              value={Math.round((1 - state.pressure * 0.24) * 100)}
              max={100}
              suffix="%"
              tone="teal"
            />
            <div className="latency-axis" aria-hidden="true">
              <span>0</span>
              <span>target</span>
              <span>limit</span>
            </div>
          </div>
          <div className="chart-footline">
            <span>
              <i className="chart-dot chart-dot-slate" /> solver response
            </span>
            <strong>
              {snapshot.dispatch.latencyMs === null
                ? "Unavailable"
                : `${snapshot.dispatch.latencyMs} ms`}
            </strong>
          </div>
        </ChartFrame>
      </div>
      <div className="analytics-grid analytics-grid-secondary">
        <ChartFrame title="Strategy distribution" meta="comparison preview">
          <StrategyBars entries={strategy} />
          <div className="chart-footline">
            <span>
              <i className="chart-dot chart-dot-teal" /> selected strategy
            </span>
            <strong>{snapshot.dispatch.strategy}</strong>
          </div>
        </ChartFrame>
        <ChartFrame title="Zone pressure field" meta="spatial heatmap">
          <Heatmap cells={heatmap} />
          <div className="chart-footline">
            <span>
              <i className="chart-dot chart-dot-red" /> elevated risk
            </span>
            <strong>pressure × traffic</strong>
          </div>
        </ChartFrame>
      </div>
    </section>
  );
}

function ChartFrame({
  title,
  meta,
  children,
}: {
  title: string;
  meta: string;
  children: ReactNode;
}) {
  return (
    <article className="chart-frame">
      <header className="chart-frame-heading">
        <h3>{title}</h3>
        <span>{meta}</span>
      </header>
      {children}
    </article>
  );
}

function LineChart({
  label,
  points,
  color,
  threshold,
  suffix,
  percentage = false,
}: {
  label: string;
  points: readonly SignalPoint[];
  color: string;
  threshold?: number;
  suffix: string;
  percentage?: boolean;
}) {
  const values = points.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values, min + 1);
  const range = max - min;
  const x = (index: number) => 12 + (index / Math.max(points.length - 1, 1)) * (chartWidth - 28);
  const y = (value: number) => chartHeight - 18 - ((value - min) / range) * (chartHeight - 34);
  const path = points
    .map(
      (point, index) => `${index ? "L" : "M"} ${x(index).toFixed(2)} ${y(point.value).toFixed(2)}`,
    )
    .join(" ");
  const thresholdY = threshold === undefined ? null : y(min + threshold * range);

  return (
    <div className="line-chart-wrap">
      <svg
        className="line-chart"
        viewBox={`0 0 ${chartWidth} ${chartHeight}`}
        role="img"
        aria-label={label}
      >
        <title>{label}</title>
        {[0, 1, 2, 3].map((step) => {
          const lineY = 12 + step * ((chartHeight - 30) / 3);
          return (
            <line
              className="chart-gridline"
              key={step}
              x1="12"
              x2={chartWidth - 14}
              y1={lineY}
              y2={lineY}
            />
          );
        })}
        {thresholdY !== null && (
          <line
            className="chart-threshold"
            x1="12"
            x2={chartWidth - 14}
            y1={thresholdY}
            y2={thresholdY}
          />
        )}
        <path className="chart-line-shadow" d={path} style={{ stroke: color }} />
        <path className="chart-line" d={path} style={{ stroke: color }} />
        {points.map((point, index) => (
          <circle
            className="chart-point"
            cx={x(index)}
            cy={y(point.value)}
            key={point.label}
            r="3"
            tabIndex={0}
            style={{ fill: color }}
          >
            <title>{`${point.label}: ${percentage ? `${Math.round(point.value * 100)}${suffix}` : `${point.value}${suffix}`}`}</title>
          </circle>
        ))}
        <text className="chart-axis-label" x="12" y={chartHeight - 3}>
          {points[0]?.label}
        </text>
        <text
          className="chart-axis-label chart-axis-label-end"
          x={chartWidth - 14}
          y={chartHeight - 3}
        >
          {points.at(-1)?.label}
        </text>
      </svg>
    </div>
  );
}

function CompactSignal({
  label,
  value,
  max,
  suffix,
  tone,
}: {
  label: string;
  value: number;
  max: number;
  suffix: string;
  tone: "teal" | "amber";
}) {
  const percent = Math.min(100, Math.round((value / max) * 100));
  return (
    <div className="compact-signal">
      <div>
        <span>{label}</span>
        <strong>
          {value}
          {suffix}
        </strong>
      </div>
      <div className={`compact-track compact-${tone}`}>
        <span style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

function StrategyBars({
  entries,
}: {
  entries: readonly { label: string; value: number; selected: boolean }[];
}) {
  return (
    <div className="strategy-bars" role="img" aria-label="Strategy comparison distribution">
      {entries.map((entry) => (
        <div className="strategy-bar" key={entry.label}>
          <div className="strategy-bar-label">
            <span>{entry.label}</span>
            <strong>{entry.value}%</strong>
          </div>
          <div className={`strategy-bar-track ${entry.selected ? "selected" : ""}`}>
            <span style={{ width: `${entry.value}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function Heatmap({ cells }: { cells: readonly { value: number; label: string; risk: boolean }[] }) {
  return (
    <svg
      className="analytics-heatmap"
      viewBox="0 0 360 142"
      role="img"
      aria-label="Zone pressure and traffic heatmap"
    >
      <title>Zone pressure and traffic heatmap</title>
      {cells.map((cell, index) => {
        const column = index % 8;
        const row = Math.floor(index / 8);
        const fill = cell.risk ? "var(--chart-red)" : "var(--chart-teal)";
        return (
          <rect
            className="heatmap-cell"
            key={cell.label}
            x={12 + column * 43}
            y={12 + row * 29}
            width="37"
            height="23"
            rx="2"
            tabIndex={0}
            style={{ fill, opacity: 0.18 + cell.value * 0.72 }}
          >
            <title>{`${cell.label}: ${Math.round(cell.value * 100)}%${cell.risk ? " · elevated risk" : ""}`}</title>
          </rect>
        );
      })}
      <text className="chart-axis-label" x="12" y="137">
        lower pressure
      </text>
      <text className="chart-axis-label chart-axis-label-end" x="348" y="137">
        higher pressure
      </text>
    </svg>
  );
}

function buildThroughputSeries(orderCount: number, pressure: number): SignalPoint[] {
  return Array.from({ length: 12 }, (_, index) => ({
    label: `T-${String(index + 1).padStart(2, "0")}`,
    value: Math.max(
      1,
      Math.round(orderCount * 0.44 + Math.sin(index * 0.86) * 2 + pressure * index * 0.8),
    ),
    detail: "orders per tick",
  }));
}

function buildRiskSeries(risk: number, traffic: number): SignalPoint[] {
  return Array.from({ length: 12 }, (_, index) => ({
    label: `T-${String(index + 1).padStart(2, "0")}`,
    value: Math.min(
      0.98,
      Math.max(
        0.04,
        risk * 0.62 + traffic * 0.18 + Math.sin(index * 0.7 + 0.4) * 0.06 + index * 0.008,
      ),
    ),
    detail: "risk index",
  }));
}

function buildStrategyDistribution(strategy: string, supply: number, risk: number) {
  return [
    { label: strategy, value: Math.round(54 + supply * 18 - risk * 6), selected: true },
    { label: "capacity-aware", value: Math.round(43 + supply * 10), selected: false },
    { label: "RADS-H preview", value: Math.round(36 + (1 - risk) * 12), selected: false },
  ];
}

function buildHeatmap(pressure: number, traffic: number, risk: number) {
  return Array.from({ length: 24 }, (_, index) => {
    const wave = (Math.sin(index * 0.61 + pressure * 2) + 1) / 2;
    const value = Math.min(0.98, 0.18 + wave * 0.42 + pressure * 0.22 + traffic * 0.12);
    return {
      label: `zone-${String(index + 1).padStart(2, "0")}`,
      value,
      risk: value > 0.68 || (risk > 0.62 && index % 7 === 0),
    };
  });
}
