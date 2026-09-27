import argparse
import sys

from src.calculator import calculate
from src.converter import convert
from src.errors import ToolkitError


def main() -> None:
    parser = argparse.ArgumentParser(prog="toolkit")
    subparsers = parser.add_subparsers(dest="command")

    calculator_parser = subparsers.add_parser("calc")
    calculator_parser.add_argument("expression")

    converter_parser = subparsers.add_parser("convert")
    converter_parser.add_argument("value", type=float)
    converter_parser.add_argument("--from", dest="from_unit", required=True)
    converter_parser.add_argument("--to", dest="to_unit", required=True)

    arguments = parser.parse_args()

    if arguments.command is None:
        parser.print_help()
        return

    try:
        if arguments.command == "calc":
            result = calculate(arguments.expression)
        else:
            result = convert(arguments.value, arguments.from_unit, arguments.to_unit)
        print(result)
    except ToolkitError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2) from error
