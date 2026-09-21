import pytest
from toolkit.calculator import calculate, tokenize, validate
from toolkit.errors import CalculatorError


def test_simple_add():
    assert calculate("2+3") == 5.0


def test_mul_priority():
    assert calculate("2+3*4") == 14.0


def test_div():
    assert calculate("10 / 4") == 2.5


def test_unary_minus():
    assert calculate("-2 * -3") == 6.0


def test_unary_plus():
    assert calculate("+5-2") == 3.0


def test_spaces():
    assert calculate("  1  +  2  *  3  ") == 7.0


def test_float():
    assert calculate("1.5 * 2") == 3.0


def test_chain():
    assert calculate("1+2+3*4-5") == 10.0


def test_empty():
    with pytest.raises(CalculatorError):
        calculate("")


def test_invalid_char():
    with pytest.raises(CalculatorError):
        calculate("2+a")


def test_double_op():
    with pytest.raises(CalculatorError):
        calculate("2*/3")


def test_div_zero():
    with pytest.raises(CalculatorError):
        calculate("1/0")


def test_missing_operand():
    with pytest.raises(CalculatorError):
        calculate("2+")


def test_start_op():
    with pytest.raises(CalculatorError):
        calculate("*2")


def test_tokenize_validate():
    tokens = tokenize("2+3")
    validate(tokens)
    assert tokens == [2, "+", 3]
