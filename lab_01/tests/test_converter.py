import json
from pathlib import Path

import pytest

from toolkit import Converter
from toolkit.errors import (
    ErrorInCompatibilityOfUnits,
    ErrorInCorrectnessOfNumericValue,
    ErrorInCorrectnessOfUnit,
    ErrorInTemperatureBelowAbsoluteZero,
)


@pytest.mark.parametrize(
    ("value", "from_unit", "to_unit", "expected"),
    [(1, "km", "m", 1000.0), (1, "m", "cm", 100.0), (1, "cm", "mm", 10.0),
     (1, "mm", "km", 0.000001), (1, "kg", "g", 1000.0), (500, "g", "kg", 0.5),
     (1, "KM", "Cm", 100000.0), (0, "c", "f", 32.0), (32, "f", "c", 0.0),
     (273.15, "k", "c", 0.0), (0, "c", "k", 273.15), (212, "f", "k", 373.15),
     (0, "k", "f", -459.67), (-459.67, "f", "k", 0.0),
     (-273.15, "c", "k", 0.0), (-10, "m", "m", -10.0), ("1e3", "g", "kg", 1.0)]
)
def test_conversion(value, from_unit: str, to_unit: str, expected: float) -> None:
    """Сверяет перевод с готовыми примерами.

    Результат должен быть float и примерно равен expected.
    """
    result = Converter()(value, from_unit, to_unit)

    assert isinstance(result, float)
    assert result == pytest.approx(expected)


@pytest.mark.parametrize("value", ["abc", "", "NaN", "Infinity", "-Infinity", None, "1e999999"])
def test_invalid_numeric_value(value) -> None:
    """Нечисловая строка, пустое значение, бесконечность и слишком большое число
    дают ErrorInCorrectnessOfNumericValue.
    """
    with pytest.raises(ErrorInCorrectnessOfNumericValue):
        Converter()(value, "m", "cm")


@pytest.mark.parametrize(("source", "target"), [("meter", "m"), ("m", "unknown"), (None, "m")])
def test_unknown_unit(source, target) -> None:
    """Если хотя бы одна из единиц неизвестна, ожидается ErrorInCorrectnessOfUnit.
    """
    with pytest.raises(ErrorInCorrectnessOfUnit):
        Converter()(1, source, target)


@pytest.mark.parametrize(("source", "target"), [("m", "kg"), ("c", "cm"), ("g", "f")])
def test_incompatible_units(source: str, target: str) -> None:
    """Известные, но несовместимые единицы, например метры и килограммы, дают
    ErrorInCompatibilityOfUnits.
    """
    with pytest.raises(ErrorInCompatibilityOfUnits):
        Converter()(1, source, target)


@pytest.mark.parametrize(
    ("value", "unit"),
    [("-273.151", "c"), ("-459.671", "f"), ("-0.001", "k"),
     ("-273.150000000000000000000000001", "c")]
)
def test_absolute_zero(value: str, unit: str) -> None:
    """Температура ниже абсолютного нуля даёт ошибку, даже когда единица
    переводится сама в себя.

    Один из примеров лежит совсем рядом с границей.
    """
    with pytest.raises(ErrorInTemperatureBelowAbsoluteZero):
        Converter()(value, unit, unit)


def test_custom_configuration(tmp_path: Path) -> None:
    """Конвертер берёт коэффициенты из собственной таблицы.

    В tmp_path записывается файл с метрами и футами.
    """
    path = tmp_path / "units.json"
    path.write_text(json.dumps({"length": {
        "m": {"numerator": "1", "denominator": "1", "offset": "0"},
        "ft": {"numerator": "0.3048", "denominator": "1", "offset": "0"}
    }}), encoding="utf-8")

    assert Converter(path)(1, "ft", "m") == 0.3048


@pytest.mark.parametrize("configuration", ["broken", "[]", "{}", '{"length":{"m":{}}}'])
def test_invalid_configuration(tmp_path: Path, configuration: str) -> None:
    """Файл конфигурации с неверным содержимым даёт ErrorInCorrectnessOfUnit уже
    при создании конвертера.
    """
    path = tmp_path / "units.json"
    path.write_text(configuration, encoding="utf-8")

    with pytest.raises(ErrorInCorrectnessOfUnit):
        Converter(path)
