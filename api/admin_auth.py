"""Google OAuth admin SSO for CareerPilot demos.

When ADMIN_EMAILS is set, mutating / LLM routes require a signed session
cookie established via Sign in with Google. Allowed emails only become admin.

When ADMIN_EMAILS is empty, auth is off (local open mode).
"""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from fastapi import HTTPException, Request
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from google_auth_oauthlib.flow import Flow
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from pydantic import BaseModel

from paths import ROOT

# Allow Google OAuth over http://127.0.0.1 in local dev.
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
# Same Google client may already have gmail.* grants; don't fail admin SSO on that.
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

OAUTH_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

SESSION_ADMIN_KEY = "is_admin"
SESSION_EMAIL_KEY = "admin_email"
OAUTH_STATE_MAX_AGE_SECONDS = 60 * 10


class AdminStatusResponse(BaseModel):
    authEnabled: bool
    isAdmin: bool
    email: str | None = None


def get_admin_emails() -> set[str]:
    raw = (os.getenv("ADMIN_EMAILS") or "").strip()
    if not raw:
        return set()
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


def auth_enabled() -> bool:
    return bool(get_admin_emails())


def get_session_secret() -> str:
    secret = (os.getenv("ADMIN_SESSION_SECRET") or "").strip()
    if secret:
        return secret
    # Dev fallback — set ADMIN_SESSION_SECRET in any shared/demo deploy.
    return "careerpilot-dev-session-secret-change-me"


def _oauth_state_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_session_secret(), salt="careerpilot-oauth-pkce")


def get_frontend_url() -> str:
    return (os.getenv("FRONTEND_URL") or "http://127.0.0.1:5173").rstrip("/")


def get_oauth_redirect_uri() -> str:
    """Must match an authorized redirect URI in Google Cloud Console.

    Default goes through the Vite proxy so the session cookie is set on :5173.
    """
    return (
        os.getenv("GOOGLE_OAUTH_REDIRECT_URI")
        or "http://127.0.0.1:5173/api/admin/auth/callback"
    ).strip()


def _credentials_path() -> Path:
    env_path = (os.getenv("GOOGLE_OAUTH_CLIENT_SECRETS") or "").strip()
    if env_path:
        return Path(env_path)
    return ROOT / "credentials.json"


def load_oauth_client_config() -> dict[str, Any]:
    """Build a client config dict for google_auth_oauthlib Flow."""
    client_id = (os.getenv("GOOGLE_OAUTH_CLIENT_ID") or "").strip()
    client_secret = (os.getenv("GOOGLE_OAUTH_CLIENT_SECRET") or "").strip()

    if client_id and client_secret:
        return {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }

    path = _credentials_path()
    if not path.is_file():
        raise RuntimeError(
            "Google OAuth client not configured. Set GOOGLE_OAUTH_CLIENT_ID and "
            "GOOGLE_OAUTH_CLIENT_SECRET, or provide credentials.json."
        )

    data = json.loads(path.read_text())
    if "web" in data:
        return {"web": data["web"]}
    if "installed" in data:
        # Reuse desktop client secrets; add redirect URI in Google Console.
        installed = data["installed"]
        return {
            "web": {
                "client_id": installed["client_id"],
                "client_secret": installed["client_secret"],
                "auth_uri": installed.get(
                    "auth_uri", "https://accounts.google.com/o/oauth2/auth"
                ),
                "token_uri": installed.get(
                    "token_uri", "https://oauth2.googleapis.com/token"
                ),
            }
        }
    raise RuntimeError(f"Unrecognized OAuth client secrets format in {path}")


def build_oauth_flow(
    *,
    state: str | None = None,
    code_verifier: str | None = None,
) -> Flow:
    flow = Flow.from_client_config(
        load_oauth_client_config(),
        scopes=OAUTH_SCOPES,
        state=state,
    )
    flow.redirect_uri = get_oauth_redirect_uri()
    # PKCE: same verifier must be used for auth URL + token exchange.
    if code_verifier:
        flow.code_verifier = code_verifier
        flow.autogenerate_code_verifier = False
    else:
        flow.autogenerate_code_verifier = True
    return flow


