"""Connector class to manage access to Solar-Log."""

from datetime import timezone, tzinfo
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

        self._device_list: dict[int, InverterData] = {}
        if device_enabled is None:
            device_enabled = {}

        for key, value in device_enabled.items():
            self._device_list |= {key: InverterData(enabled=value)}

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

            if self._device_list != {}:
                data.inverter_data = await self.update_inverter_data()

            _LOGGER.debug("Extended data updated: %s",data)

        #calculated values (for downward compatibility)
        data.alternator_loss = data.power_dc - data.power_ac
        if data.power_dc != 0:
            data.efficiency = round(data.power_ac / data.power_dc *100, 1)
        if data.power_ac != 0:
            data.usage = round(data.consumption_ac / data.power_ac * 100, 1)
            data.power_available = data.power_ac - data.consumption_ac
        else:
            data.usage = 0.0
            data.power_available = 0.0
        if data.total_power != 0:
            data.capacity = round(data.power_dc / data.total_power * 100, 1)

        return data

    async def update_device_list(self) -> dict[int, InverterData]:
        """Update list of devices."""
        if not self.extended_data:
            return {}

        devices = await self.client.get_device_list()

        self._device_list = {
            key: InverterData(name=value,enabled=self.device(key).enabled)
            for key, value in devices.items()
        }
        _LOGGER.debug("Device list: %s",self._device_list)

        return self._device_list

    async def update_inverter_data(self) -> dict[int, InverterData]:
        """Update device specific data."""

        raw_data = await self.client.get_power_per_inverter()
        for key, value in raw_data.items():
            key = int(key)
            if self._device_list.get(key,InverterData).enabled:
                self._device_list[key].current_power = float(value)

        raw_data = await self.client.get_energy_per_inverter()
        for key, value in raw_data.items():
            if self._device_list.get(key,InverterData).enabled:
                self._device_list[key].consumption_year = float(value)

        _LOGGER.debug("Inverter data updated: %s",self._device_list)

        return self._device_list

    @property
    def host(self) -> str:
        """Host of Solar-Log."""
        return self.client.host

    @property
    def device_list(self) -> dict[int, InverterData]:
        """List of all devices of Solar-Log."""
        return self._device_list

    def device(self, device_id: int) -> InverterData:
        """Get device data."""
        return self._device_list.get(device_id, InverterData())

    def device_name(self, device_id: int) -> str:
        """Get name of Solar-Log attached device."""
        _LOGGER.debug("Device list: %s; id: %s",self._device_list, device_id)

        return self._device_list.get(device_id, InverterData()).name

    def device_enabled(self, device_id: int | None = None) -> bool | dict[int, bool]:
        """Get if device is enabled (if id is provided) or list of all devices."""
        if device_id is None:
            print("no device_id")
            print(self._device_list)
            return {key: value.enabled for key, value in self._device_list.items()}
        return self._device_list[device_id].enabled

    def set_enabled_devices(self, device_enabled: dict[int, bool]) -> None:
        """Set enabled devices."""
        for key, value in device_enabled.items():
            if self._device_list.get(key) is None:
                self._device_list |= {key: InverterData(enabled=value)}
            else:
                self._device_list[key].enabled = value
