"""Sunsynk library."""
from typing import Final

from .helpers import NumType, ValType
from .rwsensors import RWSensor

# pylint: disable=unused-import
# flake8: noqa
from .sensors import Sensor
from .rwsensors import SwitchRWSensor, TimeRWSensor, NumberRWSensor, SelectRWSensor
from .state import InverterState
from .sunsynk import Sunsynk
from .solarmansunsynk import SolarmanSunsynk

# pylint: enable=unused-import

VERSION = "0.6.4"

CELSIUS: Final = "°C"
KWH: Final = "kWh"
AMPS: Final = "A"
VOLT: Final = "V"
WATT: Final = "W"
