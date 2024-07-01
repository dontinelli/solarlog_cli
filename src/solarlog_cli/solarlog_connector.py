"""Connector class to manage access to Solar-Log."""

from datetime import datetime, timezone
import logging
from zoneinfo import ZoneInfo

from .solarlog_client import Client
from .solarlog_exceptions import SolarLogUpdateError

_LOGGER = logging.getLogger(__name__)


class SolarLogConnector:
    """Connector class to access Solar-Log."""

    def __init__(
        self,
        host: str,
        extended_data: bool = False,
        tz: str = "",
        device_enabled: dict[int, bool] | None = None,
    ):
        self.client = Client(host)
        self.extended_data: bool = extended_data
        self._device_enabled: dict[int, bool] | None = device_enabled
        self._device_list: dict[int, dict[str, str | bool]] = {}

        self.timezone: ZoneInfo = timezone.utc if tz == "" else ZoneInfo(tz)

    async def test_connection(self) -> bool:
        """Test if connection to Solar-Log works."""

        return await self.client.test_connection()

    async def update_data(self) -> dict[str, int | float | datetime]:
        """Get data from Solar-Log."""

        data: dict[str, int | float | datetime] = await self.client.get_basic_data()

        if data["last_updated"].year == 1999:
            raise SolarLogUpdateError(
                "Invalid data returned (can happen after Solarlog restart)."
            )

        data["last_updated"] = data["last_updated"].replace(tzinfo=self.timezone)

        _LOGGER.debug("Basic data updated: %s",data)
        if self.extended_data:
            data |= await self.client.get_energy()
            if self._device_enabled != {} and self._device_enabled is not None:
                data |= {"devices": await self.update_inverter_data()}
            _LOGGER.debug("Extended data updated: %s",data)

        #calculated values (for downward compatibility)
        data |= {"alternator_loss": data.get("power_dc") - data.get("power_ac")}
        if data.get("power_dc") != 0:
            data |= {"efficiency": data.get("power_ac") / data.get("power_dc")}
        if data.get("power_ac") != 0:
            data |= {"usage": data.get("consumption_ac") / data.get("power_ac")}
            data |= {"power_available": data.get("power_ac") - data.get("consumption_ac")}
        else:
            data |= {"usage": 0.0}
            data |= {"power_available": 0.0}
        if data.get("total_power") != 0:
            data |= {"capacity": data.get("power_dc") / data.get("total_power")}

        return data

    async def update_device_list(self) -> dict[int, dict[str, str | bool]]:
        """Update list of devices."""
        if not self.extended_data:
            return {}

        device_list = await self.client.get_device_list()

        for key, value in self._device_enabled.items():
            device_list[int(key)] |= {"enabled": value}
        _LOGGER.debug("Device list: %s",device_list)
        self._device_list = device_list

        return device_list

    async def update_inverter_data(self) -> dict[int, dict[str, float]]:
        """Update device specific data."""
        data: dict[int, dict[str, float]] = {}
        raw_data = await self.client.get_power_per_inverter()
        for key, value in raw_data.items():
            key = int(key)
            if self._device_enabled.get(key, False):
                data |= {key: {"current_power": float(value)}}

        raw_data = await self.client.get_energy_per_inverter()
        for key, value in raw_data.items():
            if self._device_enabled[key]:
                if key in data:
                    data[key].update({"consumption_year": float(value)})
                else:
                    data |= {key: {"consumption_year": float(value)}}
        _LOGGER.debug("Inverter data updated: %s",data)

        return data

    @property
    def host(self) -> str:
        """Host of Solar-Log."""
        return self.client.host

    @property
    def device_list(self) -> dict[int, dict[str, str | bool]]:
        """List of all devices of Solar-Log."""
        return self._device_list

    def device_name(self, device_id: int) -> str:
        """Get name of Solar-Log attached device."""
        _LOGGER.debug("Device list: %s; id: %s",self._device_list, device_id)
        if device_id in self._device_list:
            return self._device_list[device_id]["name"]

        return ""

    def device_enabled(self, device_id: int = None) -> bool | dict[int, bool]:
        """Status of inverter."""
        if device_id is None:
            return self._device_enabled
        return self._device_enabled[device_id]

    def set_enabled_devices(self, device_enabled: dict[int, bool]) -> None:
        """Set enabled devices."""
        self._device_enabled = device_enabled
