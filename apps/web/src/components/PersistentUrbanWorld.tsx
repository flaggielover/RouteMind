import { lazy, Suspense, useEffect, useMemo, type MutableRefObject } from "react";
import type { OperationsSnapshot } from "../domain/model";
import { toUrbanFieldState } from "../visuals/urbanFieldState";
import type { UrbanWorldFrame } from "../visuals/operationsChapterState";
import type { UrbanFieldSceneController } from "./UrbanFieldScene";
import { UrbanFieldFallback } from "./UrbanFieldFallback";

const LazyUrbanFieldScene = lazy(() => import("./UrbanFieldScene"));

export interface PersistentUrbanWorldProps {
  snapshot: OperationsSnapshot;
  worldFrame: UrbanWorldFrame;
  controllerRef: MutableRefObject<UrbanFieldSceneController | null>;
}

export function PersistentUrbanWorld({
  snapshot,
  worldFrame,
  controllerRef,
}: PersistentUrbanWorldProps) {
  const state = useMemo(() => toUrbanFieldState(snapshot), [snapshot]);
  useEffect(() => {
    controllerRef.current?.setWorldFrame(worldFrame);
  }, [controllerRef, worldFrame]);
  return (
    <aside
      className="persistent-urban-world"
      data-world-chapter={worldFrame.chapter}
      data-world-role={worldFrame.sceneRole}
      data-pointer-target="scene"
      data-pointer-id="persistent-urban-world"
      aria-label="Persistent RouteMind urban operational world"
    >
      <div className="persistent-world-chrome" aria-hidden="true">
        <span className="persistent-world-kicker">ROUTEMIND / INTELLIGENCE CORE</span>
        <span className="persistent-world-chapter">{worldFrame.chapter.replace("-", " ")}</span>
      </div>
      <Suspense fallback={<UrbanFieldFallback state={state} />}>
        <LazyUrbanFieldScene
          state={state}
          controllerRef={controllerRef}
          onSceneReady={() => controllerRef.current?.setWorldFrame(worldFrame)}
        />
      </Suspense>
      <div className="persistent-world-readout" aria-live="polite">
        <span className="persistent-world-readout-label">active lens</span>
        <strong>{worldFrame.cameraMode.replaceAll("-", " ")}</strong>
        <span>
          {snapshot.dispatch.strategy} · {snapshot.dispatch.version}
        </span>
      </div>
      <div className="persistent-world-rule" aria-hidden="true" />
    </aside>
  );
}

export default PersistentUrbanWorld;
