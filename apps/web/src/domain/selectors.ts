import type { OperationsSnapshot, Order, OrderStatus } from "./model";

export const orderStatusLabel: Record<OrderStatus, string> = {
  CREATED: "Created",
  CONFIRMED: "Confirmed",
  PREPARING: "Preparing",
  READY_FOR_PICKUP: "Ready for pickup",
  ASSIGNED: "Assigned",
  PICKED_UP: "Picked up",
  OUT_FOR_DELIVERY: "Out for delivery",
  DELIVERED: "Delivered",
};

export function findOrder(snapshot: OperationsSnapshot, orderId: string): Order {
  return snapshot.orders.find((order) => order.id === orderId) ?? snapshot.orders[0];
}

export function countOpenExceptions(snapshot: OperationsSnapshot): number {
  return snapshot.orders.filter(
    (order) => order.priority === "priority" && order.status !== "DELIVERED",
  ).length;
}

export function statusTone(status: OrderStatus): "neutral" | "info" | "warning" | "success" {
  if (status === "DELIVERED") return "success";
  if (status === "OUT_FOR_DELIVERY" || status === "PICKED_UP") return "info";
  if (status === "PREPARING" || status === "READY_FOR_PICKUP") return "warning";
  return "neutral";
}
