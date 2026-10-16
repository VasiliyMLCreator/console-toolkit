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
    """Переводит числовое значение из одной единицы измерения в другую.

    Единицы и коэффициенты берутся из JSON-файла. Перевод разрешён только
    внутри одной группы, например из метров в сантиметры. Регистр названий
    не важен. Температура ниже абсолютного нуля считается ошибкой.
    Готовый результат возвращается как float.
    """
    def __init__(self, configuration_path: str | Path | None = None) -> None:
        """Загружает и проверяет таблицу единиц измерения.

        configuration_path задаёт путь к JSON-файлу. Если путь не передан,
        используется units.json рядом с этим модулем. Коэффициенты переводятся
        в Decimal. Проверяются названия, обязательные поля и допустимость чисел.
        При недоступном или неверном файле вызывается ErrorInCorrectnessOfUnit.
        Для дальнейших вычислений задаётся точность в 28 значащих цифр.
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
        """Преобразует входное значение value в число Decimal.

        Принимает строку или число. Сначала получает строковую запись значения,
        затем создаёт Decimal. Возвращает только конечное число: бесконечность
        и NaN запрещены. Неверное значение вызывает ErrorInCorrectnessOfNumericValue.
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
        """Проверяет название единицы unit и приводит его к нижнему регистру.

        Ищет единицу во всех группах загруженной таблицы. Если она найдена,
        возвращает её название маленькими буквами. Если аргумент не является
        строкой или единица неизвестна, вызывает ErrorInCorrectnessOfUnit.
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
        """Находит группу для единицы измерения unit.

        Ожидает уже проверенное название в нижнем регистре. Возвращает название
        группы, например «length» для метров. Если единицы нет в таблице,
        вызывает ErrorInCorrectnessOfUnit.
        """
        for group_name, group in self.units.items():
            if unit in group:
                return group_name

        raise ErrorInCorrectnessOfUnit(
            f"Unknown unit: {unit!r}"
        )

    def _checking_compatibility_of_units(self, from_unit: str, to_unit: str) -> str:
        """Проверяет, можно ли перевести from_unit в to_unit.

        Находит группы исходной и конечной единиц. Если группы совпадают,
        возвращает название общей группы. Если они разные, вызывает
        ErrorInCompatibilityOfUnits: например, метры нельзя перевести в килограммы.
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
        """Выполняет перевод между двумя проверенными единицами.

        value содержит исходное число Decimal, from_unit и to_unit — названия
        единиц, group — их общую группу. Сначала переводит значение в базовую
        единицу группы, затем в нужную, используя коэффициенты из таблицы.
        Возвращает Decimal. Для температуры проверяет нижнюю границу
        и при её нарушении вызывает ErrorInTemperatureBelowAbsoluteZero.
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
        """Проверяет данные и возвращает результат конвертации как float.

        Принимает значение value, исходную единицу from_unit и конечную to_unit.
        Проверяет число, названия и совместимость единиц. Вычисляет результат
        через Decimal с точностью 28 цифр и округлением к ближайшей чётной цифре
        при равном расстоянии. Переполнение и ошибки Decimal превращает
        в ErrorInCorrectnessOfNumericValue. Ошибки единиц и температуры
        передаются вызывающему коду.
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
