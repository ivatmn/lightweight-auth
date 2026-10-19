# src/core/health.py
"""
Environment health checks.

- Probe the environment's `health_url` with a 1-second timeout.
- If `is_active = 0` → down (skip the network call).
- If the probe returns HTTP 200 within the timeout → up.
- Any other outcome (timeout, non-200, network error) → down.
"""

from __future__ import annotations

import httpx

HEALTH_TIMEOUT_SECONDS: float = 1.0


async def check_environment_health(
    health_url: str | None,
    is_active: bool,
) -> str:
    """
    Return 'up' or 'down' for a single environment.

    - Inactive environments are considered down without a network call.
    - Missing `health_url` is treated as down.
    - Any non-200 response or network error is down.
    """
    if not is_active:
        return "down"
    if not health_url:
        return "down"

    try:
        async with httpx.AsyncClient(timeout=HEALTH_TIMEOUT_SECONDS) as client:
            response = await client.get(health_url)
        return "up" if response.status_code == 200 else "down"
    except httpx.HTTPError:
        return "down"
