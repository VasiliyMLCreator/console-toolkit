# Шкуратов Василий Сергеевич (М8О-101БВ-26) - Console toolkit

Простой набор утилит: калькулятор и конвертер величин.

## Установка

```bash
pip install -e .
```

## Использование

Калькулятор:

```bash
python -m toolkit calc "2+3*4"
```

Конвертер:

```bash
python -m toolkit convert 1000 --from mm --to m
```

Справка:

```bash
python -m toolkit --help
```

## Структура

- src/toolkit/calculator.py - калькулятор
- src/toolkit/converter.py - конвертер
- src/toolkit/errors.py - ошибки
- tests/ - тесты

## Тесты

```bash
python -m pytest
```
