import { describe, expect, it } from "vitest";
import { resolveMapOpticalLensTarget, type MapOpticalLensPointerFrame } from "./mapOpticalLens";

const frame: MapOpticalLensPointerFrame = {
  x: 300,
  y: 180,
  vx: 0,
  vy: 0,
  viewportWidth: 1000,
  viewportHeight: 600,
  active: true,
  reducedMotion: false,
};

describe("map optical lens target", () => {
  it("maps CSS pointer coordinates into the bottom-left WebGL drawing buffer", () => {
    const target = resolveMapOpticalLensTarget(frame, 1500, 900);

    expect(target.pointer[0]).toBeCloseTo(450);
    expect(target.pointer[1]).toBeCloseTo(630);
    expect(target.lensSize).toBeCloseTo(261);
    expect(target.opacity).toBe(1);
  });

  it("keeps RGB separation near zero at rest and raises it with velocity", () => {
    const resting = resolveMapOpticalLensTarget(frame, 1000, 600);
    const moving = resolveMapOpticalLensTarget({ ...frame, vx: 18, vy: 7 }, 1000, 600);
    const fast = resolveMapOpticalLensTarget({ ...frame, vx: 80 }, 1000, 600);

    expect(resting.rgbShift).toBe(0);
    expect(moving.rgbShift).toBeGreaterThan(0.009);
    expect(fast.rgbShift).toBeCloseTo(0.012);
  });

  it("suppresses chromatic response for reduced motion and inactive targets", () => {
    const reduced = resolveMapOpticalLensTarget(
      { ...frame, vx: 40, reducedMotion: true },
      1000,
      600,
    );
    const excluded = resolveMapOpticalLensTarget({ ...frame, vx: 40, active: false }, 1000, 600);

    expect(reduced.opacity).toBe(1);
    expect(reduced.rgbShift).toBe(0);
    expect(excluded.opacity).toBe(0);
    expect(excluded.rgbShift).toBe(0);
  });
});
