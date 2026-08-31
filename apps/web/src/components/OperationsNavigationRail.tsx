import type { OperationsChapterId } from "../visuals/operationsChapterState";
import { useLocale } from "../i18n";

const chapters: readonly { id: OperationsChapterId; labelKey: string }[] = [
  { id: "overview", labelKey: "chapter.overview" },
  { id: "pressure", labelKey: "chapter.pressure" },
  { id: "risk", labelKey: "chapter.risk" },
  { id: "strategy", labelKey: "chapter.strategy" },
  { id: "live", labelKey: "chapter.live" },
  { id: "replay", labelKey: "chapter.replay" },
  { id: "research", labelKey: "chapter.research" },
];

export function OperationsNavigationRail() {
  const { t } = useLocale();
  return (
    <nav className="operations-chapter-rail" aria-label={t("ops.chapterNavigation")}>
      {chapters.map((chapter, index) => (
        <a
          key={chapter.id}
          href={`#operations-chapter-${chapter.id}`}
          title={t(chapter.labelKey)}
          aria-label={`${String(index + 1).padStart(2, "0")} ${t(chapter.labelKey)}`}
        >
          <span>{String(index + 1).padStart(2, "0")}</span>
        </a>
      ))}
    </nav>
  );
}

export default OperationsNavigationRail;
