from __future__ import annotations

import os

import uvicorn


def main() -> None:
    port = int(os.environ.get("COMPUTE_API_PORT", "18081"))
    uvicorn.run("routemind_compute.api.app:app", host="127.0.0.1", port=port)


if __name__ == "__main__":  # pragma: no cover - exercised through the installed entry point
    main()
