"""Models for SolarLog."""
from dataclasses import dataclass, field
from datetime import datetime

from mashumaro import DataClassDictMixin


@dataclass
class InverterData():
    """Inverter Data model."""

    name: str = ""
    enabled: bool = False
    current_power: float | None = None
    consumption_year: float | None= None


@dataclass
class SolarlogData(DataClassDictMixin):
    """Basic Data model."""

    # pylint: disable=too-many-instance-attributes

    consumption_ac: float
    consumption_day: float
    consumption_month: float
    consumption_total: float
    consumption_yesterday: float
    consumption_year: float
    last_updated: datetime
    power_ac: float
    power_dc: float
    total_power: float
    voltage_ac: float
    voltage_dc: float
    yield_day: float
    yield_yesterday: float
    yield_month: float
    yield_year: float
    yield_total: float

    #calculated values
    alternator_loss: float = 0
    capacity: float | None = None
    efficiency: float | None = None
    power_available: float = 0
    usage: float | None = None

    #extended data
    inverter_data: dict[int, InverterData] = field(default_factory=dict)
    production_year: float | None = None
    self_consumption_year: float | None = None
