from __future__ import annotations

import os

import jwt
from fastapi import Header, HTTPException, Request


ROLE_PERMS = {
    "admin": {"*"},
    "police_officer": {
        "case.create",
        "case.view",
        "case.update",
        "case.close",
        "ledger.view",
        "analytics.view",
        "movement.run",
        "alert.recalc",
        "activation.dispatch",
        "activation.revoke",
    },
    "dispatcher": {"case.view", "case.update", "ledger.view"},
    "volunteer": {"activation.response", "case.view_limited"},
    "auditor": {"case.view", "ledger.verify", "ledger.view", "analytics.view"},
}


def require_permission(permission: str, x_role: str | None) -> str:
    role = (x_role or "").strip().lower()
    if not role:
        raise HTTPException(status_code=401, detail="Missing role header X-Role")

    perms = ROLE_PERMS.get(role)
    if perms is None:
        raise HTTPException(status_code=403, detail="Unknown role")
    if "*" in perms or permission in perms:
        return role

    raise HTTPException(status_code=403, detail=f"Role '{role}' lacks permission '{permission}'")


def permission_dependency(permission: str):
    def _dep(
        request: Request,
        authorization: str | None = Header(default=None, alias="Authorization"),
        x_role: str | None = Header(default=None, alias="X-Role"),
    ) -> str:
        role: str | None = None

        require_service_token = os.getenv("TRACEON_REQUIRE_SERVICE_TOKEN", "false").lower() == "true"
        service_secret = os.getenv("TRACEON_SERVICE_SECRET", "traceon-service-secret")

        if authorization and authorization.lower().startswith("bearer "):
            token = authorization.split(" ", 1)[1].strip()
            try:
                claims = jwt.decode(token, service_secret, algorithms=["HS256"])
                role = str(claims.get("role", "")).lower() or None
                # Keep decoded claims available for handlers if needed.
                request.state.auth_claims = claims
            except jwt.PyJWTError as exc:
                raise HTTPException(status_code=401, detail=f"Invalid internal service token: {exc}") from exc

        if role is None:
            if require_service_token:
                raise HTTPException(status_code=401, detail="Missing Authorization Bearer token")
            role = x_role

        return require_permission(permission, role)

    return _dep
