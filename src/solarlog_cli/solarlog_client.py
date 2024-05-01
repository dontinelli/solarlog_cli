"""Client to access Solar-Log."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import json
import logging
from typing import Any

from aiohttp import ClientSession

from .solarlog_exceptions import SolarLogError, SolarLogConnectionError

SOLARLOG_REQUEST_PAYLOAD = { 801: { 170: None } }

_LOGGER = logging.getLogger(__name__)


class Client():
    """Client class to access Solar-Log."""
    def __init__(self, host: str):

        self.host: str = host

        self.session: ClientSession = ClientSession()
        self._close_session: bool = True

        self.request_timeout = 10

    async def test_connection(self) -> bool:
        """Test the connection to Solar-Log"""

        url = f"{self.host}/getjp"

        response = await self.session.post(url, json = SOLARLOG_REQUEST_PAYLOAD)

        if response.status == 200:
            return True

        return False

    async def execute_http_request(self, json_payload) -> dict[str,Any]:
        """Hepler function to process the HTTP Get call."""
        if self.session is None:
            self.session = ClientSession()
            self._close_session = True

        url = f"{self.host}/getjp"

        header = {
            "Content-Type": "application/json",
        }

        try:
            async with asyncio.timeout(self.request_timeout):
                response = await self.session.post(url=url, headers = header, json = json_payload)
        except asyncio.TimeoutError as exception:
            msg = f"Timeout occurred while connecting to Solar-Log at {self.host}"
            raise SolarLogConnectionError(msg) from exception

        if response.status != 200:
            msg = f"The server responded with error code {response.status} while fetching data from Solar-Log at {self.host}.\n{url}\n{header}\n{json_payload}"
            text = await response.text()
            raise SolarLogError(
                msg,
                {"Content-Type": content_type, "response": text},
            )

        """
        content_type = response.headers.get("Content-Type", "")
        if content_type.count("text/html") > 0:
            msg = f"Error while fetching data from Solar-Log at {self.host}. Server response has wrong data format\n{url}\n{header}\n{json_payload}"
            text = await response.text()
            raise SolarLogError(
                msg,
                {"Content-Type": content_type, "response": text},
            )
        """
        text = await response.text()

        try:
            json_response = json.loads(text)
        except ValueError as err:
            msg = f"Error while decoding response: {err.msg}."
            raise SolarLogError(
                msg,
                {"Content-Type": content_type, "Server response": text},
            )

        return json_response

    async def get_basic_data(self) -> dict[str,Any]:
        """Get basic data from Solar-Log."""

        raw_data: dict = await self.execute_http_request({801: {170: None }})
        raw_data = raw_data['801']['170']

        data = {
            "last_updated": datetime.strptime(raw_data['100'], '%d.%m.%y %H:%M:%S'),
            "power_ac":raw_data['101'],
            "power_dc": raw_data['102'],
            "voltage_ac": raw_data['103'],
            "voltage_dc":raw_data['104'],
            "yield_day": raw_data['105'],
            "yield_yesterday":raw_data['106'],
            "yield_month": raw_data['107'],
            "yield_year": raw_data['108'],
            "yield_total": raw_data['109'],
            "consumption_ac": raw_data['110'],
            "consumption_day": raw_data['111'],
            "consumption_yesterday": raw_data['112'],
            "consumption_month": raw_data['113'],
            "consumption_year": raw_data['114'],
            "consumption_total": raw_data['115'],
            "total_power": raw_data['116']
        }

        return data

    async def get_power_per_inverter(self) -> dict[str,float]:
        """Get power data from Solar-Log"""

        raw_data: dict = await self.execute_http_request({782: None })
        raw_data = raw_data['782']

        data = {}

        for (key, value) in raw_data.items():
            if value != 0:
                data |= {f"power_{key}": value}

        return data

    async def get_energy_per_inverter(self) -> dict[str,float]:
        """Get power data from Solar-Log"""

        raw_data: dict = await self.execute_http_request({854: None })
        data_list = raw_data['854'][-1]

        data = {}

        for item in data_list:
            if item != 0:
                data |= {f"yearly_energy_{data_list.index(item)}": item}

        return data

    async def get_energy(self) -> dict[str,float]:
        """Get power data from Solar-Log"""

        raw_data: dict = await self.execute_http_request({878: None })

        data = {
            "yearly_production": raw_data['878'][-1][1],
            "yearly_consumption": raw_data['878'][-1][2],
            "yearly_self_consumption": raw_data['878'][-1][3],
        }

        return data

    async def get_inverter_list(self) -> dict[str,Any]:
        """Get list of all connected inverters."""

        #get list of inverters
        raw_data: dict = await self.execute_http_request({740: None })
        raw_data = raw_data['740']

        inverter_list = {}

        for (key, value) in raw_data.items():
            if value != "Err":
                #get name of the inverter
                raw_data = await self.execute_http_request({141:{key:{119: None}}})
                inverter_list |= {key: raw_data['141'][key]['119']}

        return inverter_list

    async def close(self) -> None:
        """Close open client session."""
        if self.session and self._close_session:
            await self.session.close()
