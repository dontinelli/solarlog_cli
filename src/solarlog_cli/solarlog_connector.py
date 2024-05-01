"""Connector class to manage access to FYTA API."""

from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from .solarlog_client import Client
from .utils import safe_get


class SolarLogConnector():
    """Connector class to access Solar-Log."""

    _inverter_list: dict[str, str]
    _inverter_enabled: dict[str, bool]

    def __init__(self, host: str, extended_data: bool = False, tz: str = ""):
        self.client = Client(host)
        self.extended_data: bool = extended_data

        self.timezone: ZoneInfo = timezone.utc if tz == "" else ZoneInfo(tz)

    async def test_connection(self) -> bool:
        """Test if connection to Solar-Log works."""

        return await self.client.test_connection()

    async def update_data(self) -> dict[str, Any]:
        """Get data."""

        data: dict = await self.client.get_basic_data()
        print(data)
        data["last_updated"] = data["last_updated"].astimezone(self.timezone)

        if self.extended_data:
            data |= await self.client.get_power_per_inverter()
            data |= await self.client.get_energy_per_inverter()
            data |= await self.client.get_energy()

        return data

    @property
    def host(self) -> str:
        """Host of Solar-Log."""
        return self.client.host

    @property
    def inverter(self) -> dict[str, str]:
        """Host of Solar-Log."""
        return self.inverter_list

    def inverter_enabled(self, inverter_id: str) -> bool:
        """Status of inverter."""
        return _inverter_enabled.get(inverter_id)
