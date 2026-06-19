"""Select platform for Dreame wet & dry vacuum (writable enum properties)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DreameWetDryConfigEntry
from .const import KNOWN_SELECT_PROPS
from .entity import DreameWetDryEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DreameWetDryConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        DreameWetDrySelect(coordinator, key, meta)
        for key, meta in KNOWN_SELECT_PROPS.items()
    )


class DreameWetDrySelect(DreameWetDryEntity, SelectEntity):
    """An enum device setting exposed as a dropdown."""

    def __init__(self, coordinator, key, meta) -> None:
        super().__init__(coordinator, key, meta)
        self._value_to_label: dict[int, str] = meta["options"]
        self._label_to_value = {v: k for k, v in self._value_to_label.items()}
        self._attr_options = list(self._value_to_label.values())

    @property
    def current_option(self) -> str | None:
        raw = self._raw
        if raw is None:
            return None
        try:
            return self._value_to_label.get(int(raw))
        except (ValueError, TypeError):
            return None

    async def async_select_option(self, option: str) -> None:
        value = self._label_to_value.get(option)
        if value is not None:
            await self._set(value)
