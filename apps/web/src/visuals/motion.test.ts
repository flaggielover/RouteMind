import { describe, expect, it } from "vitest";
import { ROUTEMIND_MOTION, motionDuration } from "./motion";

describe("RouteMind motion vocabulary", () => {
  it("exposes stable semantic roles and restrained timing", () => {
    expect(ROUTEMIND_MOTION.roles).toContain("map-camera");
    expect(ROUTEMIND_MOTION.roles).toContain("analytical-emphasis");
    expect(motionDuration("inspect")).toBeLessThan(motionDuration("focus"));
    expect(motionDuration("chapter-transition")).toBe(760);
  });
});
