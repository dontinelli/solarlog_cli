"""Tests for solarlog_cli - configurations."""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from aiointercept import aiointercept
from syrupy.assertion import SnapshotAssertion

from .syrupy import SolarlogSnapshotExtension


@pytest.fixture(name="snapshot")
def snapshot_assertion(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Return snapshot assertion fixture with the SolarLog extension."""
    return snapshot.use_extension(SolarlogSnapshotExtension)


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def aiointercept_server() -> AsyncGenerator[aiointercept, None]:
    """Return aiointercept server for tests using hard-coded external URLs."""
    async with aiointercept(mock_external_urls=True) as mocked_responses:
        yield mocked_responses


@pytest.fixture(name="responses")
def aiointercept_fixture(aiointercept_mock: aiointercept) -> aiointercept:
    """Return a cleared aiointercept mock for the current test."""
    return aiointercept_mock
