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
    """Проверяет перевод величин по готовым примерам.

    value задаёт число, from_unit и to_unit — единицы, expected — ожидаемый
    результат. Проверяется тип float и приблизительное равенство значений,
    так как float не всегда хранит десятичные дроби совершенно точно.
    """
    result = Converter()(value, from_unit, to_unit)

    assert isinstance(result, float)
    assert result == pytest.approx(expected)


@pytest.mark.parametrize("value", ["abc", "", "NaN", "Infinity", "-Infinity", None, "1e999999"])
def test_invalid_numeric_value(value) -> None:
    """Проверяет отказ от недопустимых числовых данных.

    pytest передаёт value из списка: неверную строку, пустое значение,
    бесконечность или слишком большое число. Каждый пример должен вызвать
    ErrorInCorrectnessOfNumericValue при переводе метров в сантиметры.
    """
    with pytest.raises(ErrorInCorrectnessOfNumericValue):
        Converter()(value, "m", "cm")


@pytest.mark.parametrize(("source", "target"), [("meter", "m"), ("m", "unknown"), (None, "m")])
def test_unknown_unit(source, target) -> None:
    """Проверяет обработку неизвестного или неверного названия единицы.

    source и target содержат исходную и конечную единицы из таблицы теста.
    Хотя бы одна из них недопустима. Ожидается ErrorInCorrectnessOfUnit,
    а не попытка выполнить перевод.
    """
    with pytest.raises(ErrorInCorrectnessOfUnit):
        Converter()(1, source, target)


@pytest.mark.parametrize(("source", "target"), [("m", "kg"), ("c", "cm"), ("g", "f")])
def test_incompatible_units(source: str, target: str) -> None:
    """Проверяет запрет перевода между разными группами величин.

    В source и target передаются известные, но несовместимые единицы,
    например метры и килограммы. Каждый вызов должен закончиться
    ошибкой ErrorInCompatibilityOfUnits.
    """
    with pytest.raises(ErrorInCompatibilityOfUnits):
        Converter()(1, source, target)


@pytest.mark.parametrize(
    ("value", "unit"),
    [("-273.151", "c"), ("-459.671", "f"), ("-0.001", "k"),
     ("-273.150000000000000000000000001", "c")]
)
def test_absolute_zero(value: str, unit: str) -> None:
    """Проверяет запрет температуры ниже абсолютного нуля.

    value содержит недопустимую температуру, unit — её единицу.
    Даже перевод единицы в саму себя должен вызвать ошибку температуры.
    Один из примеров проверяет очень маленькое отклонение от границы.
    """
    with pytest.raises(ErrorInTemperatureBelowAbsoluteZero):
        Converter()(value, unit, unit)


def test_custom_configuration(tmp_path: Path) -> None:
    """Проверяет загрузку собственной таблицы единиц из файла.

    tmp_path — временная папка, которую предоставляет pytest.
    В неё записывается таблица с метрами и футами. Затем проверяется,
    что конвертер использует коэффициент из этого файла.
    """
    path = tmp_path / "units.json"
    path.write_text(json.dumps({"length": {
        "m": {"numerator": "1", "denominator": "1", "offset": "0"},
        "ft": {"numerator": "0.3048", "denominator": "1", "offset": "0"}
    }}), encoding="utf-8")

    assert Converter(path)(1, "ft", "m") == 0.3048


@pytest.mark.parametrize("configuration", ["broken", "[]", "{}", '{"length":{"m":{}}}'])
def test_invalid_configuration(tmp_path: Path, configuration: str) -> None:
    """Проверяет обработку неверного содержимого файла конфигурации.

    tmp_path задаёт временную папку, configuration — текст из списка
    ошибочных примеров. Текст записывается в файл. Создание конвертера
    с таким файлом должно вызвать ErrorInCorrectnessOfUnit.
    """
    path = tmp_path / "units.json"
    path.write_text(configuration, encoding="utf-8")

    with pytest.raises(ErrorInCorrectnessOfUnit):
        Converter(path)
