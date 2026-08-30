import { useEffect, useRef, type MutableRefObject, type ReactNode } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import type { UrbanFieldSceneController } from "./UrbanFieldScene";

export type PointerTargetType = "scene" | "chart" | "hud" | "control" | null;

export interface RouteMindPointerState {
  x: number;
  y: number;
  nx: number;
  ny: number;
  vx: number;
  vy: number;
  intensity: number;
  targetId: string | null;
  targetType: PointerTargetType;
  pressed: boolean;
}

export interface OperationsMotionCoordinatorProps {
  children: ReactNode;
  sceneControllerRef?: MutableRefObject<UrbanFieldSceneController | null>;
}

interface SectionMetric {
  element: HTMLElement;
  name: string;
  start: number;
  end: number;
}

interface MotionFrame {
  progress: number;
  section: number;
  focus: number;
}

const SECTION_ORDER = [
  "overview",
  "filters",
  "projection",
  "simulation",
  "replay",
  "spatial",
  "analytics",
  "health",
  "metrics",
  "detail",
  "research",
  "reliability",
  "alerts",
];

const clamp = (value: number, min = 0, max = 1) => Math.min(max, Math.max(min, value));
const lerp = (from: number, to: number, amount: number) => from + (to - from) * amount;

function createPointerState(): RouteMindPointerState {
  return {
    x: 0,
    y: 0,
    nx: 0.5,
    ny: 0.5,
    vx: 0,
    vy: 0,
    intensity: 0,
    targetId: null,
    targetType: null,
    pressed: false,
  };
}

