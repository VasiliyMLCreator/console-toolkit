import pytest
from toolkit.converter import convert
from toolkit.errors import ConverterError


def test_length_mm_to_m():
    assert convert(1000, "mm", "m") == 1.0


def test_length_cm():
    assert convert(100, "cm", "m") == 1.0


def test_mass_kg_to_g():
    assert convert(1.5, "kg", "g") == 1500.0


def test_temp_c_to_f():
    assert convert(0, "c", "f") == 32.0


def test_temp_c_to_k():
    result = convert(-273.15, "c", "k")
    assert abs(result - 0.0) < 1e-9


def test_temp_f_to_c():
    assert convert(32, "f", "c") == 0.0


def test_case_insensitive():
    assert convert(1, "KM", "m") == 1000.0


def test_unknown_unit():
    with pytest.raises(ConverterError):
        convert(1, "xx", "m")


def test_incompatible():
    with pytest.raises(ConverterError):
        convert(1, "kg", "m")


def test_below_zero():
    with pytest.raises(ConverterError):
        convert(-274, "c", "k")
