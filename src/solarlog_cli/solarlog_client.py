"""Client to access Solar-Log."""

from __future__ import annotations

import asyncio
from datetime import datetime
import json
import logging
from typing import Any

from aiohttp import ClientResponse, ClientSession, ClientTimeout
import bcrypt

from .solarlog_exceptions import (
    SolarLogAuthenticationError,
    SolarLogConnectionError,
    SolarLogUpdateError,
)

from .solarlog_models import SolarlogData

SOLARLOG_REQUEST_PAYLOAD = '{ "801": { "170": null } }'
_LOGGER = logging.getLogger(__name__)


class Client:
    """Client class to access Solar-Log."""

    # pylint: disable=too-many-positional-arguments

    def __init__(self, host: str, session: ClientSession | None, password: str = "") -> None:
        self.host: str = host
        self.password: str = password

        self.request_timeout = 30

        if not session:
            self.session = ClientSession()
        else:
            self.session = session

        self._hashed_pwd: bool = False
        self._close_session: bool = True

    async def test_connection(self) -> bool:
        """Test the connection to Solar-Log."""
        if self.session is None:
            self.session = ClientSession()
            self._close_session = True

        url = f"{self.host}/getjp"

        response = await self.session.post(
            url, json=SOLARLOG_REQUEST_PAYLOAD,
            timeout=ClientTimeout(total=self.request_timeout)
        )

        if response.status == 200:
            return True

        return False

    async def login(self) -> bool:
        """Test the connection to Solar-Log."""

        if self.password == "":
            return False

        payload: str = f"u=user&p={self.password}"

        response = await self.execute_http_request(payload, "login")

        text = await response.text()
        _LOGGER.debug("Response: %s", text)
        if text.count("FAILED - User was wrong"):
            # Response means, that no password is required
            self.password = ""
            return False

        if text.count("FAILED - Password was wrong"):
            # For newer firmware, login with encrypted PWD is required.
            # Therefore test with encrypted PWD and only raise authentication error,
            # if login with encrypted PWD fails as well.

            payload = '{ "550": None }'

            response = await self.execute_http_request(payload)

            text = await response.text()
            _LOGGER.debug("Response to request for user salts: %s", text)
            r_dict: dict[str, Any] = json.loads(text)

            salt: str = r_dict.get('550', {}).get('104')
            _LOGGER.debug("Salt to hash pwd: %s", salt)

            try:
                if salt != 'QUERY IMPOSSIBLE 000' and salt is not None:
                    hashed_password = bcrypt.hashpw(
                        self.password.encode(), salt.encode())
                    payload = f"u=user&p={hashed_password.decode('utf-8')}"
                    response = await self.execute_http_request(payload, "login")
                    text = await response.text()
                    _LOGGER.debug(
                        "Response of login with hashed pwd: %s", text)
                    if text.count("FAILED - Password was wrong"):
                        _LOGGER.debug("Wrong password (hashed)")
                        raise SolarLogAuthenticationError
                    self.password = hashed_password.decode('utf-8')
            except Exception as exception:
                raise SolarLogAuthenticationError from exception

            self._hashed_pwd = True

        self.session.cookie_jar.update_cookies({"SolarLog": response.cookies["SolarLog"].value})

        _LOGGER.debug("response: %s", text)
        _LOGGER.debug("cookies: %s", response.cookies)
        _LOGGER.debug("Login successful, token: %s", response.cookies["SolarLog"].value)

        return True

    async def execute_http_request(self, body: str, path: str = "getjp") -> ClientResponse:
        """Helper function to process the HTTP Get call."""
        if self.session is None:
            self.session = ClientSession()
            self._close_session = True

        url = f"{self.host}/{path}"

        header = {"Content-Type": "text/html", "X-SL-CSRF-PROTECTION": "1"}

        _LOGGER.debug("HTTP-request header: %s", header)
        _LOGGER.debug("HTTP-request body: %s", body)

        try:
            response = await self.session.post(
                url=url,
                headers=header,
                data=body,
                timeout=ClientTimeout(total=self.request_timeout),
            )
        except asyncio.TimeoutError as exception:
            msg = f"Timeout occurred while connecting to Solar-Log at {self.host}"
            raise SolarLogConnectionError(msg) from exception

        content_type = response.headers.get("Content-Type", "")

        if response.status != 200:
            # pylint: disable-next=line-too-long
            msg = f"The server responded with error code {response.status} while fetching data from Solar-Log at {self.host}.\n{url}\n{header}\n{body}"
            text = await response.text()
            raise SolarLogUpdateError(
                msg,
                {"Content-Type": content_type, "response": text},
            )

        _LOGGER.debug("HTTP-request successful: %s", response)
        return response

    async def parse_http_response(self, response: ClientResponse) -> dict[str, Any]:
        """Helper function to parse the HTTP response."""

        text = await response.text(errors="replace")
        _LOGGER.debug("Parsing http response: %s", text)

        if text.count('{"QUERY IMPOSSIBLE 000"}'):
            raise SolarLogUpdateError(f"Server response: {text}")

        if text.count("ACCESS DENIED") and not text.startswith('{"550":{'):
            raise SolarLogAuthenticationError(f"Server response: {text}")

        try:
            json_response = json.loads(text)
        except ValueError as err:
            msg = f"Value error while decoding response: {err}."
            raise SolarLogUpdateError(
                msg,
                {"Server response": text},
            ) from err

        return json_response

    async def get_basic_data(self) -> SolarlogData:
        """Get basic data from Solar-Log."""

        raw_data: dict[str, Any] = await self.parse_http_response(
            await self.execute_http_request(SOLARLOG_REQUEST_PAYLOAD)
        )
        raw_data = raw_data["801"]["170"]

        data = SolarlogData(
            last_updated=datetime.strptime(
                raw_data["100"], "%d.%m.%y %H:%M:%S"),
            power_ac=raw_data["101"],
            power_dc=raw_data["102"],
            voltage_ac=raw_data["103"],
            voltage_dc=raw_data["104"],
            yield_day=raw_data["105"],
            yield_yesterday=raw_data["106"],
            yield_month=raw_data["107"],
            yield_year=raw_data["108"],
            yield_total=raw_data["109"],
            consumption_ac=raw_data["110"],
            consumption_day=raw_data["111"],
            consumption_yesterday=raw_data["112"],
            consumption_month=raw_data["113"],
            consumption_year=raw_data["114"],
            consumption_total=raw_data["115"],
            total_power=raw_data["116"],
        )

        return data

    async def get_battery_data(self) -> list[float]:
        """Get battery data from Solar-Log"""

        raw_data: dict = await self.parse_http_response(
            await self.execute_http_request('{ "858": null }')
        )

        data: list[float] = raw_data["858"]

        return data

    async def get_power_per_inverter(self) -> dict[int, float]:
        """Get power data from Solar-Log"""

        raw_data: dict = await self.parse_http_response(
            await self.execute_http_request('{ "782": null }')
        )

        data = {int(key): val for key,
                val in raw_data["782"].items() if val != "0"}

        return data

    async def get_energy_per_inverter(self) -> dict[int, float]:
        """Get power data from Solar-Log"""

        raw_data: dict = await self.parse_http_response(
            await self.execute_http_request('{ "854": null }')
        )
        data_list = raw_data["854"][-1][-1]

        data: dict[int, float] = {}

        for item in data_list:
            if item != 0:
                data |= {int(data_list.index(item)): item}

        return data

    async def get_energy(self, data: SolarlogData) -> SolarlogData:
        """Get energy data from Solar-Log"""

        raw_data: dict = await self.parse_http_response(
            await self.execute_http_request('{ "878": null }')
        )

        if raw_data["878"] != "QUERY IMPOSSIBLE 000":
            data.production_year = raw_data["878"][-1][1]
            data.self_consumption_year = raw_data["878"][-1][3]

        return data

    async def get_device_list(self) -> dict[int, str]:
        """Get list of all connected devices."""

        # get list of all inverters connected to Solar-Log
        raw_data: dict = await self.parse_http_response(
            await self.execute_http_request('{ "740": null }')
        )
        raw_data = raw_data["740"]

        device_list: dict[int, str] = {}

        for key, value in raw_data.items():
            if value != "Err":
                # get name of the inverter
                raw_data = await self.parse_http_response(
                    await self.execute_http_request(
                        f"""{{ "141": {{ "{key}": {{ "119": null }} }} }}"""
                    )
                )
                device_list |= {int(key): raw_data["141"][key]["119"]}

        return device_list

    async def close(self) -> None:
        """Close open client session."""
        if self.session and self._close_session:
            await self.session.close()
