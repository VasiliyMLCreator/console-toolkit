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
    """Выражения из таблицы дают ожидаемый Decimal."""
    result = Calculator()(expression)

    assert isinstance(result, Decimal)
    assert result == Decimal(expected)


@pytest.mark.parametrize(
    "expression",
    ["", " \t\n", "2a+3", "1+", "*2", "2 ** 3", "2 / * 3", "1..2", ".",
     "1 2", "()", "(1+2", "1+2)", "2(3)", "(2)3", "(1+)2", "1e3"]
)
def test_invalid_expression(expression: str) -> None:
    """Неправильная запись выражения даёт ErrorInCorrectnessOfNumericExpression.
    """
    with pytest.raises(ErrorInCorrectnessOfNumericExpression):
        Calculator()(expression)


@pytest.mark.parametrize("operator", ["/", "//", "%"])
def test_division_by_zero(operator: str) -> None:
    """Деление на ноль через /, // и % даёт ZeroDivisionError.

    Нулевой делитель получается из выражения (1 - 1).
    """
    with pytest.raises(ZeroDivisionError):
        Calculator()(f"2 {operator} (1 - 1)")


def test_recursive_descent_produces_reverse_polish_notation() -> None:
    """Выражение со скобками превращается в ожидаемую обратную польскую запись, а
    подсчёт стеком даёт верный результат.
    """
    calculator = Calculator()
    tokens = calculator._tokenization("-(2 + 3) * 4")

    assert calculator._validation(tokens)

    result = calculator._conversion_to_reverse_polish_notation(tokens)

    assert [token.value for token in result] == ["2", "3", "+", "u-", "4", "*"]
    assert calculator._calculation(result) == Decimal(-20)


def test_rounding_is_independent_of_external_context() -> None:
    """Калькулятор использует свои точность и округление, а не внешние настройки
    Decimal.

    Для проверки временно ставятся точность 3 и ROUND_DOWN. После вызова эти
    настройки должны остаться прежними.
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
    """На ровной середине округление идёт к ближайшей чётной цифре.

    В одном примере последняя цифра остаётся, в другом растёт.
    """
    assert Calculator()(expression) == Decimal(expected)


def test_excessive_nesting() -> None:
    """Две тысячи вложенных скобок дают ошибку выражения, а не необработанный
    RecursionError.
    """
    with pytest.raises(ErrorInCorrectnessOfNumericExpression):
        Calculator()("(" * 2000 + "1" + ")" * 2000)
