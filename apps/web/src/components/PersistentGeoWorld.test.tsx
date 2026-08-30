import { fireEvent, render, screen } from "@testing-library/react";
import { createRef } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { demoDataSource } from "../data/demoSnapshot";
import type { GeoWorldController } from "../visuals/geoWorldController";
import { toOperationsChapterState } from "../visuals/operationsChapterState";
import PersistentGeoWorld from "./PersistentGeoWorld";

const mocks = vi.hoisted(() => ({
  mapRemove: vi.fn(),
  overlayFinalize: vi.fn(),
  overlaySetProps: vi.fn(),
}));

vi.mock("maplibre-gl", () => {
  class Map {
    addControl() {
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
  };
});

beforeEach(() => {
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

    expect(screen.getByLabelText("Persistent Shanghai courier operations map")).toHaveAttribute(
      "data-map-status",
      "ready",
    );
    expect(screen.getByText("DEMO / SIMULATED")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Shenzhen/ }));
    expect(onCityChange).toHaveBeenCalledWith("shenzhen");
    expect(controllerRef.current).not.toBeNull();

    unmount();
    expect(mocks.overlayFinalize).toHaveBeenCalledOnce();
    expect(mocks.mapRemove).toHaveBeenCalledOnce();
    expect(controllerRef.current).toBeNull();
  });
});
