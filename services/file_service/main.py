import os
import time
from dataclasses import dataclass
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel

from common.logging import configure_logging, get_logger
from common.middleware import RequestContextMiddleware
from common.metrics import OUTBOUND_REQUESTS

SERVICE_NAME = "file-service"
configure_logging(SERVICE_NAME)
log = get_logger(SERVICE_NAME)

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
AUTH_TIMEOUT = float(os.getenv("AUTH_TIMEOUT_SECONDS", "2.0"))

app = FastAPI(title="OpsPilot File Service")
app.add_middleware(RequestContextMiddleware, service_name=SERVICE_NAME)


@dataclass
class FileFailures:
    file_storage: bool = False
    network_to_auth: bool = False


FAILURES = FileFailures()


class FailureToggle(BaseModel):
    enabled: bool


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/admin/failures/{name}")
def set_failure(name: str, toggle: FailureToggle):
    if name == "file_storage":
        FAILURES.file_storage = toggle.enabled
    elif name == "network_to_auth":
        FAILURES.network_to_auth = toggle.enabled
    else:
        raise HTTPException(status_code=404, detail="Unknown failure switch")

    log.warning("failure_toggled", failure=name, enabled=toggle.enabled)
    return {"failure": name, "enabled": toggle.enabled}


async def _call_auth(user: str) -> dict:
    if FAILURES.network_to_auth:
        log.error("network_to_auth_blocked", user=user)
        return {
            "reachable": False,
            "status": None,
            "latency_ms": 0.0,
            "reason": "network_unreachable",
        }

    url = f"{AUTH_SERVICE_URL}/verify"
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=AUTH_TIMEOUT) as client:
            resp = await client.get(url, params={"user": user})
        latency_ms = round((time.time() - start) * 1000, 2)
        OUTBOUND_REQUESTS.labels(SERVICE_NAME, "auth", str(resp.status_code)).inc()
        reason = None if resp.status_code == 200 else "auth_service_unavailable"
        return {
            "reachable": True,
            "status": resp.status_code,
            "latency_ms": latency_ms,
            "reason": reason,
        }
    except httpx.TimeoutException:
        latency_ms = round((time.time() - start) * 1000, 2)
        OUTBOUND_REQUESTS.labels(SERVICE_NAME, "auth", "timeout").inc()
        return {
            "reachable": True,
            "status": None,
            "latency_ms": latency_ms,
            "reason": "auth_timeout",
        }
    except httpx.HTTPError as exc:
        latency_ms = round((time.time() - start) * 1000, 2)
        OUTBOUND_REQUESTS.labels(SERVICE_NAME, "auth", "error").inc()
        log.error("auth_call_failed", error=str(exc))
        return {
            "reachable": False,
            "status": None,
            "latency_ms": latency_ms,
            "reason": "auth_unreachable",
        }


@app.get("/shared-drive/access")
async def access_shared_drive(user: str = "alice"):
    if FAILURES.file_storage:
        log.error(
            "shared_drive_access_failed",
            user=user,
            reason="file_storage_mount_missing",
            component="file_storage",
        )
        raise HTTPException(status_code=503, detail="Shared drive storage not mounted")

    auth = await _call_auth(user)
    if auth["reason"] is not None:
        log.error(
            "shared_drive_access_denied",
            user=user,
            reason=auth["reason"],
            component="auth",
            auth_latency_ms=auth["latency_ms"],
        )
        raise HTTPException(status_code=503, detail="Authentication service unavailable")

    log.info("shared_drive_access_ok", user=user)
    return {
        "status": "ok",
        "user": user,
        "resource": "shared-drive",
        "auth_latency_ms": auth["latency_ms"],
    }


@app.get("/probe")
async def probe(user: str = "alice"):
    auth = await _call_auth(user)
    accessible = auth["reason"] is None and not FAILURES.file_storage

    hint: Optional[str] = None
    if auth["reason"] is not None:
        hint = auth["reason"]
    elif FAILURES.file_storage:
        hint = "file_storage_mount_missing"

    return {
        "user": user,
        "checks": {
            "auth": auth,
            "file_storage": {"mounted": not FAILURES.file_storage},
            "shared_drive": {"accessible": accessible},
        },
        "root_cause_hint": hint,
    }


def _reset_local_failures():
    FAILURES.file_storage = False
    FAILURES.network_to_auth = False


async def _set_auth_failure(name: str, enabled: bool, latency_seconds: float = 5.0):
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            await client.post(
                f"{AUTH_SERVICE_URL}/admin/failures/{name}",
                json={"enabled": enabled, "latency_seconds": latency_seconds},
            )
    except httpx.HTTPError as exc:
        log.error("failed_to_set_auth_failure", failure=name, error=str(exc))


@app.post("/admin/scenarios/{name}")
async def run_scenario(name: str):
    if name == "healthy":
        _reset_local_failures()
        await _set_auth_failure("auth_down", False)
        await _set_auth_failure("auth_slow", False)

    elif name == "auth_down":
        _reset_local_failures()
        await _set_auth_failure("auth_down", True)
        await _set_auth_failure("auth_slow", False)

    elif name == "auth_slow":
        _reset_local_failures()
        await _set_auth_failure("auth_down", False)
        await _set_auth_failure("auth_slow", True, latency_seconds=5.0)

    elif name == "mount_missing":
        _reset_local_failures()
        await _set_auth_failure("auth_down", False)
        await _set_auth_failure("auth_slow", False)
        FAILURES.file_storage = True

    elif name == "network_partition":
        _reset_local_failures()
        await _set_auth_failure("auth_down", False)
        await _set_auth_failure("auth_slow", False)
        FAILURES.network_to_auth = True

    else:
        raise HTTPException(status_code=404, detail="Unknown scenario")

    log.warning("scenario_applied", scenario=name)
    return {"scenario": name, "applied": True}
