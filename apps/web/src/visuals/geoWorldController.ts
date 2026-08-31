import type { UrbanWorldFrame } from "./operationsChapterState";

export interface GeoWorldController {
  setWorldFrame(frame: UrbanWorldFrame): void;
  setScrollFrame(frame: { progress: number; section: number; focus: number }): void;
  setPointerFrame(frame: {
    x: number;
    y: number;
    nx: number;
    ny: number;
    vx: number;
    vy: number;
    intensity: number;
    pressed?: boolean;
    targetType?: "scene" | "chart" | "hud" | "control" | null;
  }): void;
  clearFocus(): void;
}
