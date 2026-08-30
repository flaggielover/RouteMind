import {
  AdditiveBlending,
  ACESFilmicToneMapping,
  BoxGeometry,
  CatmullRomCurve3,
  Color,
  DirectionalLight,
  DoubleSide,
  FogExp2,
  GridHelper,
  HemisphereLight,
  IcosahedronGeometry,
  InstancedMesh,
  Matrix4,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  Object3D,
  PerspectiveCamera,
  PlaneGeometry,
  PointLight,
  Raycaster,
  Scene,
  SphereGeometry,
  SRGBColorSpace,
  TubeGeometry,
  Quaternion,
  Vector2,
  Vector3,
  WebGLRenderer,
} from "three";
import type { BufferGeometry, LineBasicMaterial } from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { useEffect, useRef, useState, type MutableRefObject } from "react";
import type { UrbanFieldState } from "../visuals/urbanFieldState";
import { UrbanFieldFallback } from "./UrbanFieldFallback";

export interface UrbanFieldSceneProps {
  state: UrbanFieldState;
  onFocusEntity?: (entityId: string | null) => void;
  onSceneReady?: () => void;
  controllerRef?: MutableRefObject<UrbanFieldSceneController | null>;
}

export interface UrbanFieldSceneController {
  setScrollFrame(frame: { progress: number; section: number; focus: number }): void;
  setPointerFrame(frame: {
    x?: number;
    y?: number;
    nx: number;
    ny: number;
    intensity: number;
    targetType?: "scene" | "chart" | "hud" | "control" | null;
  }): void;
  clearFocus(): void;
  dispose(): void;
}

type SceneStatus = "loading" | "ready" | "fallback";

interface SceneRefs {
  scene: Scene;
  camera: PerspectiveCamera;
  renderer: WebGLRenderer;
  composer: EffectComposer | null;
  lensPass: ShaderPass | null;
  core: Mesh;
  coreGeometry: BufferGeometry;
  cells: InstancedMesh;
  cellHeights: number[];
  cellWorldPositions: Vector3[];
  routes: Mesh[];
  nodes: Mesh[];
  raycaster: Raycaster;
  rayPlane: Mesh;
  pointerNdc: Vector2;
  pointerWorld: Vector3;
  hasPointerWorld: boolean;
  cameraBase: Vector3;
  cameraTarget: Vector3;
  reducedMotion: boolean;
  scrollProgress: number;
  sectionIndex: number;
  focusStrength: number;
  pointerIntensity: number;
  lensPointer: Vector2;
  coreScaleTarget: Vector3;
  focusedEntityId: string | null;
}

const SLATE = "#273840";
const TEAL = "#67c8c0";
const AMBER = "#d6a261";
const RISK = "#d86d6b";

