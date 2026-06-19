"""Dreame wet & dry vacuum integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api import DreameAPI, DreameAPIError
from .const import CONF_DEVICE_ID, CONF_REGION, DOMAIN
from .coordinator import DreameWetDryCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.BUTTON,
]

type DreameWetDryConfigEntry = ConfigEntry[DreameWetDryCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: DreameWetDryConfigEntry) -> bool:
    """Set up Dreame wet & dry vacuum from a config entry."""
    api = DreameAPI(
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        region=entry.data.get(CONF_REGION, "eu"),
    )

    try:
        await api.login()
        devices = await api.get_devices()
    except DreameAPIError as err:
        await api.close()
        raise ConfigEntryNotReady(f"Cannot connect to Dreame cloud: {err}") from err

    device_id = entry.data[CONF_DEVICE_ID]
    device_info = next((d for d in devices if d["did"] == device_id), {})

    coordinator = DreameWetDryCoordinator(hass, api, device_id, device_info)

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        await api.close()
        raise ConfigEntryNotReady(f"Initial data fetch failed: {err}") from err

    entry.runtime_data = coordinator

    # Start the real-time MQTT feed (runs in a background thread)
    coordinator.start_mqtt()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: DreameWetDryConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded and entry.runtime_data:
        if entry.runtime_data.mqtt:
            await hass.async_add_executor_job(entry.runtime_data.mqtt.stop)
        await entry.runtime_data.api.close()
    return unloaded


async def _async_update_listener(hass: HomeAssistant, entry: DreameWetDryConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
