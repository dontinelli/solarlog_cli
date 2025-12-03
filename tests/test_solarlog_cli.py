"""Tests for solarlog_cli."""

from aioresponses import aioresponses
from aiohttp import ClientSession

import pytest
from syrupy.assertion import SnapshotAssertion

from solarlog_cli.solarlog_connector import SolarLogConnector
from solarlog_cli.solarlog_exceptions import (
    SolarLogAuthenticationError,
    SolarLogConnectionError,
    SolarLogError,
    SolarLogUpdateError,
)

from . import load_fixture


@pytest.mark.parametrize(
    ("response_status", "return_value"),
    [
        (200, True),
        (400, False),
    ],
)
async def test_connection(
    responses: aioresponses,
    response_status: str,
    return_value: bool,
) -> None:
    """Test connection."""
    responses.post(
        "localhost/getjp",
        status=response_status,
    )

    solarlog_connector = SolarLogConnector("localhost")

    await solarlog_connector.client.close()
    solarlog_connector.client.session = None  # type: ignore [assignment]
    assert await solarlog_connector.test_connection() == return_value

    assert solarlog_connector.host == "localhost"

    assert solarlog_connector.client.session is not None
    assert not solarlog_connector.client.session.closed
    await solarlog_connector.client.close()
    assert solarlog_connector.client.session.closed


async def test_existing_session(
    responses: aioresponses,
) -> None:
    """Test connection."""
    responses.post(
        "localhost/getjp",
        status=200,
    )

    solarlog_connector = SolarLogConnector(
        "localhost", session=ClientSession())

    assert await solarlog_connector.test_connection()

    assert solarlog_connector.host == "localhost"

    assert solarlog_connector.client.session is not None
    assert not solarlog_connector.client.session.closed
    await solarlog_connector.client.close()
    assert solarlog_connector.client.session.closed


async def test_extended_data_available(
    responses: aioresponses,
) -> None:
    """Test extended data available."""

    solarlog_connector = SolarLogConnector(
        "http://solarlog.com", password="pwd")

    responses.post(
        "http://solarlog.com/getjp",
        timeout=True,
    )
    assert not await solarlog_connector.test_extended_data_available()

    responses.post(
        "http://solarlog.com/getjp",
        status=400,
    )
    assert not await solarlog_connector.test_extended_data_available()

    responses.post(
        "http://solarlog.com/getjp",
        body=load_fixture("device_list_access_denied.json"),
    )
    responses.post(
        "http://solarlog.com/login",
        body="FAILED - User was wrong",
    )
    assert not await solarlog_connector.test_extended_data_available()
    assert solarlog_connector.password == ""

    responses.post(
        "http://solarlog.com/getjp",
        body=load_fixture("device_list_access_denied.json"),
    )
    responses.post(
        "http://solarlog.com/login",
        body="FAILED - Password was wrong",
    )
    responses.post(
        "http://solarlog.com/getjp",
        body=load_fixture("user_salts.json"),
    )
    responses.post(
        "http://solarlog.com/login",
        exception=SolarLogAuthenticationError('test'),
    )
    solarlog_connector.client.password = "pwd"
    # type: ignore [call-overload]
    with pytest.raises(SolarLogAuthenticationError):
        await solarlog_connector.test_extended_data_available()

    responses.post(
        "http://solarlog.com/getjp",
        body=load_fixture("device_list.json"),
    )
    assert await solarlog_connector.test_extended_data_available()

    await solarlog_connector.client.close()
    assert solarlog_connector.client.session.closed


async def test_login_and_data_retreival(responses: aioresponses) -> None:
    """Test login into Solar-Log."""
    responses.post(
        "http://solarlog.com/login",
        headers={"Set-Cookie": "SolarLog=token"},
        body="SUCCESS - Password was correct, you are now logged in",
    )
    solarlog_connector = SolarLogConnector(
        "http://solarlog.com", password="pwd")

    assert await solarlog_connector.login()

    responses.post(
        "http://solarlog.com/getjp",
        body=load_fixture("basic_data.json"),
    )
    await solarlog_connector.update_data()

    await solarlog_connector.client.close()
    assert solarlog_connector.client.session.closed


