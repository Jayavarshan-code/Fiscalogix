"""
NetSuite SuiteTalk REST Connector — OAuth 2.0 Client Credentials (machine-to-machine).

Required env vars:
  NETSUITE_ACCOUNT_ID      — e.g. "1234567"  (no dashes, no suffix)
  NETSUITE_CLIENT_ID       — OAuth 2.0 client ID from NetSuite integration record
  NETSUITE_CLIENT_SECRET   — OAuth 2.0 client secret

Optional:
  NETSUITE_TOKEN_SCOPE     — space-separated scopes (default: "rest_webservices")

Token is cached in memory and refreshed automatically when it expires.
"""

import os
import time
import logging
import asyncio
from typing import Any, Dict, List, Optional

import httpx

from app.connectors.base_connector import BaseERPConnector

log = logging.getLogger(__name__)

# ── Credential resolution ─────────────────────────────────────────────────────

def _require_env(key: str) -> str:
    val = os.getenv(key, "").strip()
    if not val:
        raise EnvironmentError(
            f"NetSuite connector: missing required env var '{key}'. "
            "Set it in your .env file or deployment secrets."
        )
    return val


class _TokenCache:
    """In-process token cache. Thread-safe enough for single-worker async use."""
    access_token: Optional[str] = None
    expires_at: float = 0.0  # epoch seconds


_cache = _TokenCache()

# ── OAuth 2.0 helpers ─────────────────────────────────────────────────────────

def _account_slug(account_id: str) -> str:
    """NetSuite requires underscores instead of dashes in subdomain slugs."""
    return account_id.replace("-", "_").lower()


def _token_url(account_id: str) -> str:
    slug = _account_slug(account_id)
    return (
        f"https://{slug}.suitetalk.api.netsuite.com"
        "/services/rest/auth/oauth2/v1/token"
    )


def _rest_base(account_id: str) -> str:
    slug = _account_slug(account_id)
    return f"https://{slug}.suitetalk.api.netsuite.com/services/rest/record/v1"


async def _fetch_token(account_id: str, client_id: str, client_secret: str) -> str:
    """
    Fetch a fresh OAuth 2.0 Bearer token using client_credentials grant.
    Caches the token until 60 seconds before expiry.
    """
    now = time.time()
    if _cache.access_token and now < _cache.expires_at:
        return _cache.access_token

    scope = os.getenv("NETSUITE_TOKEN_SCOPE", "rest_webservices")
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            _token_url(account_id),
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": scope,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if resp.status_code != 200:
        raise RuntimeError(
            f"NetSuite token request failed {resp.status_code}: {resp.text[:300]}"
        )

    body = resp.json()
    _cache.access_token = body["access_token"]
    # expires_in is in seconds; subtract 60s buffer
    _cache.expires_at = now + int(body.get("expires_in", 3600)) - 60
    log.info("NetSuite: OAuth token refreshed, expires in %ds", body.get("expires_in", 3600))
    return _cache.access_token


# ── Connector ─────────────────────────────────────────────────────────────────

