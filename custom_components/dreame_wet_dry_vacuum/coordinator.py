"""Data coordinator for Dreame wet & dry vacuum (MQTT push + HTTP seed)."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DreameAPI, DreameAPIError
from .const import (
    CONSUMABLE_MAX_KEYS,
    DOMAIN,
    KNOWN_BINARY_PROPS,
    KNOWN_MQTT_PROPS,
    KNOWN_NUMBER_PROPS,
    KNOWN_SELECT_PROPS,
    KNOWN_SWITCH_PROPS,
    MQTT_ONLY_KEYS,
    STATUS_GROUP,
)
from .dreame_mqtt import DreameMqttClient

# All "siid.piid" keys worth polling from the cloud status endpoint.
# MQTT_ONLY_KEYS (fast-changing progress) are excluded: they're driven by the
# real-time MQTT push, and a coarse 5-min poll would make them jump around.
_POLL_KEYS: list[str] = sorted(
    {f"{s}.{p}" for s, p in (
        set(KNOWN_MQTT_PROPS)
        | set(KNOWN_BINARY_PROPS)
        | set(KNOWN_SWITCH_PROPS)
        | set(KNOWN_NUMBER_PROPS)
        | set(KNOWN_SELECT_PROPS)
    ) - MQTT_ONLY_KEYS}
    | set(CONSUMABLE_MAX_KEYS)
)

_LOGGER = logging.getLogger(__name__)

# Safety-net HTTP refresh interval (MQTT is the primary, real-time source)
HTTP_REFRESH = timedelta(minutes=5)


class DreameWetDryCoordinator(DataUpdateCoordinator):
    """Holds live device state. Primary feed is MQTT push; HTTP snapshot seeds
    battery/status and acts as a periodic safety net."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: DreameAPI,
        device_id: str,
        device_info: dict[str, Any],
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{device_id}",
            update_interval=HTTP_REFRESH,
        )
        self.api = api
        self.device_id = device_id
        self.device_info_raw = device_info
        # Live property store keyed by (siid, piid)
        self.props: dict[tuple[int, int], Any] = {}
        # Callback set by the sensor platform to add entities for new props
        self.new_prop_callback = None
        self.mqtt: DreameMqttClient | None = None

    def start_mqtt(self) -> None:
        """Create and start the MQTT client."""
        snap = self.device_info_raw
        bind = snap.get("bindDomain") or snap.get("bind_domain")
        if not bind:
            _LOGGER.warning("No bindDomain; MQTT disabled, HTTP polling only")
            return
        self.mqtt = DreameMqttClient(
            uid=self.api._uid,
            access_token=self.api._access_token,
            device_id=self.device_id,
            model=snap.get("model", ""),
            bind_domain=bind,
            on_update=self._handle_mqtt_update,
        )
        self.mqtt.start()

    async def async_set_prop(self, siid: int, piid: int, value: Any) -> bool:
        """Write a property to the device, then optimistically update state."""
        ok = await self.api.set_property(self.device_id, siid, piid, value)
        if ok:
            self.props[(siid, piid)] = value
            self.async_set_updated_data(self._build_data())
        else:
            _LOGGER.warning("set_property %s.%s=%s rejected by device", siid, piid, value)
        return ok

    def _handle_mqtt_update(self, state: dict[tuple[int, int], Any]) -> None:
        """Called from the MQTT thread when properties change."""
        new_keys = set(state) - set(self.props)
        self.props.update(state)
        # Bridge to the HA event loop
        self.hass.loop.call_soon_threadsafe(self._publish, new_keys)

    def _publish(self, new_keys: set[tuple[int, int]]) -> None:
        if new_keys and self.new_prop_callback:
            self.new_prop_callback(new_keys)
        self.async_set_updated_data(self._build_data())

    def _build_data(self) -> dict[str, Any]:
        """Flatten props + snapshot into a name->value dict for entities."""
        data: dict[str, Any] = {f"{s}.{p}": v for (s, p), v in self.props.items()}
        # status_group from the main status property (2.1) if present
        status = self.props.get((2, 1))
        if status is not None:
            data["status_group"] = STATUS_GROUP.get(int(status), "unknown")
        return data

    async def _async_update_data(self) -> dict[str, Any]:
        """HTTP safety-net refresh: seed battery + status from the snapshot."""
        try:
            snapshot = await self.api.get_device_snapshot(self.device_id)
        except DreameAPIError as err:
            # If MQTT is alive we can tolerate HTTP errors
            if self.props:
                return self._build_data()
            raise UpdateFailed(f"Dreame API error: {err}") from err

        if snapshot:
            if snapshot.get("battery") is not None and (3, 1) not in self.props:
                self.props[(3, 1)] = snapshot["battery"]
            if snapshot.get("status") is not None and (2, 1) not in self.props:
                self.props[(2, 1)] = snapshot["status"]
            # Refresh MQTT token if it rotated
            if self.mqtt:
                self.mqtt.update_token(self.api._access_token)

        # Read cloud-cached property values (warn/error, consumables, settings…).
        # This is what makes alerts like "dirty tank full" reliable even when MQTT
        # missed the push (e.g. HA started after the event fired).
        try:
            values = await self.api.get_status_props(self.device_id, _POLL_KEYS)
            for key, value in values.items():
                s, _, p = key.partition(".")
                self.props[(int(s), int(p))] = value
        except (DreameAPIError, ValueError) as err:
            _LOGGER.debug("status_props poll failed (non-fatal): %s", err)

        return self._build_data()
