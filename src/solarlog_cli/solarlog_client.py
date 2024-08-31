"""Client to access Solar-Log."""

from __future__ import annotations

import asyncio
from datetime import datetime
import json
from typing import Any

from aiohttp import ClientSession, ClientTimeout

from .solarlog_exceptions import SolarLogConnectionError, SolarLogUpdateError
from .solarlog_models import SolarlogData

SOLARLOG_REQUEST_PAYLOAD = {801: {170: None}}


class Client:
    """Client class to access Solar-Log."""

    def __init__(self, host: str) -> None:
        self.host: str = host

        self.session: ClientSession = ClientSession()
        self._close_session: bool = True

        self.request_timeout = 10

    async def test_connection(self) -> bool:
        """Test the connection to Solar-Log"""

        url = f"{self.host}/getjp"

        response = await self.session.post(url, json=SOLARLOG_REQUEST_PAYLOAD)

        if response.status == 200:
            return True

        return False

    async def execute_http_request(self, json_payload) -> dict[str, Any]:
        """Hepler function to process the HTTP Get call."""
        if self.session is None:
            self.session = ClientSession()
            self._close_session = True

        url = f"{self.host}/getjp"

        header = {
            "Content-Type": "application/json",
        }

        try:
            response = await self.session.post(
                url=url,
                headers=header,
                json=json_payload,
                timeout=ClientTimeout(total=self.request_timeout)
            )
        except asyncio.TimeoutError as exception:
            msg = f"Timeout occurred while connecting to Solar-Log at {self.host}"
            raise SolarLogConnectionError(msg) from exception

        content_type = response.headers.get("Content-Type", "")

        if response.status != 200:
            # pylint: disable-next=line-too-long
            msg = f"The server responded with error code {response.status} while fetching data from Solar-Log at {self.host}.\n{url}\n{header}\n{json_payload}"
            text = await response.text()
            raise SolarLogUpdateError(
                msg,
                {"Content-Type": content_type, "response": text},
            )

        text = await response.text()

        try:
            json_response = json.loads(text)
        except ValueError as err:
            msg = f"Value error while decoding response: {err}."
            raise SolarLogUpdateError(
                msg,
                {"Content-Type": content_type, "Server response": text},
            ) from err

        return json_response

    async def get_basic_data(self) -> SolarlogData:
        """Get basic data from Solar-Log."""

        raw_data: dict = await self.execute_http_request({801: {170: None}})
        raw_data = raw_data["801"]["170"]

        data = SolarlogData(
            last_updated = datetime.strptime(raw_data["100"], "%d.%m.%y %H:%M:%S"),
            power_ac = raw_data["101"],
            power_dc = raw_data["102"],
            voltage_ac = raw_data["103"],
            voltage_dc = raw_data["104"],
            yield_day = raw_data["105"],
            yield_yesterday = raw_data["106"],
            yield_month = raw_data["107"],
            yield_year = raw_data["108"],
            yield_total = raw_data["109"],
            consumption_ac = raw_data["110"],
            consumption_day = raw_data["111"],
            consumption_yesterday = raw_data["112"],
            consumption_month = raw_data["113"],
            consumption_year = raw_data["114"],
            consumption_total = raw_data["115"],
            total_power = raw_data["116"],
        )

        return data

    async def get_power_per_inverter(self) -> dict[int, float]:
        """Get power data from Solar-Log"""

        raw_data: dict = await self.execute_http_request({782: None})

        data = {int(key): val for key, val in raw_data["782"].items() if val != "0"}

        return data

    async def get_energy_per_inverter(self) -> dict[int, float]:
        """Get power data from Solar-Log"""

        raw_data: dict = await self.execute_http_request({854: None})
        data_list = raw_data["854"][-1][-1]

        data: dict[int, float] = {}

        for item in data_list:
            if item != 0:
                data |= {int(data_list.index(item)): item}

        return data

    async def get_energy(self, data: SolarlogData) -> SolarlogData:
        """Get energy data from Solar-Log"""

        raw_data: dict = await self.execute_http_request({878: None})

        data.production_year = raw_data["878"][-1][1]
        data.self_consumption_year = raw_data["878"][-1][3]

        return data

    async def get_device_list(self) -> dict[int, str]:
        """Get list of all connected devices."""

        # get list of all inverters connected to Solar-Log
        raw_data: dict = await self.execute_http_request({740: None})
        raw_data = raw_data["740"]

        device_list: dict[int, str] = {}

        for key, value in raw_data.items():
            if value != "Err":
                # get name of the inverter
                raw_data = await self.execute_http_request({141: {key: {119: None}}})
                device_list |= {int(key): raw_data["141"][key]["119"]}

        return device_list

    async def close(self) -> None:
        """Close open client session."""
        if self.session and self._close_session:
            await self.session.close()
