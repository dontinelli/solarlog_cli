"""Connector class to manage access to Solar-Log."""

from datetime import datetime, timezone, tzinfo
import logging
from zoneinfo import ZoneInfo

from .solarlog_client import Client
from .solarlog_exceptions import SolarLogUpdateError
from .solarlog_models import SolarlogData, InverterData

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

        self.timezone: tzinfo = timezone.utc if tz == "" else ZoneInfo(tz)

    async def test_connection(self) -> bool:
        """Test if connection to Solar-Log works."""

        return await self.client.test_connection()

    async def update_data(self) -> SolarlogData:
        """Get data from Solar-Log."""

        data: SolarlogData = await self.client.get_basic_data()

        if data.last_updated.year == 1999:
            raise SolarLogUpdateError(
                "Invalid data returned (can happen after Solarlog restart)."
            )

        data.last_updated = data.last_updated.replace(tzinfo=self.timezone)

        _LOGGER.debug("Basic data updated: %s",data)
        if self.extended_data:
            data = await self.client.get_energy(data)

            if self._device_enabled != {} and self._device_enabled is not None:
                data.inverter_data = await self.update_inverter_data()

            _LOGGER.debug("Extended data updated: %s",data)

        #calculated values (for downward compatibility)
        data.alternator_loss = data.power_dc - data.power_ac
        if data.power_dc != 0:
            data.efficiency = data.power_ac / data.power_dc
        if data.power_ac != 0:
            data.usage = data.consumption_ac / data.power_ac
            data.power_available = data.power_ac - data.consumption_ac
        else:
            data.usage = 0.0
            data.power_available = 0.0
        if data.total_power != 0:
            data.capacity = data.power_dc / data.total_power

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

    async def update_inverter_data(self) -> dict[int, InverterData]:
        """Update device specific data."""
        data: dict[int, InverterData] = {}
        raw_data = await self.client.get_power_per_inverter()
        for key, value in raw_data.items():
            key = int(key)
            if self._device_enabled.get(key, False):
                data |= {key: InverterData(current_power = float(value))}

        raw_data = await self.client.get_energy_per_inverter()
        for key, value in raw_data.items():
            print (raw_data.items())
            print (self._device_enabled)
            if self._device_enabled[key]:
                if key in data:
                    data[key].consumption_year = float(value)
                else:
                    data |= {key: InverterData(consumption_year = float(value))}
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

    def device_enabled(self, device_id: int | None = None) -> bool | dict[int, bool]:
        """Status of inverter."""
        if device_id is None:
            return self._device_enabled
        return self._device_enabled[device_id]

    def set_enabled_devices(self, device_enabled: dict[int, bool]) -> None:
        """Set enabled devices."""
        self._device_enabled = device_enabled