class NetSuiteConnector(BaseERPConnector):
    """
    Production NetSuite REST connector.

    authenticate()     — validates credentials by fetching a live token.
    fetch_orders()     — GET /salesOrder?q=status IS "Pending Fulfillment"
    fetch_inventory()  — GET /inventoryItem (page 1, up to 1000 items)
    execute_action()   — PATCH /salesOrder/{internal_id} (REROUTE / EXPEDITE / CANCEL)
    """

    def __init__(self) -> None:
        # Lazy-load so the app starts even if vars are missing (until connector is used)
        self._account_id: Optional[str] = None
        self._client_id: Optional[str] = None
        self._client_secret: Optional[str] = None

    def _load_creds(self) -> None:
        if self._account_id:
            return
        self._account_id = _require_env("NETSUITE_ACCOUNT_ID")
        self._client_id = _require_env("NETSUITE_CLIENT_ID")
        self._client_secret = _require_env("NETSUITE_CLIENT_SECRET")

    # BaseERPConnector.authenticate is synchronous; we validate by doing a
    # blocking token fetch via asyncio.run (only called from non-async contexts).
    def authenticate(self) -> bool:
        self._load_creds()
        try:
            asyncio.run(_fetch_token(self._account_id, self._client_id, self._client_secret))
            log.info("NetSuite: authentication successful for account %s", self._account_id)
            return True
        except Exception as exc:
            log.error("NetSuite: authentication failed — %s", exc)
            return False

    async def _headers(self) -> Dict[str, str]:
        self._load_creds()
        token = await _fetch_token(self._account_id, self._client_id, self._client_secret)
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Prefer": "transient",
        }

    def fetch_orders(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Sync wrapper — runs the async fetch in a new event loop."""
        return asyncio.run(self._async_fetch_orders(tenant_id))

    async def _async_fetch_orders(self, tenant_id: str) -> List[Dict[str, Any]]:
        self._load_creds()
        headers = await self._headers()
        base = _rest_base(self._account_id)
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                f"{base}/salesOrder",
                headers=headers,
                params={"limit": 100, "offset": 0},
            )
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            log.info("NetSuite: fetched %d sales orders for %s", len(items), tenant_id)
            return items
        log.warning("NetSuite fetch_orders %s: %s", resp.status_code, resp.text[:200])
        return []

    def fetch_inventory(self, tenant_id: str) -> List[Dict[str, Any]]:
        return asyncio.run(self._async_fetch_inventory(tenant_id))

    async def _async_fetch_inventory(self, tenant_id: str) -> List[Dict[str, Any]]:
        self._load_creds()
        headers = await self._headers()
        base = _rest_base(self._account_id)
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                f"{base}/inventoryItem",
                headers=headers,
                params={"limit": 1000, "offset": 0},
            )
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            log.info("NetSuite: fetched %d inventory items for %s", len(items), tenant_id)
            return items
        log.warning("NetSuite fetch_inventory %s: %s", resp.status_code, resp.text[:200])
        return []

    async def execute_action(self, tenant_id: str, action_type: str, payload: dict) -> dict:
        """
        Write-back to NetSuite via PATCH on salesOrder.
        payload must contain 'internal_id' (NetSuite record ID) plus action fields.

        action_type:
          REROUTE   — updates ship-from / carrier on the SO line
          EXPEDITE  — sets expedite flag and adjusts ship date
          CANCEL    — sets transtatus to "Cancelled"
        """
        self._load_creds()
        headers = await self._headers()
        base = _rest_base(self._account_id)

        internal_id = payload.get("internal_id") or payload.get("shipment_id")
        if not internal_id:
            raise ValueError("execute_action: 'internal_id' is required in payload")

        patch_body = _build_patch_body(action_type, payload)

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.patch(
                f"{base}/salesOrder/{internal_id}",
                headers=headers,
                json=patch_body,
            )

        if resp.status_code in (200, 204):
            log.info("NetSuite: %s on SO %s succeeded (tenant=%s)", action_type, internal_id, tenant_id)
            return {
                "status": "success",
                "erp_system": "Oracle NetSuite",
                "transaction_id": f"NS-{internal_id}-{action_type}",
                "action_type": action_type,
                "http_status": resp.status_code,
            }

        # Non-2xx — surface the error but don't crash the caller
        error_body = resp.text[:500]
        log.error("NetSuite execute_action failed %s: %s", resp.status_code, error_body)
        return {
            "status": "error",
            "erp_system": "Oracle NetSuite",
            "http_status": resp.status_code,
            "detail": error_body,
        }


# ── Patch body builders ───────────────────────────────────────────────────────

def _build_patch_body(action_type: str, payload: dict) -> dict:
    if action_type == "REROUTE":
        body: dict = {}
        if "carrier" in payload:
            body["shipMethod"] = {"refName": payload["carrier"]}
        if "new_origin" in payload:
            body["shipAddressLine1"] = payload["new_origin"]
        return body

    if action_type == "EXPEDITE":
        import datetime
        body = {"expedite": True}
        if "new_ship_date" in payload:
            body["shipDate"] = payload["new_ship_date"]
        else:
            body["shipDate"] = (
                datetime.datetime.utcnow() + datetime.timedelta(days=1)
            ).strftime("%Y-%m-%d")
        return body

    if action_type == "CANCEL":
        return {"transtatus": {"refName": "Cancelled"}}

    # Generic fallback — pass payload fields directly
    return {k: v for k, v in payload.items() if k not in ("internal_id", "auth_token")}
