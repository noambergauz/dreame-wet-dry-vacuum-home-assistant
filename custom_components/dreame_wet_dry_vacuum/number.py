"""Number platform for Dreame wet & dry vacuum (writable numeric settings)."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DreameWetDryConfigEntry
from .const import KNOWN_NUMBER_PROPS
from .entity import DreameWetDryEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DreameWetDryConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        DreameWetDryNumber(coordinator, key, meta)
        for key, meta in KNOWN_NUMBER_PROPS.items()
    )


class DreameWetDryNumber(DreameWetDryEntity, NumberEntity):
    """A numeric device setting."""

    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator, key, meta) -> None:
        super().__init__(coordinator, key, meta)
        self._attr_native_min_value = meta.get("min", 0)
        self._attr_native_max_value = meta.get("max", 100)
        self._attr_native_step = meta.get("step", 1)
        if meta.get("unit"):
            self._attr_native_unit_of_measurement = meta["unit"]
        # Custom-mode tuning params are configuration, not main controls
        if key[0] == 16:
            self._attr_entity_category = EntityCategory.CONFIG

    @property
    def native_value(self) -> float | None:
        raw = self._raw
        if raw is None:
            return None
        try:
            return float(raw)
        except (ValueError, TypeError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        await self._set(int(value))
