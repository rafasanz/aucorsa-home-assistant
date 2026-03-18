import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigEntry
from homeassistant.core import callback

try:
    from homeassistant.config_entries import OptionsFlowWithReload
except ImportError:
    from homeassistant.config_entries import OptionsFlow

    class OptionsFlowWithReload(OptionsFlow):
        """Compatibility fallback for older Home Assistant versions."""


_LOGGER = logging.getLogger(__name__)

try:
    from .const import (
        CONF_INTERNAL_LINE_ID,
        CONF_LINE,
        CONF_SCAN_INTERVAL_SECONDS,
        CONF_STOP_ID,
        DEFAULT_SCAN_INTERVAL_SECONDS,
        DOMAIN,
        MAX_SCAN_INTERVAL_SECONDS,
        MIN_SCAN_INTERVAL_SECONDS,
    )
except Exception:
    _LOGGER.exception("AUCORSA: error importing const.py in config flow; using local fallbacks")
    DOMAIN = "aucorsa"
    CONF_LINE = "line"
    CONF_STOP_ID = "stop_id"
    CONF_INTERNAL_LINE_ID = "internal_line_id"
    CONF_SCAN_INTERVAL_SECONDS = "scan_interval_seconds"
    DEFAULT_SCAN_INTERVAL_SECONDS = 60
    MIN_SCAN_INTERVAL_SECONDS = 30
    MAX_SCAN_INTERVAL_SECONDS = 300


def _user_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_LINE): str,
            vol.Required(CONF_STOP_ID): str,
            vol.Required(
                CONF_SCAN_INTERVAL_SECONDS,
                default=DEFAULT_SCAN_INTERVAL_SECONDS,
            ): vol.All(
                int,
                vol.Range(min=MIN_SCAN_INTERVAL_SECONDS, max=MAX_SCAN_INTERVAL_SECONDS),
            ),
        }
    )


def _options_schema(default_scan_interval: int) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_SCAN_INTERVAL_SECONDS,
                default=default_scan_interval,
            ): vol.All(
                int,
                vol.Range(min=MIN_SCAN_INTERVAL_SECONDS, max=MAX_SCAN_INTERVAL_SECONDS),
            ),
        }
    )


async def _validate_input(hass, user_input: dict[str, Any]) -> dict[str, Any]:
    from homeassistant.helpers.aiohttp_client import async_get_clientsession
    from .api import AucorsaApi

    line = str(user_input[CONF_LINE]).strip()
    stop_id = str(user_input[CONF_STOP_ID]).strip()
    scan_interval_seconds = int(user_input[CONF_SCAN_INTERVAL_SECONDS])

    if not line or not stop_id or not stop_id.isdigit():
        raise ValueError("invalid_stop")

    api = AucorsaApi(async_get_clientsession(hass))
    result = await api.estimate(visible_line=line, stop_id=stop_id)

    if result.stop_label is None:
        raise ValueError("invalid_stop")

    if result.route is None:
        raise ValueError("line_not_available_for_stop")

    return {
        CONF_LINE: result.line,
        CONF_STOP_ID: result.stop_id,
        CONF_INTERNAL_LINE_ID: result.internal_line_id,
        CONF_SCAN_INTERVAL_SECONDS: scan_interval_seconds,
    }


class AucorsaConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowWithReload:
        return AucorsaOptionsFlow(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await _validate_input(self.hass, user_input)
                await self.async_set_unique_id(f"{info[CONF_LINE].upper()}:{info[CONF_STOP_ID]}")
                self._abort_if_unique_id_configured()
            except LookupError:
                errors["base"] = "invalid_line"
            except ValueError as exc:
                if str(exc) == "line_not_available_for_stop":
                    errors["base"] = "invalid_stop"
                else:
                    errors["base"] = "invalid_stop"
            except Exception:
                _LOGGER.exception("Unexpected error while validating AUCORSA config")
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"{info[CONF_LINE]} / {info[CONF_STOP_ID]}",
                    data={
                        CONF_LINE: info[CONF_LINE],
                        CONF_STOP_ID: info[CONF_STOP_ID],
                        CONF_INTERNAL_LINE_ID: info[CONF_INTERNAL_LINE_ID],
                    },
                    options={
                        CONF_SCAN_INTERVAL_SECONDS: info[CONF_SCAN_INTERVAL_SECONDS],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(_user_schema(), user_input or {}),
            errors=errors,
        )


class AucorsaOptionsFlow(OptionsFlowWithReload):
    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current_scan_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL_SECONDS,
            DEFAULT_SCAN_INTERVAL_SECONDS,
        )
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                _options_schema(current_scan_interval),
                self.config_entry.options,
            ),
        )
