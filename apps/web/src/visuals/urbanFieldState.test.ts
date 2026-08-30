import { describe, expect, it } from "vitest";
import { demoDataSource } from "../data/demoSnapshot";
import { toUrbanFieldState } from "./urbanFieldState";

describe("urban field state adapter", () => {
  it("derives bounded operational signals and spatial extension points", () => {
    const state = toUrbanFieldState(demoDataSource.getSnapshot());

    expect(state.mode).toBe("demo");
    expect(state.provenance).toBe("visual-demo");
    expect(state.pressure).toBeGreaterThanOrEqual(0);
    expect(state.pressure).toBeLessThanOrEqual(1);
    expect(state.supply).toBeGreaterThanOrEqual(0);
    expect(state.supply).toBeLessThanOrEqual(1);
    expect(state.risk).toBeGreaterThanOrEqual(0);
    expect(state.risk).toBeLessThanOrEqual(1);
    expect(state.spatial?.cells).toHaveLength(72);
    expect(state.spatial?.nodes?.some((node) => node.kind === "courier")).toBe(true);
    expect(state.spatial?.flows?.length).toBeGreaterThan(0);
    expect(state.spatial?.zones).toHaveLength(2);
  });

  it("preserves live provenance while handling an empty fleet", () => {
    const snapshot = demoDataSource.getSnapshot();
    const state = toUrbanFieldState({
      ...snapshot,
      source: "live",
      orders: [],
      couriers: [],
      merchants: [],
    });

    expect(state.provenance).toBe("snapshot-derived");
    expect(state.supply).toBe(0);
    expect(state.pressure).toBe(0);
    expect(state.spatial?.cells).toHaveLength(72);
  });
});
