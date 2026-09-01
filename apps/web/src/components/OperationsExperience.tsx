import { lazy, Suspense, type ReactNode, type MutableRefObject } from "react";
import type { OperationsSnapshot } from "../domain/model";
import {
  cityGeoCatalog,
  cityIds,
  createCityOperationalDataset,
  type CityId,
} from "../visuals/cityGeo";
import type { GeoWorldController } from "../visuals/geoWorldController";
import type { UrbanWorldFrame } from "../visuals/operationsChapterState";
import { GeoWorldFallback } from "./GeoWorldFallback";
import { OperationsNavigationRail } from "./OperationsNavigationRail";

const PersistentGeoWorld = lazy(() => import("./PersistentGeoWorld"));

function CapabilityFallbackWorld({
  cityId,
  onCityChange,
  worldFrame,
  status,
  reason,
}: {
  cityId: CityId;
  onCityChange: (cityId: CityId) => void;
  worldFrame: UrbanWorldFrame;
  status: "loading" | "fallback";
  reason: string;
}) {
  return (
    <aside
      className="persistent-urban-world persistent-geo-world rm251-world-surface"
      data-city={cityId}
      data-map-status={status}
      data-world-chapter={worldFrame.chapter}
      data-world-role={worldFrame.sceneRole}
      aria-label="Persistent courier operations map fallback"
    >
      <GeoWorldFallback dataset={createCityOperationalDataset(cityId)} reason={reason} />
      <div
        className="geo-city-selector glass-overlay"
        role="group"
        aria-label="Select operations city"
      >
        {cityIds.map((id) => (
          <button
            key={id}
            type="button"
            className={id === cityId ? "active" : ""}
            aria-pressed={id === cityId}
            onClick={() => onCityChange(id)}
          >
            <span>{cityGeoCatalog[id].name}</span>
            <small>{cityGeoCatalog[id].nameZh}</small>
          </button>
        ))}
      </div>
    </aside>
  );
}

export interface OperationsExperienceProps {
  snapshot: OperationsSnapshot;
  worldFrame: UrbanWorldFrame;
  cityId: CityId;
  onCityChange: (cityId: CityId) => void;
  selectedTrajectoryId: string | null;
  onSelectTrajectory: (trajectoryId: string | null) => void;
  controllerRef: MutableRefObject<GeoWorldController | null>;
  children: ReactNode;
}

export function OperationsExperience({
  snapshot,
  worldFrame,
  cityId,
  onCityChange,
  selectedTrajectoryId,
  onSelectTrajectory,
  controllerRef,
  children,
}: OperationsExperienceProps) {
  const canRenderWebGl =
    typeof window !== "undefined" && typeof WebGL2RenderingContext !== "undefined";

  return (
    <div
      className="operations-experience rm251-material-experience"
      data-experience-world="persistent"
    >
      <OperationsNavigationRail />
      <div className="operations-experience-stage rm251-world-stage">
        {canRenderWebGl ? (
          <Suspense
            fallback={
              <CapabilityFallbackWorld
                cityId={cityId}
                onCityChange={onCityChange}
                worldFrame={worldFrame}
                status="loading"
                reason="Map bundle loading"
              />
            }
          >
            <PersistentGeoWorld
              snapshot={snapshot}
              worldFrame={worldFrame}
              cityId={cityId}
              onCityChange={onCityChange}
              selectedTrajectoryId={selectedTrajectoryId}
              onSelectTrajectory={onSelectTrajectory}
              controllerRef={controllerRef}
            />
          </Suspense>
        ) : (
          <CapabilityFallbackWorld
            cityId={cityId}
            onCityChange={onCityChange}
            worldFrame={worldFrame}
            status="fallback"
            reason="WebGL2 unavailable"
          />
        )}
      </div>
      <div className="operations-chapter-track page-stack rm251-material-chapter-track">
        {children}
      </div>
    </div>
  );
}

export default OperationsExperience;
