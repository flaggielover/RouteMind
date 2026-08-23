import { describe, expect, it } from "vitest";
import { demoDataSource } from "../data/demoSnapshot";
import { compareDecisionXrayReplay, projectDecisionXray } from "./decisionXray";

describe("decision X-Ray projection", () => {
  it("promotes an attached durable ledger record to the authoritative projection", () => {
    const digest = "a".repeat(64);
    const snapshot = {
      ...demoDataSource.getSnapshot(),
      decisionLedger: {
        decisionId: "ledger-decision-1",
        requestId: "dispatch-request-1",
        strategy: "weighted-greedy",
        strategyVersion: "dispatch-api:v1",
        referenceDataId: "ref-2026-08-24",
        clockDomain: "WALL" as const,
        inputDigest: digest,
        outputDigest: digest,
        inputSnapshotDigest: digest,
        outputSnapshotDigest: digest,
        inputSnapshotJson: '{"travel_seconds":120}',
        createdAt: "2026-08-24T08:00:00Z",
      },
    };

    const projection = projectDecisionXray(snapshot);

    expect(projection.authority).toBe("durable-ledger");
    expect(projection.decisionId).toBe("ledger-decision-1");
    expect(projection.provenance.requestId).toBe("dispatch-request-1");
    expect(projection.digests.inputSnapshot).toBe(digest);
    expect(projection.travel.status).toBe("recorded");
  });

  it("exposes provenance, candidates, grounded reasons, and honest travel state", () => {
    const snapshot = demoDataSource.getSnapshot();
    const projection = projectDecisionXray(snapshot);

    expect(projection.authority).toBe("snapshot-projection");
    expect(projection.decisionId).toMatch(/^snapshot:/);
    expect(projection.candidates).toHaveLength(3);
    expect(
      projection.candidates.find((candidate) => candidate.courierId === "courier-17"),
    ).toMatchObject({
      eligibility: "selected",
      rejectionReasons: ["courier is already on route"],
    });
    expect(projection.alternatives).toEqual(["courier-22", "courier-31"]);
    expect(projection.travel.status).toBe("unavailable");
    expect(projection.travel.summary).toMatch(/no provider travel metric/i);
    expect(projection.digests.decision).toHaveLength(64);
    expect(projection.summary).toMatch(/weighted-greedy.*courier-17/i);
  });

  it("flags bounded replay digest changes without mutating the captured snapshot", () => {
    const captured = {
      ...demoDataSource.getSnapshot(),
      replay: {
        clockDomain: "REPLAY" as const,
        artifactId: "fixture",
        scenarioId: "scenario",
        seed: 7,
        status: "ready" as const,
        verified: true,
        cursorSeconds: 0,
        durationSeconds: 10,
        speed: 1,
        replayDigest: "replay-artifact",
        provenance: "test fixture",
        events: [],
        visibleEvents: [],
        verificationError: null,
      },
    };
    const replayed = {
      ...captured,
      couriers: captured.couriers.map((courier) =>
        courier.id === "courier-22" ? { ...courier, status: "offline" as const } : courier,
      ),
    };

    expect(compareDecisionXrayReplay(captured, captured)).toMatchObject({
      bounded: true,
      status: "match",
    });
    expect(compareDecisionXrayReplay(captured, replayed)).toMatchObject({
      bounded: true,
      status: "changed",
    });
    expect(captured.couriers.find((courier) => courier.id === "courier-22")?.status).toBe(
      "available",
    );
  });
});