export function OperationsMotionCoordinator({
  children,
  sceneControllerRef,
}: OperationsMotionCoordinatorProps) {
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const root = rootRef.current;
    if (!root || typeof window === "undefined") return;
    if (typeof window.ResizeObserver !== "function") return;
    gsap.registerPlugin(ScrollTrigger);

    let frame = 0;
    let destroyed = false;
    let reducedMotion = false;
    const pointer = createPointerState();
    const targetPointer = createPointerState();
    const scrollFrame: MotionFrame = { progress: 0, section: 0, focus: 0 };
    const sections: SectionMetric[] = [];
    let lastScrollY = window.scrollY;
    let scrollVelocity = 0;
    const motionRoot = root;
    const stack = root.querySelector<HTMLElement>(".page-stack");

    const reducedQuery =
      typeof window.matchMedia === "function"
        ? window.matchMedia("(prefers-reduced-motion: reduce)")
        : null;
    reducedMotion = reducedQuery?.matches ?? false;

    const setVar = (name: string, value: number) => {
      motionRoot.style.setProperty(name, value.toFixed(4));
    };

    const updateSectionMetrics = () => {
      sections.length = 0;
      if (!stack) return;
      const rootTop = root.getBoundingClientRect().top + window.scrollY;
      Array.from(stack.querySelectorAll<HTMLElement>("[data-motion-section]")).forEach(
        (element, index) => {
          const name = element.dataset.motionSection ?? SECTION_ORDER[index] ?? `section-${index}`;
          const rect = element.getBoundingClientRect();
          const start = Math.max(0, rect.top + window.scrollY - rootTop);
          sections.push({
            element,
            name,
            start,
            end: start + Math.max(rect.height, 1),
          });
        },
      );
    };

    const updateSectionFocus = (absoluteOffset: number) => {
      if (!sections.length) return;
      const activeIndex = sections.reduce((best, section, index) => {
        if (absoluteOffset >= section.start) return index;
        return best;
      }, 0);
      const active = sections[activeIndex];
      const local = active
        ? clamp((absoluteOffset - active.start) / Math.max(active.end - active.start, 1))
        : 0;
      scrollFrame.section = activeIndex;
      scrollFrame.focus = reducedMotion ? 0.82 : 0.78 + Math.sin(local * Math.PI) * 0.22;
      motionRoot.dataset.motionFocus = active?.name ?? "overview";
      motionRoot.style.setProperty("--rm-section-name", `"${active?.name ?? "overview"}"`);
      setVar("--rm-section-progress", local);
    };

    const sampleScroll = (self?: ScrollTrigger) => {
      const rootTop = root.getBoundingClientRect().top + window.scrollY;
      const maxScroll = Math.max(root.scrollHeight - window.innerHeight, 1);
      const rootOffset = Math.max(0, window.scrollY - rootTop);
      const absoluteOffset = clamp(rootOffset / maxScroll, 0, 1) * maxScroll;
      scrollFrame.progress = self ? clamp(self.progress) : clamp(rootOffset / maxScroll);
      scrollVelocity = clamp(Math.abs(window.scrollY - lastScrollY) / 42);
      lastScrollY = window.scrollY;
      updateSectionFocus(absoluteOffset);
      sceneControllerRef?.current?.setScrollFrame(scrollFrame);
    };

    const classifyTarget = (eventTarget: EventTarget | null) => {
      if (!(eventTarget instanceof Element)) return { id: null, type: null as PointerTargetType };
      const control = eventTarget.closest<HTMLElement>(
        "button, input, select, textarea, a, [role='button']",
      );
      if (control) return { id: control.id || null, type: "control" as const };
      const target = eventTarget.closest<HTMLElement>("[data-pointer-target]");
      if (!target) return { id: null, type: null as PointerTargetType };
      const type = (target.dataset.pointerTarget ?? null) as PointerTargetType;
      if (type === "control") return { id: target.dataset.pointerId ?? null, type };
      return { id: target.dataset.pointerId ?? target.id ?? null, type };
    };

    const updateTargetPointer = (event: PointerEvent) => {
      targetPointer.x = event.clientX;
      targetPointer.y = event.clientY;
      targetPointer.nx = clamp(event.clientX / Math.max(window.innerWidth, 1));
      targetPointer.ny = clamp(event.clientY / Math.max(window.innerHeight, 1));
      const target = classifyTarget(event.target);
      targetPointer.targetId = target.id;
      targetPointer.targetType = target.type;
      targetPointer.pressed = event.buttons > 0;
    };

    const clearTargetPointer = () => {
      targetPointer.targetId = null;
      targetPointer.targetType = null;
      targetPointer.pressed = false;
      targetPointer.intensity = 0;
    };

    const onPointerMove = (event: PointerEvent) => updateTargetPointer(event);
    const onPointerDown = (event: PointerEvent) => {
      updateTargetPointer(event);
      targetPointer.pressed = true;
    };
    const onPointerUp = (event: PointerEvent) => {
      updateTargetPointer(event);
      targetPointer.pressed = false;
    };

    const onReducedMotionChange = (event: MediaQueryListEvent) => {
      reducedMotion = event.matches;
      motionRoot.dataset.motionReduced = String(reducedMotion);
      if (reducedMotion) {
        targetPointer.intensity = 0;
        pointer.intensity = 0;
      }
    };

    root.addEventListener("pointermove", onPointerMove, { passive: true });
    root.addEventListener("pointerdown", onPointerDown, { passive: true });
    root.addEventListener("pointerup", onPointerUp, { passive: true });
    root.addEventListener("pointerleave", clearTargetPointer, { passive: true });
    reducedQuery?.addEventListener?.("change", onReducedMotionChange);
    motionRoot.dataset.motionReduced = String(reducedMotion);

    const updateFrame = (now: number) => {
      if (destroyed) return;
      const pointerEase = reducedMotion ? 0.2 : 0.13;
      const nextX = lerp(pointer.x, targetPointer.x, pointerEase);
      const nextY = lerp(pointer.y, targetPointer.y, pointerEase);
      const dx = nextX - pointer.x;
      const dy = nextY - pointer.y;
      pointer.vx = lerp(pointer.vx, dx, reducedMotion ? 0.28 : 0.18);
      pointer.vy = lerp(pointer.vy, dy, reducedMotion ? 0.28 : 0.18);
      pointer.x = nextX;
      pointer.y = nextY;
      pointer.nx = lerp(pointer.nx, targetPointer.nx, pointerEase);
      pointer.ny = lerp(pointer.ny, targetPointer.ny, pointerEase);
      pointer.targetId = targetPointer.targetId;
      pointer.targetType = targetPointer.targetType;
      pointer.pressed = targetPointer.pressed;
      const velocity = Math.min(1, Math.hypot(pointer.vx, pointer.vy) / 34);
      const targetEnergy = reducedMotion
        ? pointer.targetType === "scene" || pointer.targetType === "chart"
          ? 0.35
          : 0
        : pointer.targetType === "scene" || pointer.targetType === "chart"
          ? Math.max(0.24, velocity)
          : 0;
      pointer.intensity = lerp(pointer.intensity, targetEnergy, reducedMotion ? 0.24 : 0.16);
      targetPointer.intensity = targetEnergy;
      motionRoot.dataset.pointerTarget = pointer.targetType ?? "none";

      setVar("--rm-pointer-x", pointer.nx);
      setVar("--rm-pointer-y", pointer.ny);
      setVar("--rm-pointer-intensity", pointer.intensity);
      setVar("--rm-scroll-velocity", scrollVelocity);
      motionRoot.style.setProperty("--rm-pointer-px", `${pointer.x}px`);
      motionRoot.style.setProperty("--rm-pointer-py", `${pointer.y}px`);
      motionRoot.style.setProperty("--rm-motion-time", `${now}ms`);
      sceneControllerRef?.current?.setPointerFrame(pointer);
      frame = window.requestAnimationFrame(updateFrame);
    };

    updateSectionMetrics();
    const refreshMetrics = () => {
      updateSectionMetrics();
      sampleScroll();
    };
    const resizeObserver = new ResizeObserver(refreshMetrics);
    resizeObserver.observe(root);

    const context = gsap.context(() => {
      const pageTrigger = ScrollTrigger.create({
        trigger: root,
        start: "top top",
        end: "bottom bottom",
        onUpdate: sampleScroll,
      });

      const visualStage = root.querySelector<HTMLElement>(".operations-hero-stage");
      const hero = root.querySelector<HTMLElement>('[data-motion-section="spatial"]');
      const analytics = root.querySelector<HTMLElement>('[data-motion-section="analytics"]');
      const detailElements = root.querySelectorAll<HTMLElement>(
        '[data-motion-section="detail"], [data-motion-section="research"], [data-motion-section="reliability"]',
      );

      if (visualStage && hero) {
        gsap.fromTo(
          visualStage,
          { scale: 0.92, y: 22, rotateX: 2.5, transformPerspective: 1200 },
          {
            scale: 1,
            y: 0,
            rotateX: 0,
            ease: "none",
            scrollTrigger: {
              trigger: hero,
              start: "top 82%",
              end: "top 16%",
              scrub: 0.7,
            },
          },
        );
      }

      if (analytics) {
        gsap.fromTo(
          analytics.querySelectorAll<HTMLElement>(".chart-frame"),
          { y: 44, z: -80, opacity: 0.35, scale: 0.94 },
          {
            y: 0,
            z: 0,
            opacity: 1,
            scale: 1,
            stagger: 0.07,
            ease: "none",
            scrollTrigger: {
              trigger: analytics,
              start: "top 88%",
              end: "top 38%",
              scrub: 0.75,
            },
          },
        );
      }

      detailElements.forEach((element, index) => {
        gsap.fromTo(
          element,
          { y: 28 + index * 5, z: -40 - index * 18, opacity: 0.72, transformPerspective: 1100 },
          {
            y: 0,
            z: 0,
            opacity: 1,
            ease: "power2.out",
            scrollTrigger: {
              trigger: element,
              start: "top 94%",
              end: "top 62%",
              scrub: 0.65,
            },
          },
        );
      });

      ScrollTrigger.addEventListener("refresh", refreshMetrics);
      ScrollTrigger.refresh();
      sampleScroll(pageTrigger);
    }, root);

    frame = window.requestAnimationFrame(updateFrame);
    return () => {
      destroyed = true;
      if (frame) window.cancelAnimationFrame(frame);
      resizeObserver.disconnect();
      root.removeEventListener("pointermove", onPointerMove);
      root.removeEventListener("pointerdown", onPointerDown);
      root.removeEventListener("pointerup", onPointerUp);
      root.removeEventListener("pointerleave", clearTargetPointer);
      reducedQuery?.removeEventListener?.("change", onReducedMotionChange);
      ScrollTrigger.removeEventListener("refresh", refreshMetrics);
      context.revert();
      sceneControllerRef?.current?.setPointerFrame(createPointerState());
    };
  }, [sceneControllerRef]);

  return (
    <div className="operations-motion-root" ref={rootRef}>
      <div className="operations-pointer-lens" aria-hidden="true">
        <span className="operations-pointer-lens-crosshair" />
        <span className="operations-pointer-lens-label">inspect</span>
      </div>
      {children}
    </div>
  );
}

export default OperationsMotionCoordinator;
