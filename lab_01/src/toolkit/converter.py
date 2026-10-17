import json
from decimal import ROUND_HALF_EVEN, Decimal, DecimalException, localcontext
from pathlib import Path

from .errors import (
    ErrorInCompatibilityOfUnits,
    ErrorInCorrectnessOfNumericValue,
    ErrorInCorrectnessOfUnit,
    ErrorInTemperatureBelowAbsoluteZero,
)


class Converter:
    """Переводит число из одной единицы в другую по таблице из JSON-файла.

    Перевод возможен только внутри одной группы: метры в сантиметры можно, в
    килограммы нельзя. Регистр названий не важен. Температуру ниже абсолютного
    нуля конвертер отвергает. Результат - float.
    """
    def __init__(self, configuration_path: str | Path | None = None) -> None:
        """Читает и проверяет таблицу единиц.

        Без configuration_path берётся units.json рядом с модулем. Если файл не
        читается или в нём ошибка, бросает ErrorInCorrectnessOfUnit. Вычисления
        идут с точностью 28 значащих цифр.
        """
        path: Path = Path(configuration_path) if configuration_path else Path(__file__).with_name(
            "units.json"
        )

        try:
            configuration: dict = json.loads(path.read_text(encoding="utf-8"))
            self.units: dict[str, dict[str, dict[str, Decimal]]] = {
                group_name: {
                    unit: {name: Decimal(value) for name, value in parameters.items()}
                    for unit, parameters in group.items()
                }
                for group_name, group in configuration.items()
            }

            if not self.units or any(not group for group in self.units.values()):
                raise ValueError("Empty configuration")

            names: set[str] = set()

            for group_name, group in self.units.items():
                for unit, parameters in group.items():
                    if not unit or unit != unit.lower() or unit in names:
                        raise ValueError("Invalid or duplicate unit")

                    names.add(unit)

                    if not all(value.is_finite() for value in parameters.values()):
                        raise ValueError("Non-finite coefficient")

                    if parameters["numerator"] <= 0 or parameters["denominator"] <= 0:
                        raise ValueError("Invalid coefficient")

                    parameters["offset"]

                    if group_name == "temperature":
                        parameters["minimum"]

        except (OSError, ValueError, TypeError, KeyError, AttributeError, DecimalException) as error:
            raise ErrorInCorrectnessOfUnit("Invalid unit configuration") from error

        self.decimal_precision: int = 28

    def _checking_correctness_of_numeric_value(self, value: str | float | Decimal) -> Decimal:
        """Превращает value в конечный Decimal.

        Всё, что не читается как число, а также бесконечность и NaN дают
        ErrorInCorrectnessOfNumericValue.
        """
        try:
            number: Decimal = Decimal(str(value))

        except (DecimalException, ValueError, TypeError) as error:
            raise ErrorInCorrectnessOfNumericValue(
                f"Invalid numeric value: {value!r}"
            ) from error

        if not number.is_finite():
            raise ErrorInCorrectnessOfNumericValue(
                f"Numeric value must be finite: {value!r}"
            )

        return number

    def _checking_correctness_of_unit(self, unit: str) -> str:
        """Проверяет, что unit есть в таблице, и возвращает его в нижнем регистре.

        Для нестроки или неизвестной единицы бросает ErrorInCorrectnessOfUnit.
        """
        if not isinstance(unit, str):
            raise ErrorInCorrectnessOfUnit(
                f"Invalid unit: {unit!r}"
            )

        unit = unit.lower()

        for group in self.units.values():
            if unit in group:
                return unit

        raise ErrorInCorrectnessOfUnit(
            f"Unknown unit: {unit!r}"
        )

    def _searching_for_unit_group(self, unit: str) -> str:
        """Возвращает название группы, в которой лежит unit, например length.

        unit уже в нижнем регистре. Если его нет в таблице, бросает
        ErrorInCorrectnessOfUnit.
        """
        for group_name, group in self.units.items():
            if unit in group:
                return group_name

        raise ErrorInCorrectnessOfUnit(
            f"Unknown unit: {unit!r}"
        )

    def _checking_compatibility_of_units(self, from_unit: str, to_unit: str) -> str:
        """Возвращает общую группу двух единиц.

        Если группы разные, бросает ErrorInCompatibilityOfUnits.
        """
        from_group: str = self._searching_for_unit_group(from_unit)
        to_group: str = self._searching_for_unit_group(to_unit)

        if from_group != to_group:
            raise ErrorInCompatibilityOfUnits(
                f"Incompatible units: {from_unit!r} and {to_unit!r}"
            )

        return from_group

    def _calculation(
        self,
        value: Decimal,
        from_unit: str,
        to_unit: str,
        group: str
    ) -> Decimal:
        """Считает перевод value из from_unit в to_unit внутри группы group.

        Значение сначала приводится к базовой единице группы, потом к целевой.
        Для температуры раньше всего проверяется нижняя граница, при нарушении
        бросается ErrorInTemperatureBelowAbsoluteZero. Возвращает Decimal.
        """
        source: dict[str, Decimal] = self.units[group][from_unit]
        target: dict[str, Decimal] = self.units[group][to_unit]

        if group == "temperature" and value < source["minimum"]:
            raise ErrorInTemperatureBelowAbsoluteZero(
                "Temperature cannot be below absolute zero"
            )

        base_value: Decimal = (
            (value - source["offset"]) * source["numerator"] / source["denominator"]
        )

        return (
            base_value * target["denominator"] / target["numerator"] + target["offset"]
        )

    def __call__(
        self,
        value: str | float | Decimal,
        from_unit: str,
        to_unit: str
    ) -> float:
        """Проверяет аргументы, считает перевод и возвращает float.

        Вычисления идут в Decimal с точностью 28 цифр и округлением к ближайшей
        чётной (ROUND_HALF_EVEN). Переполнение и сбои Decimal превращаются в
        ErrorInCorrectnessOfNumericValue, остальные ошибки проходят как есть.
        """
        number: Decimal = self._checking_correctness_of_numeric_value(value)

        from_unit = self._checking_correctness_of_unit(from_unit)
        to_unit = self._checking_correctness_of_unit(to_unit)

        group: str = self._checking_compatibility_of_units(
            from_unit, to_unit
        )

        try:
            with localcontext() as context:
                context.prec = self.decimal_precision
                context.rounding = ROUND_HALF_EVEN

                result: Decimal = self._calculation(
                    number, from_unit, to_unit, group
                )

                converted_result: float = float(result)

                if converted_result == float("inf") or converted_result == float("-inf"):
                    raise ErrorInCorrectnessOfNumericValue(
                        "Conversion result is too large"
                    )

                return converted_result

        except DecimalException as error:
            raise ErrorInCorrectnessOfNumericValue(
                "Decimal conversion failed"
            ) from error

        except OverflowError as error:
            raise ErrorInCorrectnessOfNumericValue(
                "Conversion result is too large"
            ) from error