export function UrbanFieldScene({
  state,
  onFocusEntity,
  onSceneReady,
  controllerRef,
}: UrbanFieldSceneProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const stateRef = useRef(state);
  const focusRef = useRef(onFocusEntity);
  const readyRef = useRef(onSceneReady);
  const [status, setStatus] = useState<SceneStatus>("loading");
  const [hoveredEntity, setHoveredEntity] = useState<string | null>(null);

  stateRef.current = state;
  focusRef.current = onFocusEntity;
  readyRef.current = onSceneReady;

  useEffect(() => {
    const host = hostRef.current;
    if (!host || typeof window === "undefined") return;

    let sceneRefs: SceneRefs | null = null;
    let frame = 0;
    let destroyed = false;
    let hidden = document.visibilityState === "hidden";
    let inViewport = true;
    if (controllerRef) controllerRef.current = null;
    const reducedQuery =
      typeof window.matchMedia === "function"
        ? window.matchMedia("(prefers-reduced-motion: reduce)")
        : null;

    const stopLoop = () => {
      if (frame) cancelAnimationFrame(frame);
      frame = 0;
    };

    const disposeObject = (object: Object3D) => {
      object.traverse((child) => {
        const mesh = child as Mesh;
        if (mesh.geometry) mesh.geometry.dispose();
        const material = mesh.material;
        if (Array.isArray(material)) material.forEach((item) => item.dispose());
        else if (material) material.dispose();
      });
    };

    const fallback = () => {
      stopLoop();
      if (!destroyed) setStatus("fallback");
    };

    try {
      const probe = document.createElement("canvas");
      const context = probe.getContext("webgl2") ?? probe.getContext("webgl");
      if (!context) {
        fallback();
        return () => undefined;
      }

      const renderer = new WebGLRenderer({
        antialias: true,
        alpha: true,
        powerPreference: "high-performance",
      });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
      renderer.outputColorSpace = SRGBColorSpace;
      renderer.toneMapping = ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.08;
      renderer.shadowMap.enabled = true;
      renderer.shadowMap.type = 2;
      renderer.setClearColor(new Color("#0b1216"), 0);
      renderer.domElement.className = "urban-field-canvas";
      renderer.domElement.setAttribute(
        "aria-label",
        "Interactive RouteMind urban operational field",
      );
      renderer.domElement.setAttribute("role", "img");
      host.prepend(renderer.domElement);

      const scene = new Scene();
      scene.background = new Color("#0b1216");
      scene.fog = new FogExp2("#0b1216", 0.055);
      const camera = new PerspectiveCamera(34, 1, 0.1, 100);
      camera.position.set(8.4, 7.2, 11.6);
      camera.lookAt(0, 1.15, 0);
      const post = createComposer(renderer, scene, camera);
      const composer = post?.composer ?? null;
      const lensPass = post?.lensPass ?? null;
      const reducedMotion = reducedQuery?.matches ?? false;

      const ambient = new HemisphereLight("#c8e2e0", "#11191e", 1.35);
      scene.add(ambient);
      const directional = new DirectionalLight("#e4f1ed", 3.4);
      directional.position.set(5.5, 10, 6);
      directional.castShadow = true;
      directional.shadow.mapSize.set(1024, 1024);
      directional.shadow.radius = 4;
      scene.add(directional);
      const keyLight = new PointLight(TEAL, 5.5, 12, 2);
      keyLight.position.set(-3.5, 3.7, 1.8);
      scene.add(keyLight);
      const riskLight = new PointLight(RISK, 3.2, 9, 2);
      riskLight.position.set(3.8, 1.7, -3.5);
      scene.add(riskLight);

      const ground = new Mesh(
        new PlaneGeometry(18, 12),
        new MeshStandardMaterial({
          color: "#101b20",
          roughness: 0.86,
          metalness: 0.12,
          side: DoubleSide,
        }),
      );
      ground.rotation.x = -Math.PI / 2;
      ground.position.y = -0.03;
      ground.receiveShadow = true;
      scene.add(ground);
      const grid = new GridHelper(18, 18, new Color("#36545b"), new Color("#1b3037"));
      grid.scale.z = 0.67;
      grid.position.y = 0;
      (grid.material as LineBasicMaterial).transparent = true;
      (grid.material as LineBasicMaterial).opacity = 0.46;
      scene.add(grid);

      const cellSource = stateRef.current.spatial?.cells ?? [];
      const cellCount = Math.max(cellSource.length, 72);
      const cellGeometry = new BoxGeometry(0.58, 1, 0.58);
      const cellMaterial = new MeshStandardMaterial({
        color: SLATE,
        vertexColors: true,
        roughness: 0.7,
        metalness: 0.22,
        emissive: "#122c31",
        emissiveIntensity: 0.38,
      });
      const cells = new InstancedMesh(cellGeometry, cellMaterial, cellCount);
      cells.castShadow = true;
      cells.receiveShadow = true;
      const cellHeights: number[] = [];
      const cellWorldPositions: Vector3[] = [];
      const cellMatrix = new Matrix4();
      const cellPosition = new Vector3();
      const cellScale = new Vector3(1, 1, 1);
      const cellQuaternion = new Quaternion();
      const cellColor = new Color();
      const tealColor = new Color(TEAL);
      const sourceCells = cellSource.length
        ? cellSource
        : Array.from({ length: cellCount }, (_, index) => ({
            id: `cell-${index}`,
            center: { x: 8 + (index % 12) * 7.6, y: 14 + Math.floor(index / 12) * 14.2 },
            intensity: 0.22 + ((index * 17) % 52) / 100,
            risk: ((index * 11) % 32) / 100,
          }));
      sourceCells.slice(0, cellCount).forEach((cell, index) => {
        const height = 0.24 + cell.intensity * 1.25 + stateRef.current.traffic * 0.35;
        const x = (cell.center.x / 100 - 0.5) * 16.4;
        const z = (cell.center.y / 100 - 0.5) * 9.3;
        cellPosition.set(x, height / 2, z);
        cellHeights[index] = height;
        cellWorldPositions[index] = new Vector3(x, 0, z);
        cellScale.set(1, height, 1);
        cellMatrix.compose(cellPosition, cellQuaternion, cellScale);
        cells.setMatrixAt(index, cellMatrix);
        cellColor
          .set(cell.risk && cell.risk > 0.55 ? AMBER : SLATE)
          .lerp(tealColor, Math.min(0.64, cell.intensity * 0.65));
        cells.setColorAt(index, cellColor);
      });
      cells.instanceMatrix.needsUpdate = true;
      if (cells.instanceColor) cells.instanceColor.needsUpdate = true;
      scene.add(cells);

      const routeGroup = new Object3D();
      const routes: Mesh[] = [];
      (stateRef.current.spatial?.flows ?? []).slice(0, 9).forEach((flow) => {
        const from = toWorldPoint(flow.from, 0.48);
        const to = toWorldPoint(flow.to, 0.58);
        const midpoint = from.clone().lerp(to, 0.5);
        midpoint.y += 0.56 + flow.value * 0.48;
        const curve = new CatmullRomCurve3([
          from,
          from.clone().lerp(midpoint, 0.52),
          midpoint,
          midpoint.clone().lerp(to, 0.5),
          to,
        ]);
        const routeMaterial = new MeshStandardMaterial({
          color: flow.risk && flow.risk > 0.6 ? AMBER : TEAL,
          emissive: flow.risk && flow.risk > 0.6 ? RISK : TEAL,
          emissiveIntensity: flow.risk && flow.risk > 0.6 ? 0.72 : 0.42,
          roughness: 0.46,
          metalness: 0.34,
          transparent: true,
          opacity: 0.68,
        });
        const route = new Mesh(
          new TubeGeometry(curve, 34, 0.018 + flow.value * 0.034, 6, false),
          routeMaterial,
        );
        route.userData = { id: flow.id, phase: routes.length * 0.8 };
        route.castShadow = true;
        routeGroup.add(route);
        routes.push(route);
      });
      scene.add(routeGroup);

      const nodeGroup = new Object3D();
      const nodeGeometry = new SphereGeometry(0.105, 14, 10);
      const nodes: Mesh[] = [];
      (stateRef.current.spatial?.nodes ?? []).slice(0, 30).forEach((node) => {
        const nodeColor = node.kind === "risk" ? RISK : node.kind === "courier" ? AMBER : TEAL;
        const material = new MeshStandardMaterial({
          color: nodeColor,
          emissive: nodeColor,
          emissiveIntensity: node.kind === "risk" ? 1.1 : 0.58,
          roughness: 0.3,
          metalness: 0.5,
        });
        const mesh = new Mesh(nodeGeometry, material);
        const point = toWorldPoint(node.position, node.kind === "risk" ? 0.55 : 0.4);
        mesh.position.copy(point);
        mesh.userData = { id: node.id, kind: node.kind, baseY: point.y };
        mesh.castShadow = true;
        nodeGroup.add(mesh);
        nodes.push(mesh);
      });
      scene.add(nodeGroup);

      // IcosahedronGeometry is non-indexed in the current Three.js release, which
      // lets the deformation pass address each triangle face directly.
      const coreGeometry = new IcosahedronGeometry(0.95, 2);
      const coreBasePositions = new Float32Array(
        coreGeometry.attributes.position.array as Float32Array,
      );
      const coreMaterial = new MeshStandardMaterial({
        color: "#41636a",
        emissive: "#1b7f83",
        emissiveIntensity: 0.58,
        roughness: 0.29,
        metalness: 0.54,
        flatShading: true,
      });
      const core = new Mesh(coreGeometry, coreMaterial);
      core.position.set(0, 1.72, 0);
      core.castShadow = true;
      scene.add(core);

      const coreWire = new Mesh(
        new IcosahedronGeometry(1.17, 1),
        new MeshBasicMaterial({ color: TEAL, wireframe: true, transparent: true, opacity: 0.14 }),
      );
      coreWire.position.copy(core.position);
      scene.add(coreWire);
      const halo = new Mesh(
        new SphereGeometry(1.52, 24, 16),
        new MeshBasicMaterial({
          color: TEAL,
          transparent: true,
          opacity: 0.06,
          blending: AdditiveBlending,
          depthWrite: false,
        }),
      );
      halo.position.copy(core.position);
      scene.add(halo);
      const hitArea = new Mesh(
        new SphereGeometry(1.4, 16, 12),
        new MeshBasicMaterial({ visible: false, side: DoubleSide }),
      );
      hitArea.position.copy(core.position);
      scene.add(hitArea);

      const rayPlane = new Mesh(
        new PlaneGeometry(18, 12),
        new MeshBasicMaterial({ visible: false, side: DoubleSide }),
      );
      rayPlane.rotation.x = -Math.PI / 2;
      rayPlane.updateMatrixWorld(true);
      scene.add(rayPlane);
      const sceneState: SceneRefs = {
        scene,
        camera,
        renderer,
        composer,
        lensPass,
        core,
        coreGeometry,
        cells,
        cellHeights,
        cellWorldPositions,
        routes,
        nodes: [hitArea, ...nodes],
        raycaster: new Raycaster(),
        rayPlane,
        pointerNdc: new Vector2(),
        pointerWorld: new Vector3(),
        hasPointerWorld: false,
        cameraBase: camera.position.clone(),
        cameraTarget: camera.position.clone(),
        reducedMotion,
        scrollProgress: 0,
        sectionIndex: 0,
        focusStrength: 0,
        pointerIntensity: 0,
        lensPointer: new Vector2(0.5, 0.5),
        coreScaleTarget: new Vector3(1, 1, 1),
        focusedEntityId: null,
      };
      sceneRefs = sceneState;
      if (controllerRef) {
        controllerRef.current = {
          setScrollFrame: (frame) => {
            if (!sceneRefs) return;
            sceneRefs.scrollProgress = Math.min(1, Math.max(0, frame.progress));
            sceneRefs.sectionIndex = frame.section;
            sceneRefs.focusStrength = Math.min(1, Math.max(0, frame.focus));
          },
          setPointerFrame: (frame) => {
            if (!sceneRefs) return;
            const targetType = frame.targetType ?? "scene";
            sceneRefs.pointerIntensity =
              targetType === "scene" ? Math.min(1, Math.max(0, frame.intensity)) : 0;
            if (targetType !== "scene") {
              sceneRefs.hasPointerWorld = false;
              sceneRefs.pointerIntensity = 0;
              if (sceneRefs.focusedEntityId !== null) {
                sceneRefs.focusedEntityId = null;
                setHoveredEntity(null);
                focusRef.current?.(null);
              }
              if (sceneRefs.lensPass) {
                sceneRefs.lensPass.uniforms.uIntensity.value = 0;
                sceneRefs.lensPass.uniforms.uRgbShift.value = 0;
              }
              return;
            }
            const rect = renderer.domElement.getBoundingClientRect();
            const localX = frame.x === undefined ? frame.nx : (frame.x - rect.left) / rect.width;
            const localY = frame.y === undefined ? frame.ny : (frame.y - rect.top) / rect.height;
            sceneRefs.pointerNdc.set(
              Math.min(1, Math.max(-1, localX * 2 - 1)),
              Math.min(1, Math.max(-1, -(localY * 2 - 1))),
            );
            sceneRefs.lensPointer.set(localX, 1 - localY);
            sceneRefs.raycaster.setFromCamera(sceneRefs.pointerNdc, sceneRefs.camera);
            const worldHit = sceneRefs.raycaster.intersectObject(sceneRefs.rayPlane, false)[0];
            if (worldHit) {
              sceneRefs.pointerWorld.copy(worldHit.point);
              sceneRefs.hasPointerWorld = true;
            }
            const hits = sceneRefs.raycaster.intersectObjects(sceneRefs.nodes, false);
            const hit = hits[0]?.object;
            const entityId =
              hit?.userData.id === undefined ? (hit ? "intelligence-core" : null) : hit.userData.id;
            if (sceneRefs.focusedEntityId !== entityId) {
              sceneRefs.focusedEntityId = entityId;
              setHoveredEntity(entityId);
              focusRef.current?.(entityId);
            }
          },
          clearFocus: () => {
            if (!sceneRefs) return;
            sceneRefs.hasPointerWorld = false;
            sceneRefs.pointerIntensity = 0;
            if (sceneRefs.focusedEntityId !== null) {
              sceneRefs.focusedEntityId = null;
              setHoveredEntity(null);
              focusRef.current?.(null);
            }
          },
          dispose: () => undefined,
        };
      }

      const resize = () => {
        if (!sceneRefs || !host.clientWidth || !host.clientHeight) return;
        const width = host.clientWidth;
        const height = host.clientHeight;
        sceneRefs.camera.aspect = width / height;
        sceneRefs.camera.updateProjectionMatrix();
        sceneRefs.renderer.setSize(width, height, false);
        sceneRefs.composer?.setSize(width, height);
      };
      const resizeObserver = new ResizeObserver(resize);
      resizeObserver.observe(host);
      resize();

      const updateReducedMotion = () => {
        if (sceneRefs) sceneRefs.reducedMotion = reducedQuery?.matches ?? false;
        if (sceneRefs?.reducedMotion) renderFrame(performance.now());
      };
      reducedQuery?.addEventListener?.("change", updateReducedMotion);

      const intersectionObserver = new IntersectionObserver(
        ([entry]) => {
          inViewport = entry?.isIntersecting ?? true;
          if (inViewport && !hidden) startLoop();
          else stopLoop();
        },
        { threshold: 0.05 },
      );
      intersectionObserver.observe(host);

      const visibilityChange = () => {
        hidden = document.visibilityState === "hidden";
        if (hidden || !inViewport) stopLoop();
        else startLoop();
      };
      document.addEventListener("visibilitychange", visibilityChange);

      let previous = performance.now();
      const frameMatrix = new Matrix4();
      const renderFrame = (now: number) => {
        if (destroyed || !sceneRefs) return;
        const refs = sceneRefs;
        const delta = Math.min(0.05, Math.max(0, (now - previous) / 1000));
        previous = now;
        const elapsed = now / 1000;
        const current = stateRef.current;
        const motion = !refs.reducedMotion;
        const coreMaterialRef = refs.core.material as MeshStandardMaterial;
        const pressure = current.pressure;
        const spatialBeat = Math.max(0, 1 - Math.abs(refs.scrollProgress - 0.055) / 0.075);
        const riskBeat = Math.max(0, 1 - Math.abs(refs.scrollProgress - 0.13) / 0.075);
        const strategyBeat = Math.max(0, 1 - Math.abs(refs.scrollProgress - 0.215) / 0.1);
        const detailBeat = Math.min(1, Math.max(0, (refs.scrollProgress - 0.29) / 0.24));
        const inspection = refs.pointerIntensity;
        const deformation = motion
          ? (0.045 + pressure * 0.16 + current.activityRate * 0.05) *
            (0.7 + spatialBeat * 0.45 + riskBeat * 0.75 + inspection * 0.65)
          : 0;
        const corePosition = refs.coreGeometry.attributes.position;
        const array = corePosition.array as Float32Array;
        for (let index = 0; index < array.length; index += 9) {
          const cx = (array[index] + array[index + 3] + array[index + 6]) / 3;
          const cy = (array[index + 1] + array[index + 4] + array[index + 7]) / 3;
          const cz = (array[index + 2] + array[index + 5] + array[index + 8]) / 3;
          const phase = elapsed * (0.8 + current.activityRate * 0.8) + cx * 2.1 + cz * 1.7;
          const scale = 1 + Math.sin(phase) * deformation;
          for (let vertex = 0; vertex < 3; vertex += 1) {
            const offset = index + vertex * 3;
            const baseX = coreBasePositions[offset];
            const baseY = coreBasePositions[offset + 1];
            const baseZ = coreBasePositions[offset + 2];
            array[offset] = cx + (baseX - cx) * scale;
            array[offset + 1] = cy + (baseY - cy) * scale;
            array[offset + 2] = cz + (baseZ - cz) * scale;
          }
        }
        corePosition.needsUpdate = motion;
        if (motion) refs.coreGeometry.computeVertexNormals();
        coreMaterialRef.emissiveIntensity =
          0.34 +
          current.risk * 0.46 +
          riskBeat * 0.34 +
          strategyBeat * 0.12 +
          inspection * 0.28 +
          Math.sin(elapsed * 1.4) * (motion ? 0.08 : 0);
        const coreScale = 1 + spatialBeat * 0.07 + riskBeat * 0.09 - strategyBeat * 0.08;
        refs.coreScaleTarget.set(coreScale, coreScale, coreScale);
        refs.core.scale.lerp(refs.coreScaleTarget, motion ? 0.08 : 1);
        refs.core.rotation.y += motion ? delta * (0.11 + current.activityRate * 0.12) : 0;
        refs.core.rotation.x = motion ? Math.sin(elapsed * 0.33) * 0.08 : 0;

        const wavePoint = refs.pointerWorld;
        refs.cellWorldPositions.forEach((position, index) => {
          const base = refs.cellHeights[index] ?? 0.6;
          const distance = refs.hasPointerWorld ? position.distanceTo(wavePoint) : 12;
          const wave =
            motion && refs.hasPointerWorld
              ? Math.sin(elapsed * 3.4 - distance * 2.2) * Math.exp(-distance * 0.54)
              : 0;
          const height = Math.max(
            0.12,
            base * (0.84 + riskBeat * 0.2 + strategyBeat * 0.1) +
              wave * (0.18 + current.activityRate * 0.18 + inspection * 0.12),
          );
          cellPosition.set(position.x, height / 2, position.z);
          cellScale.set(1, height, 1);
          frameMatrix.compose(cellPosition, cellQuaternion, cellScale);
          refs.cells.setMatrixAt(index, frameMatrix);
        });
        refs.cells.instanceMatrix.needsUpdate = motion && refs.hasPointerWorld;

        refs.nodes.slice(1).forEach((node, index) => {
          const focused = node.userData.id === hoveredEntity;
          const material = node.material as MeshStandardMaterial;
          const pulse = motion ? (Math.sin(elapsed * 2.4 + index * 0.67) + 1) * 0.08 : 0;
          material.emissiveIntensity = focused
            ? 1.25 + inspection * 0.45
            : 0.38 + pulse + riskBeat * 0.18;
          node.scale.setScalar(focused ? 1.55 + inspection * 0.18 : 1 + strategyBeat * 0.05);
          if (motion)
            node.position.y = node.userData.baseY + Math.sin(elapsed * 1.2 + index) * 0.04;
        });
        refs.routes.forEach((route, index) => {
          const material = route.material as MeshStandardMaterial;
          material.emissiveIntensity = refs.reducedMotion
            ? 0.34 + strategyBeat * 0.12
            : 0.34 +
              strategyBeat * 0.24 +
              riskBeat * 0.12 +
              (Math.sin(elapsed * 1.8 + index) + 1) * 0.08;
        });
        const pointerOffset = refs.pointerIntensity;
        refs.cameraTarget.set(
          refs.cameraBase.x +
            (refs.scrollProgress - 0.5) * 0.95 +
            refs.pointerNdc.x * 0.62 * pointerOffset,
          refs.cameraBase.y +
            spatialBeat * 0.26 -
            riskBeat * 0.18 -
            refs.pointerNdc.y * 0.34 * pointerOffset,
          refs.cameraBase.z +
            spatialBeat * 0.55 -
            riskBeat * 0.4 +
            strategyBeat * 1.15 +
            detailBeat * 0.35,
        );
        if (refs.lensPass) {
          refs.lensPass.uniforms.uPointer.value.copy(refs.lensPointer);
          refs.lensPass.uniforms.uIntensity.value = refs.reducedMotion
            ? 0
            : Math.min(0.55, refs.pointerIntensity * (0.56 + riskBeat * 0.22));
          refs.lensPass.uniforms.uRgbShift.value = refs.reducedMotion
            ? 0
            : Math.min(0.0045, refs.pointerIntensity * 0.0028);
        }
        if (motion) {
          camera.position.lerp(refs.cameraTarget, 1 - Math.pow(0.001, delta));
          camera.lookAt(0, 1.15 + riskBeat * 0.24 - strategyBeat * 0.12, 0);
        } else if (!camera.position.equals(refs.cameraBase)) {
          camera.position.copy(refs.cameraBase);
          camera.lookAt(0, 1.15, 0);
        }
        if (!hidden && inViewport) refs.composer?.render(delta);
        if (!hidden && inViewport && !refs.composer) refs.renderer.render(scene, camera);
        if (motion) frame = requestAnimationFrame(renderFrame);
      };
      const startLoop = () => {
        if (!sceneRefs || sceneRefs.reducedMotion || frame || hidden || !inViewport) return;
        previous = performance.now();
        frame = requestAnimationFrame(renderFrame);
      };

      if (!reducedMotion) startLoop();
      else renderFrame(performance.now());
      setStatus("ready");
      readyRef.current?.();

      return () => {
        destroyed = true;
        stopLoop();
        resizeObserver.disconnect();
        intersectionObserver.disconnect();
        reducedQuery?.removeEventListener?.("change", updateReducedMotion);
        document.removeEventListener("visibilitychange", visibilityChange);
        disposeObject(scene);
        composer?.dispose();
        renderer.dispose();
        renderer.domElement.remove();
        sceneRefs = null;
        if (controllerRef) controllerRef.current = null;
      };
    } catch {
      fallback();
      return () => undefined;
    }
  }, [controllerRef]);

  return status === "fallback" ? (
    <UrbanFieldFallback state={state} />
  ) : (
    <div
      className="urban-field-scene"
      ref={hostRef}
      data-scene-status={status}
      data-pointer-target="scene"
      data-pointer-id="urban-field"
    >
      <div className="urban-field-hud" aria-hidden="true">
        <span className="scene-kicker">Urban field / WebGL</span>
        <span className="scene-mode">
          {state.mode.toUpperCase()} · {state.strategy}
        </span>
      </div>
      <div className="urban-field-legend" aria-hidden="true">
        <span>
          <i className="legend-swatch legend-demand" /> demand
        </span>
        <span>
          <i className="legend-swatch legend-supply" /> supply
        </span>
        <span>
          <i className="legend-swatch legend-risk" /> risk
        </span>
      </div>
      <div className="urban-field-context" aria-live="polite">
        {hoveredEntity
          ? `Focused entity ${hoveredEntity}`
          : status === "loading"
            ? "Initializing spatial field"
            : "Spatial field ready"}
      </div>
    </div>
  );
}

