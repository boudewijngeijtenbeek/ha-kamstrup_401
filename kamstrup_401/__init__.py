"""
Custom integration to integrate kamstrup_401 with Home Assistant.

For more details about this integration, please refer to
...
"""
import asyncio
from datetime import timedelta
import logging
from typing import Any, List

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PORT, CONF_SCAN_INTERVAL, CONF_TIMEOUT
from homeassistant.core import Config, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import serial

from .const import (
    DEFAULT_BAUDRATE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
    NAME,
    PLATFORMS,
    VERSION,
)
from .kamstrup import Kamstrup

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup(_hass: HomeAssistant, _config: Config) -> bool:
    """Set up this integration using YAML is not supported."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})

    port = entry.data.get(CONF_PORT)
    scan_interval_seconds = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    scan_interval = timedelta(seconds=scan_interval_seconds)
    timeout_seconds = entry.options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
    
    _LOGGER.debug(
        "Set up entry from %s (baudrate: %s) with scan_interval of %s seconds and timeout of %s seconds",
        port,
        DEFAULT_BAUDRATE,
        scan_interval_seconds,
        timeout_seconds,
    )

    client = Kamstrup(port, DEFAULT_BAUDRATE, timeout_seconds)

    device_info = DeviceInfo(
        entry_type=DeviceEntryType.SERVICE,
        identifiers={(DOMAIN, port)},
        manufacturer=NAME,
        name=NAME,
        model=VERSION,
    )

    coordinator = KamstrupUpdateCoordinator(
        hass=hass, client=client, scan_interval=scan_interval, device_info=device_info
    )

    hass.data[DOMAIN][entry.entry_id] = coordinator

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    for platform in PLATFORMS:
        if entry.options.get(platform, True):
            await hass.async_add_job(
                hass.config_entries.async_forward_entry_setup(entry, platform)
            )

    await coordinator.async_config_entry_first_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload this config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        del hass.data[DOMAIN][entry.entry_id]
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


class KamstrupUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Kamstrup serial reader."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: Kamstrup,
        scan_interval: int,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize."""
        self.kamstrup = client
        self.device_info = device_info

        self._commands: List[str] = []

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=scan_interval)

    def register_command(self, command: str) -> None:
        """Add a command to the commands list."""
        _LOGGER.debug("Register command %s", command)
        self._commands.append(command)

    def unregister_command(self, command: str) -> None:
        """Remove a command from the commands list."""
        _LOGGER.debug("Unregister command %s", command)
        self._commands.remove(command)

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        _LOGGER.debug("Start update")

        data = {}
        failed_counter = 0

        try:
            heatEnergy, volume, hoursCounter = self.kamstrup.readMeter()
            
            for command in self._commands:
                if command == "6.8":
                    data[command] = {"value": heatEnergy, "unit": "GJ"}
                    _LOGGER.debug("New value for sensor %s (Heat Energy), value: %s GJ", command, str(heatEnergy))
                    if heatEnergy is None:
                        failed_counter += 1
                if command == "6.26":
                    data[command] = {"value": volume, "unit": "m³"}
                    _LOGGER.debug("New value for sensor %s (Volume), value: %s m³", command, str(volume))
                    if volume is None:
                        failed_counter += 1
                if command == "6.31":
                    data[command] = {"value": hoursCounter, "unit": "h"}
                    _LOGGER.debug("New value for sensor %s (Hours Counter), value: %s h", command, str(hoursCounter))
                    if hoursCounter is None:
                        failed_counter += 1
                        
            await asyncio.sleep(1)
                
        except (serial.SerialException) as exception:
            _LOGGER.error("Device disconnected or multiple access on port? \nException: %e", exception)
        except (Exception) as exception:
            _LOGGER.error("Error updating sensors \nException: %s", exception)
            raise UpdateFailed() from exception

        if failed_counter == len(data):
            _LOGGER.error(
                "Finished update, No readings from the meter. Please check the IR connection"
            )
        else:
            _LOGGER.debug(
                "Finished update, %s/%s readings failed", failed_counter, len(data)
            )

        return data
