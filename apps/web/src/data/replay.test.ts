import { describe, expect, it } from "vitest";
import { createReplayDataSource, replayArtifact, verifyReplayArtifact } from "./replay";

describe("verified replay boundary", () => {
  it("verifies the artifact and exposes deterministic playback", async () => {
    expect(await verifyReplayArtifact(replayArtifact)).toBe(true);
    const source = createReplayDataSource();
    const loaded = await source.loadSnapshot?.();
    expect(loaded?.replay?.verified).toBe(true);
    expect(loaded?.replay?.status).toBe("ready");

    const stepped = await source.controlReplay?.({
      commandId: "step-1",
      action: "step",
      seconds: 30,
    });
    expect(stepped?.replay?.cursorSeconds).toBe(30);
    expect(stepped?.replay?.visibleEvents).toHaveLength(2);
    const seeked = await source.controlReplay?.({
      commandId: "seek-1",
      action: "seek",
      seconds: 90,
    });
    expect(seeked?.replay?.visibleEvents).toHaveLength(3);
    const reset = await source.controlReplay?.({ commandId: "reset-1", action: "reset" });
    expect(reset?.replay?.cursorSeconds).toBe(0);
  });
});
