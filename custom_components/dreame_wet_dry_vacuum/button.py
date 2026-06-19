"""Button platform for Dreame wet & dry vacuum (one-shot commands)."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DreameWetDryConfigEntry
from .const import KNOWN_BUTTON_PROPS
from .entity import DreameWetDryEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DreameWetDryConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        DreameWetDryButton(coordinator, key, meta)
        for key, meta in KNOWN_BUTTON_PROPS.items()
    )


class DreameWetDryButton(DreameWetDryEntity, ButtonEntity):
    """Sends a fixed value to a property when pressed."""

    def __init__(self, coordinator, key, meta) -> None:
        super().__init__(coordinator, key, meta)
        self._press_value = meta.get("press_value", 1)

    async def async_press(self) -> None:
        await self._set(self._press_value)
