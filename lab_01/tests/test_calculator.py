from decimal import ROUND_DOWN, Decimal, localcontext

import pytest

from toolkit import Calculator
from toolkit.errors import ErrorInCorrectnessOfNumericExpression


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("42", "42"),
        (".5 + 1.25", "1.75"),
        ("2 + 3 * 4", "14"),
        ("20 / 2 / 5", "2"),
        ("9 - 3 - 2", "4"),
        (" -2 * +3 + 8 ", "2"),
        ("2--3", "5"),
        ("2+-3", "-1"),
        ("\t2\n + 3", "5"),
        ("2 * (3 + (4 - 1))", "12"),
        ("-(2 + 3) * --2", "-10"),
        ("0.1 + 0.2", "0.3"),
        ("1 / 3", "0.3333333333333333333333333333"),
        ("-7 // 3", "-3"),
        ("7 // -3", "-3"),
        ("-7 // -3", "2"),
        ("-7 % 3", "2"),
        ("7 % -3", "-2"),
        ("-7 % -3", "-1"),
        ("5.5 % 2", "1.5"),
        ("-6 // 3", "-2"),
        ("-6 % 3", "0")
    ]
)
def test_calculation(expression: str, expected: str) -> None:
    """Проверяет правильные выражения из таблицы примеров.

    pytest передаёт expression и ожидаемый результат expected для каждого
    примера. Тест вызывает калькулятор напрямую и проверяет, что получено
    именно число Decimal с нужным значением.
    """
    result = Calculator()(expression)

    assert isinstance(result, Decimal)
    assert result == Decimal(expected)


@pytest.mark.parametrize(
    "expression",
    ["", " \t\n", "2a+3", "1+", "*2", "2 ** 3", "2 / * 3", "1..2", ".",
     "1 2", "()", "(1+2", "1+2)", "2(3)", "(2)3", "(1+)2", "1e3"]
)
def test_invalid_expression(expression: str) -> None:
    """Проверяет, что калькулятор отклоняет неправильную запись выражения.

    expression берётся из списка ошибочных примеров над функцией.
    Тест ожидает ErrorInCorrectnessOfNumericExpression. Если калькулятор
    не вызовет эту ошибку, проверка не пройдёт.
    """
    with pytest.raises(ErrorInCorrectnessOfNumericExpression):
        Calculator()(expression)


@pytest.mark.parametrize("operator", ["/", "//", "%"])
def test_division_by_zero(operator: str) -> None:
    """Проверяет запрет деления на ноль для трёх операций.

    В operator pytest передаёт /, // или %. Нулевой делитель получается
    из выражения в скобках. Для каждого варианта ожидается ZeroDivisionError.
    """
    with pytest.raises(ZeroDivisionError):
        Calculator()(f"2 {operator} (1 - 1)")


def test_recursive_descent_produces_reverse_polish_notation() -> None:
    """Проверяет порядок токенов после разбора выражения со скобками.

    Создаёт токены, проверяет их и переводит в обратную польскую запись.
    Сравнивает полученный порядок с заранее известным, а затем проверяет
    результат вычисления этой записи стеком.
    """
    calculator = Calculator()
    tokens = calculator._tokenization("-(2 + 3) * 4")

    assert calculator._validation(tokens)

    result = calculator._conversion_to_reverse_polish_notation(tokens)

    assert [token.value for token in result] == ["2", "3", "+", "u-", "4", "*"]
    assert calculator._calculation(result) == Decimal(-20)


def test_rounding_is_independent_of_external_context() -> None:
    """Проверяет независимость калькулятора от внешних настроек Decimal.

    Временно задаёт маленькую точность и другое округление. Проверяет,
    что калькулятор всё равно использует свои настройки, а после вызова
    внешняя точность и способ округления остаются прежними.
    """
    with localcontext() as context:
        context.prec = 3
        context.rounding = ROUND_DOWN

        assert Calculator()("1 / 6") == Decimal("0.1666666666666666666666666667")
        assert context.prec == 3
        assert context.rounding == ROUND_DOWN


@pytest.mark.parametrize(
    ("expression", "expected"),
    [("1.2345678901234567890123456785", "1.234567890123456789012345678"),
     ("1.2345678901234567890123456795", "1.234567890123456789012345680")]
)
def test_half_even_rounding(expression: str, expected: str) -> None:
    """Проверяет округление числа, находящегося ровно посередине.

    expression и expected задаются в таблице примеров. В одном случае
    последняя сохраняемая цифра должна остаться прежней, в другом —
    увеличиться, чтобы получилась чётная цифра.
    """
    assert Calculator()(expression) == Decimal(expected)


def test_excessive_nesting() -> None:
    """Проверяет обработку слишком большого количества вложенных скобок.

    Создаёт выражение с двумя тысячами пар скобок. Ожидает ошибку
    математического выражения вместо необработанной ошибки рекурсии.
    """
    with pytest.raises(ErrorInCorrectnessOfNumericExpression):
        Calculator()("(" * 2000 + "1" + ")" * 2000)
