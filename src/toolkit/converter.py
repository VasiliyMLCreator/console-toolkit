from toolkit.errors import ConverterError

LENGTH = {
    "mm": 0.001,
    "cm": 0.01,
    "m": 1.0,
    "km": 1000.0,
}

MASS = {
    "g": 0.001,
    "kg": 1.0,
}

TEMP = {"c", "f", "k"}


def convert(value: float, from_unit: str, to_unit: str) -> float:
    from_u = from_unit.lower()
    to_u = to_unit.lower()

    if from_u in LENGTH and to_u in LENGTH:
        return value * LENGTH[from_u] / LENGTH[to_u]
    if from_u in MASS and to_u in MASS:
        return value * MASS[from_u] / MASS[to_u]
    if from_u in TEMP and to_u in TEMP:
        return _convert_temp(value, from_u, to_u)

    if from_u not in LENGTH and from_u not in MASS and from_u not in TEMP:
        raise ConverterError("unknown unit")
    if to_u not in LENGTH and to_u not in MASS and to_u not in TEMP:
        raise ConverterError("unknown unit")
    raise ConverterError("incompatible units")


def _convert_temp(value: float, from_u: str, to_u: str) -> float:
    if from_u == "c":
        kelvin = value + 273.15
    elif from_u == "f":
        kelvin = (value - 32) * 5 / 9 + 273.15
    else:
        kelvin = value

    if kelvin < 0:
        raise ConverterError("below absolute zero")

    if to_u == "k":
        return kelvin
    if to_u == "c":
        return kelvin - 273.15
    return (kelvin - 273.15) * 9 / 5 + 32
