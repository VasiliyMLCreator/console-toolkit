class GeneralApplicationErrorClass(Exception):
    """Базовая ошибка приложения.

    От неё наследуются ошибки калькулятора, конвертера и сохранения истории,
    поэтому CLI ловит их одним except и печатает понятное сообщение.
    """


class GeneralErrorClassOfCalculatorModule(GeneralApplicationErrorClass):
    """Общий родитель ошибок калькулятора."""


class GeneralErrorClassOfConverterModule(GeneralApplicationErrorClass):
    """Общий родитель ошибок конвертера."""


class ErrorInCorrectnessOfNumericExpression(GeneralErrorClassOfCalculatorModule):
    """Выражение нельзя вычислить.

    Причины: пустая строка, лишний символ, пропущенное число, неправильные
    скобки, слишком глубокая вложенность или сбой Decimal.
    """


class ErrorInCorrectnessOfNumericValue(GeneralErrorClassOfConverterModule):
    """Конвертер не принял значение.

    Оно не читается как число, бесконечно или равно NaN, либо результат не
    удалось посчитать или он не помещается во float.
    """


class ErrorInCorrectnessOfUnit(GeneralErrorClassOfConverterModule):
    """Единица неизвестна или передана не строкой.

    Та же ошибка бросается, если файл с таблицей единиц не читается или в нём
    не хватает данных.
    """


class ErrorInCompatibilityOfUnits(GeneralErrorClassOfConverterModule):
    """Единицы из разных групп, например метры и килограммы."""


class ErrorInTemperatureBelowAbsoluteZero(GeneralErrorClassOfConverterModule):
    """Температура ниже абсолютного нуля.

    В стандартной таблице это −273.15 °C, −459.67 °F или 0 K. Конвертер
    проверяет границу до самого перевода.
    """
