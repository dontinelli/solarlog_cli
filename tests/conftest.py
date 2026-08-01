"""Tests for solarlog_cli - configurations."""

from collections.abc import AsyncGenerator

import pytest
from aiointercept import aiointercept

from syrupy.assertion import SnapshotAssertion

from .syrupy import SolarlogSnapshotExtension

from solarlog_cli.solarlog_connector import SolarLogConnector

@pytest.fixture(name="snapshot")
def snapshot_assertion(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Return snapshot assertion fixture with the SolarLog extension."""
    return snapshot.use_extension(SolarlogSnapshotExtension)


@pytest.fixture(name="solarlog_connector")
async def connector() -> AsyncGenerator[SolarLogConnector, None]:
    """Return a SolarLogConnector."""
    async with SolarLogConnector(
        "http://solarlog.com",
    ) as solarlog_connector:
        yield solarlog_connector


@pytest.fixture(name="responses")
async def aiointercept_fixture() -> AsyncGenerator[aiointercept, None]:
    """Return aiointercept fixture."""
    async with aiointercept(mock_external_urls=True) as mocked_responses:
        yield mocked_responses
