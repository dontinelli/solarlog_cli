"""Tests for solarlog_cli - configurations."""

from collections.abc import AsyncGenerator

import pytest
from aiointercept import aiointercept

from syrupy.assertion import SnapshotAssertion

from .syrupy import SolarlogSnapshotExtension


@pytest.fixture(name="snapshot")
def snapshot_assertion(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Return snapshot assertion fixture with the SolarLog extension."""
    return snapshot.use_extension(SolarlogSnapshotExtension)

@pytest.fixture(name="responses")
async def aiointercept_fixture() -> AsyncGenerator[aiointercept, None]:
    """Return aiointercept fixture."""
    async with aiointercept(mock_external_urls=True) as mocked_responses:
        yield mocked_responses