export default UrbanFieldScene;

function toWorldPoint(point: { x: number; y: number }, elevation: number): Vector3 {
  return new Vector3((point.x / 100 - 0.5) * 16.4, elevation, (point.y / 100 - 0.5) * 9.3);
}

function createComposer(
  renderer: WebGLRenderer,
  scene: Scene,
  camera: PerspectiveCamera,
): { composer: EffectComposer; lensPass: ShaderPass } | null {
  try {
    const composer = new EffectComposer(renderer);
    composer.addPass(new RenderPass(scene, camera));
    composer.addPass(new UnrealBloomPass(new Vector2(1, 1), 0.42, 0.48, 0.82));
    const lensPass = new ShaderPass({
      uniforms: {
        tDiffuse: { value: null },
        uPointer: { value: new Vector2(0.5, 0.5) },
        uIntensity: { value: 0 },
        uRadius: { value: 0.25 },
        uRgbShift: { value: 0 },
      },
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform sampler2D tDiffuse;
        uniform vec2 uPointer;
        uniform float uIntensity;
        uniform float uRadius;
        uniform float uRgbShift;
        varying vec2 vUv;
        void main() {
          vec2 delta = vUv - uPointer;
          float distanceToPointer = length(delta);
          float edge = smoothstep(uRadius, 0.0, distanceToPointer);
          float localEnergy = edge * uIntensity;
          vec2 direction = normalize(delta + vec2(0.0001));
          float bulge = localEnergy * 0.038 * (1.0 - smoothstep(0.0, uRadius, distanceToPointer));
          vec2 lensUv = clamp(vUv - direction * bulge, 0.001, 0.999);
          float shift = uRgbShift * localEnergy * smoothstep(0.0, uRadius, distanceToPointer);
          float red = texture2D(tDiffuse, clamp(lensUv + direction * shift, 0.001, 0.999)).r;
          float green = texture2D(tDiffuse, lensUv).g;
          float blue = texture2D(tDiffuse, clamp(lensUv - direction * shift, 0.001, 0.999)).b;
          vec4 base = texture2D(tDiffuse, lensUv);
          gl_FragColor = vec4(red, green, blue, base.a);
        }
      `,
    });
    composer.addPass(lensPass);
    composer.addPass(new OutputPass());
    return { composer, lensPass };
  } catch {
    return null;
  }
}