async def test_login_hashed_pwd(responses: aioresponses) -> None:
    """Test login into Solar-Log."""

    responses.post(
        "http://solarlog.com/login",
        body="FAILED - Password was wrong",
    )
    responses.post(
        "http://solarlog.com/getjp",
        body=load_fixture("user_salts.json"),
    )
    responses.post(
        "http://solarlog.com/login",
        headers={"Set-Cookie": "SolarLog=token"},
        body="SUCCESS - Password was correct, you are now logged in",
    )
    solarlog_connector = SolarLogConnector(
        "http://solarlog.com", password="pwd")

    assert await solarlog_connector.login()

    await solarlog_connector.client.close()
    assert solarlog_connector.client.session.closed


async def test_login_exceptions(responses: aioresponses) -> None:
    """Test exceptions at login into Solar-Log."""
    solarlog_connector = SolarLogConnector(
        "http://solarlog.com", password="pwd")

    responses.post(
        "http://solarlog.com/login",
        body="FAILED - Password was wrong",
    )
    responses.post(
        "http://solarlog.com/getjp",
        body=load_fixture("user_salts.json"),
    )
    responses.post(
        "http://solarlog.com/login",
        body="FAILED - Password was wrong",
    )
    # type: ignore [call-overload]
    with pytest.raises(SolarLogAuthenticationError):
        await solarlog_connector.client.login()

    responses.post(
        "http://solarlog.com/login",
        body="FAILED - User was wrong",
    )
    assert not await solarlog_connector.client.login()

    responses.post(
        "http://solarlog.com/getjp",
        body=load_fixture("device_list.json"),
    )
    assert not await solarlog_connector.client.login()

    await solarlog_connector.client.close()
    assert solarlog_connector.client.session.closed


async def test_update_data(
    responses: aioresponses,
    snapshot: SnapshotAssertion
) -> None:
    """Test update data."""
    responses.post(
        "http://solarlog.com/getjp",
        body=load_fixture("basic_data.json"),
    )
    responses.post(
        "http://solarlog.com/getjp",
        body=load_fixture("extended_data.json"),
    )
    responses.post(
        "http://solarlog.com/getjp",
        body=load_fixture("power_per_inverter.json"),
    )
    responses.post(
        "http://solarlog.com/getjp",
        body=load_fixture("energy_per_inverter.json"),
    )
    responses.post(
        "http://solarlog.com/getjp",
        body=load_fixture("battery_data.json"),
    )

    solarlog_connector = SolarLogConnector(
        "http://solarlog.com",
        True,
        "UTC",
        {0: True, 1: True, 2: False, 3: True},
    )

    data = await solarlog_connector.update_data()

    assert data == snapshot

    await solarlog_connector.client.close()
    assert solarlog_connector.client.session.closed


async def test_update_data_without_battery(
    responses: aioresponses,
) -> None:
    """Test update data."""
    responses.post(
        "http://solarlog.com/getjp",
        body=load_fixture("basic_data.json"),
    )
    responses.post(
        "http://solarlog.com/getjp",
        body=load_fixture("extended_data.json"),
    )
    responses.post(
        "http://solarlog.com/getjp",
        body=load_fixture("power_per_inverter.json"),
    )
    responses.post(
        "http://solarlog.com/getjp",
        body=load_fixture("energy_per_inverter.json"),
    )
    responses.post(
        "http://solarlog.com/getjp",
        body=load_fixture("battery_data_without_battery.json"),
    )

    solarlog_connector = SolarLogConnector(
        "http://solarlog.com",
        True,
        "UTC",
        {0: True, 1: True, 2: False, 3: True},
    )

    data = await solarlog_connector.update_data()

    assert data.battery_data is None

    await solarlog_connector.client.close()
    assert solarlog_connector.client.session.closed


