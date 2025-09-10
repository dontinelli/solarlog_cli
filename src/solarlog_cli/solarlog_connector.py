"""Connector class to manage access to Solar-Log."""

from datetime import timezone, tzinfo
import logging
from zoneinfo import ZoneInfo

from aiohttp import ClientSession

from .solarlog_client import Client
from .solarlog_exceptions import(
    SolarLogAuthenticationError,
    SolarLogConnectionError,
    SolarLogUpdateError,
)
from .solarlog_models import BatteryData, InverterData, SolarlogData

_LOGGER = logging.getLogger(__name__)


class SolarLogConnector:
    """Connector class to access Solar-Log."""

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-positional-arguments

    def __init__(
        self,
        host: str,
        extended_data: bool = False,
        tz: str = "",
        device_enabled: dict[int, bool] | None = None,
        password: str = "",
        session: ClientSession | None = None,
    ):
        self.client = Client(host, session, password)
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

    async def test_extended_data_available(self) -> bool:
        """Test if extended data is reachable."""

        _LOGGER.debug("Start testing extended data available")

        try:
            await self.client.parse_http_response(
                await self.client.execute_http_request('{"740": null}')
            )
        except (SolarLogConnectionError, SolarLogUpdateError) as err:
            _LOGGER.debug("Error: %s", err)
            return False
        except SolarLogAuthenticationError as err:
            #User has no unprotected access to extended API, try to log in
            #(login returns false, if no pwd is set)
            _LOGGER.debug("Auth error during test for extended data: %s", err)
            try:
                self.extended_data = await self.login()
            except SolarLogAuthenticationError as error:
                _LOGGER.debug("Auth error during login in test for extended data: %s", err)
                raise SolarLogAuthenticationError from error
            _LOGGER.debug("Login successful?: %s", self.extended_data)
        else:
            self.extended_data = True

        return self.extended_data

    async def login(self) -> bool:
        """Login to Solar-Log."""

        return await self.client.login()

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

            data.battery_data = await self.update_battery_data()

            _LOGGER.debug("Extended data updated: %s",data)

        #calculated values (for downward compatibility)
        data.alternator_loss = data.power_dc - data.power_ac
        if data.power_dc != 0:
            data.efficiency = data.power_ac / data.power_dc *100
        if data.power_ac != 0:
            data.usage = data.consumption_ac / data.power_ac * 100
            data.power_available = data.power_ac - data.consumption_ac
        else:
            data.usage = 0.0
            data.power_available = 0.0
        if data.total_power != 0:
            data.capacity = data.power_dc / data.total_power * 100

        return data


    async def update_battery_data(self) -> BatteryData | None:
        """Update device specific data."""

        raw_data = await self.client.get_battery_data()

        if raw_data == []:
            return None

        battery_data = BatteryData(
                voltage=raw_data[0],
                level=raw_data[1],
                charge_power=raw_data[2],
                discharge_power=raw_data[3],
            )

        _LOGGER.debug("Battery data updated: %s",battery_data)

        return battery_data

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

    @property
    def password(self) -> str:
        """Password for Solar-Log."""
        return self.client.password

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
