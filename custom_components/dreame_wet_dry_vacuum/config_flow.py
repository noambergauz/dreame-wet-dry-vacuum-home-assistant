"""Config flow for Dreame wet & dry vacuum."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from .api import DreameAPI, DreameAuthError, DreameAPIError
from .const import CONF_DEVICE_ID, CONF_REGION, DOMAIN, REGIONS

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_REGION, default="eu"): vol.In(REGIONS),
    }
)


class DreameWetDryConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Dreame wet & dry vacuum."""

    VERSION = 1

    def __init__(self) -> None:
        self._username: str = ""
        self._password: str = ""
        self._region: str = "eu"
        self._devices: list[dict] = []

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            self._username = user_input[CONF_USERNAME]
            self._password = user_input[CONF_PASSWORD]
            self._region = user_input[CONF_REGION]

            api = DreameAPI(self._username, self._password, self._region)
            try:
                await api.login()
                self._devices = await api.get_devices()
            except DreameAuthError:
                errors["base"] = "invalid_auth"
            except DreameAPIError:
                errors["base"] = "cannot_connect"
            finally:
                await api.close()

            if not errors:
                if len(self._devices) == 1:
                    device = self._devices[0]
                    return self._create_entry(device)
                elif len(self._devices) > 1:
                    return await self.async_step_device()
                else:
                    errors["base"] = "no_devices"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    async def async_step_device(self, user_input=None) -> FlowResult:
        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID]
            device = next((d for d in self._devices if d["did"] == device_id), None)
            if device:
                return self._create_entry(device)

        device_options = {d["did"]: f"{d.get('name', d['did'])} ({d.get('model', 'unknown')})" for d in self._devices}

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema(
                {vol.Required(CONF_DEVICE_ID): vol.In(device_options)}
            ),
        )

    def _create_entry(self, device: dict) -> FlowResult:
        unique_id = device["did"]
        self._async_abort_entries_match({CONF_DEVICE_ID: unique_id})

        return self.async_create_entry(
            title=device.get("name", f"Dreame Vacuum ({unique_id})"),
            data={
                CONF_USERNAME: self._username,
                CONF_PASSWORD: self._password,
                CONF_REGION: self._region,
                CONF_DEVICE_ID: unique_id,
                "device_model": device.get("model", ""),
                "device_name": device.get("name", "Dreame Wet & Dry Vacuum"),
            },
        )
