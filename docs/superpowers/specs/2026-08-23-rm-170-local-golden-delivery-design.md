# RM-170 Real Local Golden Delivery

Date: 2026-08-23

## Goal

Exercise one delivery from real local infrastructure through both runtimes:
PostgreSQL durable order state, Python dispatch, Java assignment, courier shift
and location commands, Outbox publication to RabbitMQ, Redis GEO projection,
and the final delivered lifecycle.

## Shape

`scripts/golden-delivery.ps1` owns process orchestration and cleanup. It starts
the existing Compose PostgreSQL/RabbitMQ/Redis stack, starts the Java and Python
processes using the repository scripts, waits on their health endpoints, and
drives only public HTTP commands. It uses a UUID courier candidate so the
compute decision can be applied directly through the versioned Java dispatch
assignment boundary.

The existing Outbox relay is scheduled at a bounded local interval when the
Rabbit publisher is enabled. The script polls PostgreSQL for the delivered
order, dispatch audit, published assignment event, and courier location; it
also probes RabbitMQ and Redis through their authenticated local CLI/API paths.
No browser mock or direct database mutation is used to create business state.

## Failure and cleanup

Health timeouts fail with service logs and preserve Compose volumes. Started
application processes are stopped in `finally`; the script does not delete
infrastructure volumes. Re-running is safe because each run uses a fresh
idempotency namespace and UUIDs.
