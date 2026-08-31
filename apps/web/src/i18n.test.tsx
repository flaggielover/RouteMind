import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { LocaleProvider, LOCALE_STORAGE_KEY, detectInitialLocale, useLocale } from "./i18n";

function Probe() {
  const { locale, t, formatNumber, formatDateTime, formatRelative } = useLocale();
  return (
    <div>
      <output data-testid="locale">{locale}</output>
      <output data-testid="title">{t("chapter.overview.title")}</output>
      <output data-testid="fallback">{t("missing.key")}</output>
      <output data-testid="number">{formatNumber(1200)}</output>
      <output data-testid="date">
        {formatDateTime("2026-08-31T10:00:00Z", { timeZone: "UTC" })}
      </output>
      <output data-testid="relative">{formatRelative(-1, "day")}</output>
    </div>
  );
}

describe("RouteMind locale runtime", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("prefers persisted locale and safely falls back to browser language", () => {
    const storage = { getItem: () => "zh-CN" };
    expect(detectInitialLocale(storage, ["en-US"])).toBe("zh-CN");
    expect(detectInitialLocale({ getItem: () => null }, ["zh-CN"])).toBe("zh-CN");
    expect(detectInitialLocale({ getItem: () => "unsupported" }, ["fr-FR"])).toBe("en-US");
  });

  it("renders translated keys, fallback keys, and locale-aware formatting", async () => {
    const user = userEvent.setup();
    function Harness() {
      const { locale, setLocale } = useLocale();
      return (
        <>
          <Probe />
          <button type="button" onClick={() => setLocale("zh-CN")}>
            Chinese
          </button>
          <output data-testid="current">{locale}</output>
        </>
      );
    }
    render(
      <LocaleProvider>
        <Harness />
      </LocaleProvider>,
    );
    expect(screen.getByTestId("locale")).toHaveTextContent("en-US");
    expect(screen.getByTestId("title")).toHaveTextContent("Keep the city moving.");
    expect(screen.getByTestId("fallback")).toHaveTextContent("missing.key");
    expect(screen.getByTestId("number")).toHaveTextContent("1,200");
    await user.click(screen.getByRole("button", { name: "Chinese" }));
    expect(screen.getByTestId("locale")).toHaveTextContent("zh-CN");
    expect(screen.getByTestId("title")).toHaveTextContent("让城市持续运转。");
    expect(window.localStorage.getItem(LOCALE_STORAGE_KEY)).toBe("zh-CN");
    expect(screen.getByTestId("relative")).toHaveTextContent("昨天");
  });
});
