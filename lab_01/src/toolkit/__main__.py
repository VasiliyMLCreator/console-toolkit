import argparse
import json
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from .calculator import Calculator
from .converter import Converter
from .errors import GeneralApplicationErrorClass


def configuration_for_calculator(subparsers) -> None:
    """Добавляет подкоманду calc с одним аргументом: выражением."""
    calc_parser = subparsers.add_parser(
        "calc",
        description="Calculating a numeric expression"
    )

    calc_parser.add_argument(
        "expression",
        help="Numeric expression with arithmetic operators and parentheses"
    )


def configuration_for_converter(subparsers) -> None:
    """Добавляет подкоманду convert: число, обязательные --from и --to и
    необязательный --config с путём к таблице единиц.
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
    """Дописывает record в историю ~/toolkit_history.json.

    Новый список сначала пишется во временный файл, потом тот заменяет
    основной, так что при сбое старая история не пострадает. Если файл истории
    повреждён или запись не удалась, бросает ошибку приложения.
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
    """Запускает calc или convert, смотря что указано в args, и печатает
    результат.

    Запись в историю делается, если не передан --no-history. Ошибки не ловит:
    это работа main.
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
    """Разбирает аргументы и запускает команду.

    arguments - список без имени программы, по умолчанию берётся sys.argv.
    Выражения и числа, начинающиеся с минуса, подготавливаются так, чтобы
    argparse не принял их за флаги.

    При успехе возвращает 0. При ошибке сообщение уходит в stderr, а процесс
    завершается с кодом 2 через SystemExit. Справка завершается с кодом 0.
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
