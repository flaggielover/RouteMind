import { describe, expect, it } from "vitest";
import { demoDataSource } from "../data/demoSnapshot";
import { countOpenExceptions, findOrder, orderStatusLabel, statusTone } from "./selectors";

describe("operations selectors", () => {
  const snapshot = demoDataSource.getSnapshot();

  it("exposes a complete lifecycle and finds a selected order", () => {
    const order = findOrder(snapshot, "order-2041");

    expect(order.shortId).toBe("RM-2041");
    expect(order.events).toHaveLength(8);
    expect(order.events.every((event) => event.completed)).toBe(true);
    expect(orderStatusLabel[order.status]).toBe("Delivered");
  });

  it("derives exception count from priority orders that are not delivered", () => {
    expect(countOpenExceptions(snapshot)).toBe(1);
    expect(statusTone("OUT_FOR_DELIVERY")).toBe("info");
    expect(statusTone("PREPARING")).toBe("warning");
    expect(statusTone("DELIVERED")).toBe("success");
  });
});