def authorization_url(request: Request) -> str:
    # Put PKCE verifier in signed OAuth state so the Google round-trip
    # does not depend on the session cookie surviving the redirect.
    _ = request
    code_verifier = secrets.token_urlsafe(64)
    state = _oauth_state_serializer().dumps(
        {"v": code_verifier, "n": secrets.token_urlsafe(8)}
    )
    flow = build_oauth_flow(state=state, code_verifier=code_verifier)
    url, _ = flow.authorization_url(
        access_type="online",
        prompt="select_account",
    )
    return url


def _code_verifier_from_authorization_response(authorization_response: str) -> str:
    query = parse_qs(urlparse(authorization_response).query)
    state_values = query.get("state") or []
    if not state_values:
        raise HTTPException(status_code=400, detail="OAuth callback missing state")
    try:
        payload = _oauth_state_serializer().loads(
            state_values[0],
            max_age=OAUTH_STATE_MAX_AGE_SECONDS,
        )
    except SignatureExpired as exc:
        raise HTTPException(
            status_code=400,
            detail="OAuth login expired — click Admin sign-in again.",
        ) from exc
    except BadSignature as exc:
        raise HTTPException(status_code=400, detail="Invalid OAuth state") from exc

    verifier = payload.get("v") if isinstance(payload, dict) else None
    if not isinstance(verifier, str) or not verifier:
        raise HTTPException(
            status_code=400,
            detail="Missing OAuth code verifier — click Admin sign-in again.",
        )
    return verifier


def complete_oauth_login(request: Request, authorization_response: str) -> str:
    """Exchange code, verify email allowlist, set session. Returns admin email."""
    code_verifier = _code_verifier_from_authorization_response(authorization_response)
    query = parse_qs(urlparse(authorization_response).query)
    state = (query.get("state") or [None])[0]
    flow = build_oauth_flow(state=state, code_verifier=code_verifier)
    flow.fetch_token(authorization_response=authorization_response)

    credentials = flow.credentials
    if not credentials.id_token:
        raise HTTPException(status_code=400, detail="Google did not return an ID token")

    claims = google_id_token.verify_oauth2_token(
        credentials.id_token,
        google_requests.Request(),
        audience=load_oauth_client_config()["web"]["client_id"],
    )
    email = (claims.get("email") or "").strip().lower()
    email_verified = bool(claims.get("email_verified", False))
    if not email or not email_verified:
        raise HTTPException(status_code=400, detail="Google account email not verified")

    allowed = get_admin_emails()
    if email not in allowed:
        request.session.clear()
        raise HTTPException(
            status_code=403,
            detail=f"{email} is not an allowed admin account",
        )

    request.session[SESSION_ADMIN_KEY] = True
    request.session[SESSION_EMAIL_KEY] = email
    return email


def clear_admin_session(request: Request) -> None:
    request.session.clear()


def is_admin_request(request: Request) -> bool:
    if not auth_enabled():
        return True
    return bool(request.session.get(SESSION_ADMIN_KEY))


def admin_status(request: Request) -> AdminStatusResponse:
    enabled = auth_enabled()
    if not enabled:
        return AdminStatusResponse(authEnabled=False, isAdmin=True, email=None)
    email = request.session.get(SESSION_EMAIL_KEY)
    return AdminStatusResponse(
        authEnabled=True,
        isAdmin=bool(request.session.get(SESSION_ADMIN_KEY)),
        email=email if isinstance(email, str) else None,
    )


def require_admin(request: Request) -> None:
    if is_admin_request(request):
        return
    raise HTTPException(
        status_code=401,
        detail="Admin sign-in required for this action (demo mode blocks AI / edits).",
    )
