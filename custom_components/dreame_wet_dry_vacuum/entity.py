"""Shared base entity for Dreame wet & dry vacuum controls."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import DreameWetDryCoordinator


class DreameWetDryEntity(CoordinatorEntity[DreameWetDryCoordinator]):
    """Base entity bound to one (siid, piid) property."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: DreameWetDryCoordinator, key: tuple[int, int], meta: dict) -> None:
        super().__init__(coordinator)
        self._key = key
        self._siid, self._piid = key
        self._data_key = f"{key[0]}.{key[1]}"
        self._meta = meta
        self._attr_unique_id = f"{coordinator.device_id}_{meta['key']}"
        self._attr_name = meta.get("name")
        self._attr_icon = meta.get("icon")

        snap = coordinator.device_info_raw
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.device_id)},
            "name": snap.get("name")
            or snap.get("deviceInfo", {}).get("displayName")
            or "Dreame Wet & Dry Vacuum",
            "manufacturer": MANUFACTURER,
            "model": snap.get("model", MODEL),
            "sw_version": snap.get("ver") or snap.get("firmware"),
        }

    @property
    def _raw(self) -> Any:
        return self.coordinator.data.get(self._data_key)

    async def _set(self, value: Any) -> bool:
        return await self.coordinator.async_set_prop(self._siid, self._piid, value)
