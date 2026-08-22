import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { OperationsMap } from "./OperationsMap";

const order = {
  id: "order-live",
  shortId: "LIVE-1",
  customerName: "Customer",
  merchantName: "Merchant",
  status: "CONFIRMED" as const,
  eta: "unknown",
  age: "live",
  priority: "standard" as const,
  destination: "Durable state",
  route: [],
  events: [],
};

describe("operations map projection", () => {
  it("keeps live orders without route geometry functional", () => {
    render(
      <OperationsMap
        orders={[order]}
        couriers={[]}
        selectedOrderId={order.id}
        onSelectOrder={vi.fn()}
        availability="ready"
        source="live"
        generatedAt="2026-08-22T10:00:00Z"
      />,
    );

    expect(screen.getByText("Route geometry is unavailable from this source")).toBeInTheDocument();
    expect(screen.getByText("LIVE-1")).toBeInTheDocument();
  });

  it("shows loading state before projections arrive", () => {
    render(
      <OperationsMap
        orders={[]}
        couriers={[]}
        selectedOrderId=""
        onSelectOrder={vi.fn()}
        availability="loading"
        source="live"
        generatedAt=""
      />,
    );

    expect(screen.getByText("Loading operational map projections")).toBeInTheDocument();
  });
});
