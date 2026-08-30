import { describe, expect, it } from "vitest";
import { demoDataSource } from "../data/demoSnapshot";
import {
  interpolateUrbanWorldFrame,
  OPERATIONS_CHAPTER_ORDER,
  toOperationsChapterState,
} from "./operationsChapterState";

describe("operations chapter state", () => {
  it("keeps the approved seven-chapter order and renderer-neutral world roles", () => {
    const chapters = toOperationsChapterState(demoDataSource.getSnapshot(), "order-2042");

    expect(chapters.map((chapter) => chapter.id)).toEqual(OPERATIONS_CHAPTER_ORDER);
    expect(chapters).toHaveLength(7);
    expect(chapters[0]?.world.cameraMode).toBe("overview");
    expect(chapters[1]?.world.cameraMode).toBe("pressure-close");
    expect(chapters[2]?.world.cameraMode).toBe("risk-hotspot");
    expect(chapters[4]?.world.sceneRole).toBe("inspection");
    expect(chapters[6]?.world.cameraMode).toBe("research-stable");
    expect(chapters.every((chapter) => chapter.focusEntityId === "order-2042")).toBe(true);
    expect(chapters.every((chapter) => chapter.urbanField.spatial?.cells?.length)).toBeTruthy();
  });

  it("preserves unavailable source state without inventing production provenance", () => {
    const snapshot = {
      ...demoDataSource.getSnapshot(),
      availability: "unavailable" as const,
      sourceDetail: "fixture unavailable",
    };
    const chapters = toOperationsChapterState(snapshot);

    expect(chapters.every((chapter) => chapter.availability === "unavailable")).toBe(true);
    expect(chapters.every((chapter) => chapter.provenance === "deterministic demo state")).toBe(
      true,
    );
  });

  it("bounds interpolation and retains the future spatial contract", () => {
    const chapters = toOperationsChapterState(demoDataSource.getSnapshot());
    const before = interpolateUrbanWorldFrame(chapters, -3);
    const after = interpolateUrbanWorldFrame(chapters, 4);
    const middle = interpolateUrbanWorldFrame(chapters, 0.5);

    expect(before.progress).toBe(0);
    expect(before.chapter).toBe("overview");
    expect(after.progress).toBe(1);
    expect(after.chapter).toBe("research");
    expect(middle.layerVisibility.flows).toBeGreaterThanOrEqual(0);
    expect(middle.layerVisibility.flows).toBeLessThanOrEqual(1);
    expect(chapters[0]?.urbanField.spatial).toMatchObject({
      cells: expect.any(Array),
      nodes: expect.any(Array),
      flows: expect.any(Array),
      zones: expect.any(Array),
    });
  });
});