@pytest.mark.parametrize(
    ("status", "request_timeout", "error"),
    [
        (200, True, SolarLogConnectionError),
        (400, False, SolarLogUpdateError),
    ],
)
async def test_update_data_exceptions(
    responses: aioresponses,
    status: int,
    request_timeout: bool,
    error: SolarLogError,
) -> None:
    """Test update data with exceptions."""
    responses.post(
        "http://solarlog.com/getjp",
        timeout=request_timeout,
        status=status,
    )

    solarlog_connector = SolarLogConnector(
        "http://solarlog.com",
        True,
        "UTC",
        {0: True, 1: False, 2: False, 3: True},
    )
    await solarlog_connector.client.close()
    solarlog_connector.client.session = None  # type: ignore [assignment]

    with pytest.raises(error):  # type: ignore [call-overload]
        await solarlog_connector.update_data()

    await solarlog_connector.client.close()
    assert solarlog_connector.client.session.closed


async def test_update_data_with_data_exceptions(
    responses: aioresponses,
) -> None:
    """Test update data with exceptions due to data."""
    responses.post(
        "http://solarlog.com/getjp",
        body="",
    )
    responses.post(
        "http://solarlog.com/getjp",
        body='{"QUERY IMPOSSIBLE 000"}',
    )
    responses.post(
        "http://solarlog.com/getjp",
        body=load_fixture("basic_data_during_update.json"),
    )
    responses.post(
        "http://solarlog.com/getjp",
        body=load_fixture("basic_data_no_power.json"),
    )

    solarlog_connector = SolarLogConnector("http://solarlog.com")

    with pytest.raises(SolarLogUpdateError):
        await solarlog_connector.update_data()

    with pytest.raises(SolarLogUpdateError):
        await solarlog_connector.update_data()

    with pytest.raises(SolarLogUpdateError):
        await solarlog_connector.update_data()

    data = await solarlog_connector.update_data()

    assert data.usage == 0
    assert data.power_available == 0

    await solarlog_connector.client.close()
    assert solarlog_connector.client.session.closed


async def test_update_device_list(
    responses: aioresponses,
    snapshot: SnapshotAssertion
) -> None:
    """Test update device list."""

    responses.post(
        "http://solarlog.com/getjp",
        body=load_fixture("device_list.json"),
    )
    responses.post(
        "http://solarlog.com/getjp",
        body=load_fixture("device_data_1.json"),
    )
    responses.post(
        "http://solarlog.com/getjp",
        body=load_fixture("device_data_2.json"),
    )
    responses.post(
        "http://solarlog.com/getjp",
        body=load_fixture("device_data_3.json"),
    )
    responses.post(
        "http://solarlog.com/getjp",
        body=load_fixture("device_data_4.json"),
    )

    solarlog_connector = SolarLogConnector(
        "http://solarlog.com",
        True,
        "UTC",
        {0: True, 1: False, 2: False, 3: True},
    )

    await solarlog_connector.update_device_list()
    data = solarlog_connector.device_list

    assert data == snapshot

    assert solarlog_connector.device_name(0) == "Device 1"
    assert solarlog_connector.device_name(4) == ""

    await solarlog_connector.client.close()
    assert solarlog_connector.client.session.closed


async def test_enabled_devices(responses: aioresponses) -> None:
    """Test enabled devices."""
    responses.post(
        "http://solarlog.com/getjp",
        body=load_fixture("device_list.json"),
    )

    solarlog_connector = SolarLogConnector(
        "http://solarlog.com", device_enabled={})
    assert solarlog_connector.device_enabled() == {}
    assert await solarlog_connector.update_device_list() == {}

    solarlog_connector.set_enabled_devices(
        {0: True, 1: False, 2: False, 3: True})

    assert solarlog_connector.device_enabled(0)
    assert not solarlog_connector.device_enabled(1)
    assert solarlog_connector.device_enabled(3)

    await solarlog_connector.client.close()
    assert solarlog_connector.client.session.closed
