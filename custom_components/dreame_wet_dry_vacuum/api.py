"""Dreame Home cloud API client."""
from __future__ import annotations

import hashlib
import json
import logging
import random
import string
import time
from typing import Any

import aiohttp
from Crypto.Cipher import AES

from .const import (
    DREAME_BASIC_AUTH,
    DREAME_IOT_PREFIX,
    DREAME_PASSWORD_SALT,
    DREAME_RLC_KEY,
    DREAME_RLC_PLAIN,
    DREAME_TENANT_ID,
    ENDPOINTS,
    EU_BASE_URL,
    CN_BASE_URL,
)

_LOGGER = logging.getLogger(__name__)

REGION_URLS = {
    "eu": EU_BASE_URL,
    "cn": CN_BASE_URL,
}


def _md5_password(password: str) -> str:
    return hashlib.md5((password + DREAME_PASSWORD_SALT).encode()).hexdigest()


def _parse_prop_value(value: Any) -> Any:
    """Parse an iotstatus value (returned as a string) to a native type.

    "0" -> 0, "[81]" -> [81], "abc" -> "abc". Keeps types consistent with the
    MQTT feed, which delivers ints/lists natively.
    """
    if not isinstance(value, str):
        return value
    s = value.strip()
    if s and (s[0] in "[-" or s.isdigit()):
        try:
            return json.loads(s)
        except (ValueError, TypeError):
            pass
    return value


def _compute_rlc(region: str = "eu") -> str:
    """Generate the dreame-rlc header value via AES-128-ECB."""
    plain = f"{region}|en|DE"
    key = DREAME_RLC_KEY
    cipher = AES.new(key, AES.MODE_ECB)
    # Pad to 16-byte block
    pad_len = 16 - (len(plain) % 16)
    plain_padded = plain + chr(pad_len) * pad_len
    encrypted = cipher.encrypt(plain_padded.encode("utf-8"))
    return encrypted.hex()


def _random_request_id() -> str:
    return "".join(random.choices(string.digits, k=8))


class DreameAPIError(Exception):
    pass


class DreameAuthError(DreameAPIError):
    pass


