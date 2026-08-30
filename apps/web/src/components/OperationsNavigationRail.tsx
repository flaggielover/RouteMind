import type { OperationsChapterId } from "../visuals/operationsChapterState";

const chapters: readonly { id: OperationsChapterId; label: string }[] = [
  { id: "overview", label: "Network overview" },
  { id: "pressure", label: "Urban pressure" },
  { id: "risk", label: "SLA risk" },
  { id: "strategy", label: "Strategy" },
  { id: "live", label: "Live operations" },
  { id: "replay", label: "Simulation and replay" },
  { id: "research", label: "Reliability and research" },
];

export function OperationsNavigationRail() {
  return (
    <nav className="operations-chapter-rail" aria-label="Operations chapters">
      {chapters.map((chapter, index) => (
        <a
          key={chapter.id}
          href={`#operations-chapter-${chapter.id}`}
          title={chapter.label}
          aria-label={`${String(index + 1).padStart(2, "0")} ${chapter.label}`}
        >
          <span>{String(index + 1).padStart(2, "0")}</span>
        </a>
      ))}
    </nav>
  );
}

export default OperationsNavigationRail;
