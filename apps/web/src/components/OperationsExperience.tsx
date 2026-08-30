import type { ReactNode, MutableRefObject } from "react";
import type { OperationsSnapshot } from "../domain/model";
import type { UrbanWorldFrame } from "../visuals/operationsChapterState";
import type { UrbanFieldSceneController } from "./UrbanFieldScene";
import { PersistentUrbanWorld } from "./PersistentUrbanWorld";
import { OperationsNavigationRail } from "./OperationsNavigationRail";

export interface OperationsExperienceProps {
  snapshot: OperationsSnapshot;
  worldFrame: UrbanWorldFrame;
  controllerRef: MutableRefObject<UrbanFieldSceneController | null>;
  children: ReactNode;
}

export function OperationsExperience({
  snapshot,
  worldFrame,
  controllerRef,
  children,
}: OperationsExperienceProps) {
  return (
    <div className="operations-experience" data-experience-world="persistent">
      <OperationsNavigationRail />
      <div className="operations-experience-stage">
        <PersistentUrbanWorld
          snapshot={snapshot}
          worldFrame={worldFrame}
          controllerRef={controllerRef}
        />
      </div>
      <div className="operations-chapter-track page-stack">{children}</div>
    </div>
  );
}

export default OperationsExperience;
