import argparse
import json
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from .calculator import Calculator
from .converter import Converter
from .errors import GeneralApplicationErrorClass


def configuration_for_calculator(subparsers) -> None:
    """Добавляет команду calc в общий обработчик командной строки.

    Принимает subparsers, созданный библиотекой argparse. Настраивает
    обязательный аргумент expression с математическим выражением
    и текст справки. Изменяет настройки обработчика и ничего не возвращает.
    """
    calc_parser = subparsers.add_parser(
        "calc",
        description="Calculating a numeric expression"
    )

    calc_parser.add_argument(
        "expression",
        help="Numeric expression with arithmetic operators and parentheses"
    )


def configuration_for_converter(subparsers) -> None:
    """Добавляет команду convert и её аргументы.

    Принимает общий обработчик подкоманд subparsers. Задаёт числовое значение,
    обязательные параметры --from и --to, а также необязательный --config
    для таблицы единиц. Только настраивает аргументы, не выполняя конвертацию.
    """
    conv_parser = subparsers.add_parser(
        "convert",
        description="Converting a numeric value from one unit to another"
    )

    conv_parser.add_argument("value", help="Numeric value")
    conv_parser.add_argument("--from", dest="from_unit", required=True, help="Source unit")
    conv_parser.add_argument("--to", dest="to_unit", required=True, help="Target unit")
    conv_parser.add_argument("--config", type=Path, help="Path to a JSON unit configuration")


def saving_successful_calculation(record: dict) -> None:
    """Добавляет запись record в общий JSON-файл истории пользователя.

    record — словарь с командой, исходными данными и результатом.
    Читает toolkit_history.json из домашнего каталога и дополняет список.
    Сначала записывает данные во временный файл, затем заменяет основной.
    При неверной истории или ошибке чтения и записи сообщает об ошибке
    приложения. После работы старается удалить временный файл.
    При успешном сохранении ничего не возвращает.
    """
    path: Path = Path.home() / "toolkit_history.json"
    temporary_path: Path | None = None

    try:
        history: list = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []

        if not isinstance(history, list) or not all(isinstance(item, dict) for item in history):
            raise ValueError("History must contain a list of records")

        history.append(record)
        path.parent.mkdir(parents=True, exist_ok=True)

        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(history, temporary_file, ensure_ascii=False, indent=4, allow_nan=False)
            temporary_file.write("\n")

        temporary_path.replace(path)

    except (OSError, ValueError) as error:
        raise GeneralApplicationErrorClass(f"Cannot save calculation history: {error}") from error

    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def router(args) -> None:
    """Запускает операцию, выбранную в аргументах командной строки.

    args содержит разобранные параметры: команду, входные данные и флаги.
    Для calc вызывает калькулятор, для convert — конвертер. Подготавливает
    запись истории и сохраняет её, если нет флага --no-history.
    Выводит результат на экран. Ошибки передаёт в main для обработки.
    """
    match args.mode:
        case "calc":
            calculator = Calculator()
            result = calculator(args.expression)
            record: dict = {
                "command": "calc",
                "expression": args.expression,
                "result": str(result)
            }

        case "convert":
            converter = Converter(args.config)
            result = converter(args.value, args.from_unit, args.to_unit)
            record = {
                "command": "convert",
                "value": args.value,
                "from": args.from_unit.lower(),
                "to": args.to_unit.lower(),
                "result": result
            }

    if not args.no_history:
        saving_successful_calculation(record)
    print(result)


def main(arguments: list[str] | None = None) -> int:
    """Подготавливает командную строку и запускает выбранную команду.

    arguments — список аргументов без имени программы. Если он не передан,
    аргументы берутся из sys.argv. Настраивает команды и флаг --no-history,
    учитывает отрицательные числа, затем вызывает router.
    При успехе возвращает 0. При ошибке argparse выводит сообщение в stderr
    и завершает выполнение через SystemExit с кодом 2. Справка завершает
    выполнение через SystemExit с кодом 0.
    """
    parser = argparse.ArgumentParser(
        prog="python -m toolkit",
        description="A utility for calculating numeric expressions and converting numeric values.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "--no-history",
        action="store_true",
        help="Do not save this operation to the history"
    )

    subparsers = parser.add_subparsers(dest="mode", required=True)
    configuration_for_calculator(subparsers)
    configuration_for_converter(subparsers)

    arguments = list(sys.argv[1:] if arguments is None else arguments)

    for index, argument in enumerate(arguments):
        if argument == "calc":
            if index + 1 < len(arguments) and arguments[index + 1] not in ("--help", "-h", "--"):
                arguments.insert(index + 1, "--")

            break

        if argument == "convert":
            if index + 1 < len(arguments):
                value: str = arguments[index + 1]

                if value.startswith("-") and value not in ("--help", "-h", "--from", "--to"):
                    arguments[index + 1] = " " + value

            break

    args = parser.parse_args(arguments)

    try:
        router(args)

    except (GeneralApplicationErrorClass, ZeroDivisionError, OSError) as error:
        parser.error(str(error))

    return 0


if __name__ == "__main__":
    sys.exit(main())
