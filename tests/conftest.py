"""Tests for solarlog_cli - configurations."""

from typing import Generator

from aioresponses import aioresponses
import pytest

from syrupy import SnapshotAssertion

from .syrupy import SolarlogSnapshotExtension


@pytest.fixture(name="snapshot")
def snapshot_assertion(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Return snapshot assertion fixture with the SolarLog extension."""
    return snapshot.use_extension(SolarlogSnapshotExtension)

@pytest.fixture(name="responses")
def aioresponses_fixture() -> Generator[aioresponses, None, None]:
    """Return aioresponses fixture."""
    with aioresponses() as mocked_responses:
        yield mocked_responses
