# Шкуратов Василий Сергеевич (М8О-101БВ-26) — Console toolkit

Консольный набор утилит для вычислений и перевода единиц измерения.

## Установка

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Использование

Калькулятор:

```bash
python -m src calc "2+3*4"
```

Конвертер:

```bash
python -m src convert 1000 --from mm --to m
```

Справка:

```bash
python -m src --help
```

После установки также доступна команда `toolkit`.

## Структура

- `src/main.py` — точка входа и обработка аргументов
- `src/calculator.py` — вычисление арифметических выражений
- `src/converter.py` — перевод единиц измерения
- `src/constants.py` — константы
- `src/errors.py` — ошибки приложения
- `tests/` — тесты

## Тесты

```bash
python -m pytest
```
