import asyncio
import random
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel

from common.logging import configure_logging, get_logger
from common.middleware import RequestContextMiddleware

SERVICE_NAME = "auth-service"
configure_logging(SERVICE_NAME)
log = get_logger(SERVICE_NAME)

app = FastAPI(title="OpsPilot Auth Service")
app.add_middleware(RequestContextMiddleware, service_name=SERVICE_NAME)


@dataclass
class AuthFailures:
    auth_down: bool = False
    auth_slow_seconds: float = 0.0


FAILURES = AuthFailures()


class FailureToggle(BaseModel):
    enabled: bool
    latency_seconds: float = 5.0


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/admin/failures/{name}")
def set_failure(name: str, toggle: FailureToggle):
    if name == "auth_down":
        FAILURES.auth_down = toggle.enabled
    elif name == "auth_slow":
        FAILURES.auth_slow_seconds = toggle.latency_seconds if toggle.enabled else 0.0
    else:
        raise HTTPException(status_code=404, detail="Unknown failure switch")

    log.warning("failure_toggled", failure=name, enabled=toggle.enabled)
    return {"failure": name, "enabled": toggle.enabled}


@app.get("/verify")
async def verify(user: str):
    if FAILURES.auth_down:
        log.error("auth_unavailable", user=user, component="auth")
        raise HTTPException(status_code=503, detail="Auth service unavailable")

    if FAILURES.auth_slow_seconds > 0:
        log.warning(
            "auth_slow_injected", user=user, latency_s=FAILURES.auth_slow_seconds
        )
        await asyncio.sleep(FAILURES.auth_slow_seconds)

    latency_ms = round(random.uniform(1.0, 5.0), 2)
    log.info("auth_verified", user=user, latency_ms=latency_ms)
    return {"ok": True, "user": user, "latency_ms": latency_ms}
