export const ROUTEMIND_MOTION = {
  duration: {
    reveal: 520,
    relocate: 760,
    focus: 900,
    handoff: 760,
    inspect: 340,
  },
  easing: {
    smooth: "cubic-bezier(0.22, 0.61, 0.36, 1)",
    precise: "cubic-bezier(0.16, 1, 0.3, 1)",
  },
  roles: [
    "reveal",
    "relocate",
    "focus",
    "handoff",
    "inspect",
    "chapter-transition",
    "map-camera",
    "analytical-emphasis",
  ] as const,
} as const;

export type RouteMindMotionRole = (typeof ROUTEMIND_MOTION.roles)[number];

export function motionDuration(role: RouteMindMotionRole): number {
  if (role === "reveal") return ROUTEMIND_MOTION.duration.reveal;
  if (role === "relocate" || role === "handoff" || role === "chapter-transition") {
    return ROUTEMIND_MOTION.duration.relocate;
  }
  if (role === "focus" || role === "map-camera" || role === "analytical-emphasis") {
    return ROUTEMIND_MOTION.duration.focus;
  }
  return ROUTEMIND_MOTION.duration.inspect;
}
