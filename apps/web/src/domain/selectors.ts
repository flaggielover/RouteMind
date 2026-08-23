import type { OperationsSnapshot, Order, OrderStatus } from "./model";

export const orderStatusLabel: Record<OrderStatus, string> = {
  CREATED: "Created",
  CONFIRMED: "Confirmed",
  PREPARING: "Preparing",
  READY_FOR_PICKUP: "Ready for pickup",
  ASSIGNED: "Assigned",
  ACCEPTED: "Assignment accepted",
  ARRIVED: "Arrived at merchant",
  PICKED_UP: "Picked up",
  OUT_FOR_DELIVERY: "Out for delivery",
  DELIVERED: "Delivered",
  ASSIGNMENT_TIMED_OUT: "Assignment timed out",
  ASSIGNMENT_REJECTED: "Assignment rejected",
  REASSIGNMENT_PENDING: "Reassignment pending",
  COMPENSATING: "Compensation in progress",
  COMPENSATED: "Compensated",
  CANCELLED: "Cancelled",
};

export function findOrder(snapshot: OperationsSnapshot, orderId: string): Order {
  const order = snapshot.orders.find((candidate) => candidate.id === orderId) ?? snapshot.orders[0];
  if (!order) {
    throw new Error("selected order is unavailable");
  }
  return order;
}

export function countOpenExceptions(snapshot: OperationsSnapshot): number {
  return snapshot.orders.filter(
    (order) => order.priority === "priority" && order.status !== "DELIVERED",
  ).length;
}

export function statusTone(status: OrderStatus): "neutral" | "info" | "warning" | "success" {
  if (status === "DELIVERED") return "success";
  if (status === "CANCELLED" || status === "COMPENSATED") return "neutral";
  if (status === "ASSIGNMENT_REJECTED" || status === "ASSIGNMENT_TIMED_OUT") return "warning";
  if (status === "REASSIGNMENT_PENDING" || status === "COMPENSATING") return "info";
  if (
    status === "OUT_FOR_DELIVERY" ||
    status === "PICKED_UP" ||
    status === "ACCEPTED" ||
    status === "ARRIVED"
  )
    return "info";
  if (status === "PREPARING" || status === "READY_FOR_PICKUP") return "warning";
  return "neutral";
}
