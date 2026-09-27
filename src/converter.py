from src.constants import LENGTH_UNITS, MASS_UNITS, TEMPERATURE_UNITS
from src.errors import ConverterError


def convert(value: float, from_unit: str, to_unit: str) -> float:
    source = from_unit.lower()
    target = to_unit.lower()

    if source in LENGTH_UNITS and target in LENGTH_UNITS:
        return value * LENGTH_UNITS[source] / LENGTH_UNITS[target]
    if source in MASS_UNITS and target in MASS_UNITS:
        return value * MASS_UNITS[source] / MASS_UNITS[target]
    if source in TEMPERATURE_UNITS and target in TEMPERATURE_UNITS:
        return _convert_temperature(value, source, target)

    known_units = LENGTH_UNITS.keys() | MASS_UNITS.keys() | TEMPERATURE_UNITS
    if source not in known_units or target not in known_units:
        raise ConverterError("unknown unit")
    raise ConverterError("incompatible units")


def _convert_temperature(value: float, source: str, target: str) -> float:
    if source == "c":
        kelvin = value + 273.15
    elif source == "f":
        kelvin = (value - 32) * 5 / 9 + 273.15
    else:
        kelvin = value

    if kelvin < 0:
        raise ConverterError("below absolute zero")

    if target == "k":
        return kelvin
    if target == "c":
        return kelvin - 273.15
    return (kelvin - 273.15) * 9 / 5 + 32