class DreameAPI:
    """Client for the Dreame Home cloud API."""

    def __init__(self, username: str, password: str, region: str = "eu") -> None:
        self._username = username
        self._password = password
        self._region = region
        self._base_url = REGION_URLS.get(region, EU_BASE_URL)
        self._access_token: str | None = None
        self._uid: str | None = None
        self._session: aiohttp.ClientSession | None = None
        self._rlc = _compute_rlc(region)

    def _get_base_headers(self) -> dict[str, str]:
        return {
            "user-agent": "Dart/3.2 (dart:io)",
            "dreame-meta": "cv=i_829",
            "dreame-rlc": self._rlc,
            "tenant-id": DREAME_TENANT_ID,
            "host": self._base_url.split("//")[1],
        }

    def _get_auth_headers(self) -> dict[str, str]:
        headers = self._get_base_headers()
        headers["dreame-auth"] = f"bearer {self._access_token}"
        headers["content-type"] = "application/json"
        return headers

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def login(self) -> None:
        """Authenticate and store access token."""
        session = await self._get_session()
        url = self._base_url + ENDPOINTS["token"]

        headers = self._get_base_headers()
        headers["authorization"] = DREAME_BASIC_AUTH
        headers["content-type"] = "application/x-www-form-urlencoded"

        data = {
            "grant_type": "password",
            "scope": "all",
            "platform": "IOS",
            "type": "account",
            "username": self._username,
            "password": _md5_password(self._password),
            "country": "DE",
            "lang": "en",
        }

        try:
            async with session.post(url, headers=headers, data=data, ssl=False) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise DreameAuthError(f"Login failed ({resp.status}): {text}")
                result = await resp.json(content_type=None)
        except DreameAuthError:
            raise
        except Exception as err:
            raise DreameAPIError(f"Login request failed: {err}") from err

        if "access_token" not in result:
            raise DreameAuthError(f"No access_token in response: {result}")

        self._access_token = result["access_token"]
        self._uid = result.get("uid")
        _LOGGER.debug("Dreame login successful, uid=%s", self._uid)

    async def get_devices(self) -> list[dict[str, Any]]:
        """Return list of devices bound to the account."""
        await self._ensure_logged_in()
        session = await self._get_session()
        url = self._base_url + ENDPOINTS["device_list"]

        payload = {
            "sharedStatus": 1,
            "current": 1,
            "size": 100,
            "lang": "en",
            "timestamp": int(time.time() * 1000),
        }

        try:
            async with session.post(
                url, headers=self._get_auth_headers(), json=payload, ssl=False
            ) as resp:
                if resp.status == 401:
                    await self.login()
                    return await self.get_devices()
                result = await resp.json(content_type=None)
        except Exception as err:
            raise DreameAPIError(f"get_devices failed: {err}") from err

        data = result.get("data", {})
        # Dreame nests the list under data.page.records
        records = data.get("page", {}).get("records", [])
        if not records:
            records = data.get("records", [])
        return records

    async def get_device_snapshot(self, device_id: str) -> dict[str, Any]:
        """
        Return the cloud-cached state for a device (battery, status, online).
        This always works, even when the vacuum is docked/asleep, because it
        reads the last state the device reported to the cloud.
        """
        devices = await self.get_devices()
        for d in devices:
            if str(d.get("did")) == str(device_id):
                return {
                    "battery": d.get("battery"),
                    "status": d.get("latestStatus"),
                    "online": d.get("online"),
                    "model": d.get("model"),
                    "name": d.get("deviceInfo", {}).get("displayName")
                    or d.get("customName")
                    or d.get("model"),
                    "firmware": d.get("ver"),
                    "mac": d.get("mac"),
                }
        return {}

    async def get_status_props(
        self, device_id: str, keys: list[str]
    ) -> dict[str, Any]:
        """
        Read cloud-cached property values by key ("siid.piid").
        Uses /dreame-user-iot/iotstatus/props, which works on this model (unlike
        the realtime get_properties RPC that returns null). Returns {key: value}
        with values parsed to native types (int / list), keys never reported are
        simply absent.
        """
        await self._ensure_logged_in()
        session = await self._get_session()
        url = self._base_url + ENDPOINTS["status_props"]
        # The endpoint expects keys as a single comma-separated string.
        payload = {"did": device_id, "keys": ",".join(keys)}

        try:
            async with session.post(
                url, headers=self._get_auth_headers(), json=payload, ssl=False
            ) as resp:
                if resp.status == 401:
                    await self.login()
                    return await self.get_status_props(device_id, keys)
                result = await resp.json(content_type=None)
        except Exception as err:
            raise DreameAPIError(f"get_status_props failed: {err}") from err

        out: dict[str, Any] = {}
        for item in result.get("data") or []:
            key = item.get("key")
            if key is None or "value" not in item:
                continue
            out[key] = _parse_prop_value(item["value"])
        return out

    async def get_properties(
        self, device_id: str, props: list[dict[str, int]]
    ) -> list[dict[str, Any]]:
        """
        Fetch device properties.
        props: list of {siid, piid} dicts
        Returns list of {siid, piid, value, code} dicts.
        """
        await self._ensure_logged_in()
        session = await self._get_session()
        url = self._base_url + ENDPOINTS["send_command"].format(prefix=DREAME_IOT_PREFIX)

        req_id = _random_request_id()
        params = [
            {"siid": p["siid"], "piid": p["piid"], "code": 0, "updateTime": 0}
            for p in props
        ]

        payload = {
            "did": device_id,
            "id": req_id,
            "data": {
                "did": device_id,
                "id": req_id,
                "method": "get_properties",
                "params": params,
                "from": "100000",
            },
        }

        try:
            async with session.post(
                url, headers=self._get_auth_headers(), json=payload, ssl=False
            ) as resp:
                if resp.status == 401:
                    await self.login()
                    return await self.get_properties(device_id, props)
                result = await resp.json(content_type=None)
        except Exception as err:
            raise DreameAPIError(f"get_properties failed: {err}") from err

        return result.get("data", {}).get("result", [])

    async def set_property(
        self, device_id: str, siid: int, piid: int, value: Any
    ) -> bool:
        """Set a single device property."""
        await self._ensure_logged_in()
        session = await self._get_session()
        url = self._base_url + ENDPOINTS["send_command"].format(prefix=DREAME_IOT_PREFIX)

        req_id = _random_request_id()
        payload = {
            "did": device_id,
            "id": req_id,
            "data": {
                "did": device_id,
                "id": req_id,
                "method": "set_properties",
                "params": [{"siid": siid, "piid": piid, "value": value}],
                "from": "100000",
            },
        }

        try:
            async with session.post(
                url, headers=self._get_auth_headers(), json=payload, ssl=False
            ) as resp:
                if resp.status == 401:
                    await self.login()
                    return await self.set_property(device_id, siid, piid, value)
                result = await resp.json(content_type=None)
        except Exception as err:
            raise DreameAPIError(f"set_property failed: {err}") from err

        results = result.get("data", {}).get("result", [])
        return all(r.get("code", -1) == 0 for r in results)

    async def call_action(
        self, device_id: str, siid: int, aiid: int, params: list | None = None
    ) -> bool:
        """Call a device action."""
        await self._ensure_logged_in()
        session = await self._get_session()
        url = self._base_url + ENDPOINTS["send_command"].format(prefix=DREAME_IOT_PREFIX)

        req_id = _random_request_id()
        payload = {
            "did": device_id,
            "id": req_id,
            "data": {
                "did": device_id,
                "id": req_id,
                "method": "action",
                "params": {
                    "siid": siid,
                    "aiid": aiid,
                    "did": device_id,
                    "in": params or [],
                },
                "from": "100000",
            },
        }

        try:
            async with session.post(
                url, headers=self._get_auth_headers(), json=payload, ssl=False
            ) as resp:
                if resp.status == 401:
                    await self.login()
                    return await self.call_action(device_id, siid, aiid, params)
                result = await resp.json(content_type=None)
        except Exception as err:
            raise DreameAPIError(f"call_action failed: {err}") from err

        return result.get("data", {}).get("code", -1) == 0

    async def discover_properties(
        self, device_id: str, siid_range: range = range(1, 11), piid_range: range = range(1, 21)
    ) -> dict[tuple[int, int], Any]:
        """
        Probe all siid/piid combinations and return those that return valid values.
        Useful for discovering what a new device exposes.
        """
        all_props = [
            {"siid": s, "piid": p} for s in siid_range for p in piid_range
        ]
        # Chunk into groups of 50
        results: dict[tuple[int, int], Any] = {}
        chunk_size = 50
        for i in range(0, len(all_props), chunk_size):
            chunk = all_props[i : i + chunk_size]
            try:
                data = await self.get_properties(device_id, chunk)
                for item in data:
                    if item.get("code", -1) == 0:
                        key = (item["siid"], item["piid"])
                        results[key] = item.get("value")
            except Exception as err:
                _LOGGER.warning("Discovery chunk failed: %s", err)
        return results

    async def _ensure_logged_in(self) -> None:
        if self._access_token is None:
            await self.login()
