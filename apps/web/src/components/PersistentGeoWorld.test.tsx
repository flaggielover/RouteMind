import { fireEvent, render, screen } from "@testing-library/react";
import { createRef } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { demoDataSource } from "../data/demoSnapshot";
import type { GeoWorldController } from "../visuals/geoWorldController";
import { toOperationsChapterState } from "../visuals/operationsChapterState";
import PersistentGeoWorld from "./PersistentGeoWorld";

const mocks = vi.hoisted(() => ({
  addedLayers: new Map<string, unknown>(),
  mapRemove: vi.fn(),
  layerRemove: vi.fn(),
  overlayFinalize: vi.fn(),
  overlaySetProps: vi.fn(),
}));

vi.mock("maplibre-gl", () => {
  class Map {
    scrollZoom = { disable: vi.fn() };
    addControl() {
      return this;
    }
    addLayer(layer: { id: string }) {
      mocks.addedLayers.set(layer.id, layer);
      return this;
    }
    getLayer(id: string) {
      return mocks.addedLayers.get(id);
    }
    removeLayer(id: string) {
      mocks.addedLayers.delete(id);
      mocks.layerRemove(id);
      return this;
    }
    on(event: string, callback: () => void) {
      if (event === "load") callback();
      return this;
    }
    loaded() {
      return true;
    }
    getStyle() {
      return { layers: [] };
    }
    setPaintProperty() {}
    easeTo() {}
    jumpTo() {}
    remove() {
      mocks.mapRemove();
    }
  }
  return {
    Map,
    AttributionControl: class AttributionControl {},
    NavigationControl: class NavigationControl {},
    setWorkerUrl: vi.fn(),
  };
});

vi.mock("@deck.gl/mapbox", () => ({
  MapboxOverlay: class MapboxOverlay {
    setProps() {
      mocks.overlaySetProps();
    }
    finalize() {
      mocks.overlayFinalize();
    }
  },
}));

vi.mock("@deck.gl/layers", () => {
  class Layer {
    constructor(public readonly props: unknown) {}
  }
  return {
    ArcLayer: Layer,
    PathLayer: Layer,
    PolygonLayer: Layer,
    ScatterplotLayer: Layer,
    TextLayer: Layer,
  };
});

beforeEach(() => {
  mocks.addedLayers.clear();
  vi.stubGlobal("WebGL2RenderingContext", class WebGL2RenderingContext {});
});

afterEach(() => {
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

describe("persistent geographic world", () => {
  it("mounts one map world, exposes city switching, and disposes WebGL ownership", () => {
    const onCityChange = vi.fn();
    const onSelectTrajectory = vi.fn();
    const controllerRef = createRef<GeoWorldController>();
    const chapter = toOperationsChapterState(demoDataSource.getSnapshot())[0]!;
    const { unmount } = render(
      <PersistentGeoWorld
        snapshot={demoDataSource.getSnapshot()}
        worldFrame={chapter.world}
        cityId="shanghai"
        onCityChange={onCityChange}
        selectedTrajectoryId={null}
        onSelectTrajectory={onSelectTrajectory}
        controllerRef={controllerRef}
      />,
    );

    const world = screen.getByLabelText("Persistent Shanghai courier operations map");
    expect(world).toHaveAttribute("data-map-status", "ready");
    expect(world).toHaveAttribute("data-lens-mode", "webgl-cc-lens");
    vi.spyOn(world, "getBoundingClientRect").mockReturnValue({
      bottom: 600,
      height: 600,
      left: 0,
      right: 1000,
      top: 0,
      width: 1000,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    });
    controllerRef.current?.setPointerFrame({
      x: 300,
      y: 180,
      nx: 0.3,
      ny: 0.3,
      vx: 12,
      vy: 0,
      intensity: 0.32,
      targetType: "scene",
    });
    expect(world).toHaveAttribute("data-lens-active", "true");
    expect(world).toHaveAttribute("data-lens-distortion", "1.50");
    expect(world).toHaveAttribute("data-lens-rgb-shift", "0.00000");
    controllerRef.current?.setPointerFrame({
      x: 300,
      y: 180,
      nx: 0.3,
      ny: 0.3,
      vx: 12,
      vy: 0,
      intensity: 0.32,
      targetType: "control",
    });
    expect(world).toHaveAttribute("data-lens-active", "false");
    expect(screen.getByText("DEMO / SIMULATED")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Shenzhen/ }));
    expect(onCityChange).toHaveBeenCalledWith("shenzhen");
    expect(controllerRef.current).not.toBeNull();

    unmount();
    expect(mocks.layerRemove).toHaveBeenCalledWith("routemind-map-optical-lens");
    expect(mocks.overlayFinalize).toHaveBeenCalledOnce();
    expect(mocks.mapRemove).toHaveBeenCalledOnce();
    expect(controllerRef.current).toBeNull();
  });
});
