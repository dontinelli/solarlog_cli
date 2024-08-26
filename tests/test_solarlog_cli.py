"""Tests for solarlog_cli."""

from datetime import datetime, timedelta, UTC

from aioresponses import aioresponses

import pytest
from syrupy import SnapshotAssertion

from solarlog_cli.solarlog_connector import SolarLogConnector
from solarlog_cli.solarlog_exceptions import (
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

    assert await solarlog_connector.test_connection() == return_value

    assert solarlog_connector.client.session is not None
    assert not solarlog_connector.client.session.closed
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

    solarlog_connector = SolarLogConnector(
        "http://solarlog.com",
        True,
        "UTC",
        {0: True, 1: False, 2: False, 3: True},
    )

    data = await solarlog_connector.update_data()

    assert data == snapshot

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
    """Test login."""
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
