from src.constants import OPERATOR_PRECEDENCE
from src.errors import CalculatorError

Token = int | float | str


def tokenize(expression: str) -> list[Token]:
    if not expression or not expression.strip():
        raise CalculatorError("empty expression")

    tokens: list[Token] = []
    index = 0

    while index < len(expression):
        character = expression[index]

        if character.isspace():
            index += 1
            continue

        if character in "+-*/()":
            tokens.append(character)
            index += 1
            continue

        if character.isdigit() or character == ".":
            start = index
            has_dot = False

            while index < len(expression) and (
                expression[index].isdigit() or expression[index] == "."
            ):
                if expression[index] == ".":
                    if has_dot:
                        raise CalculatorError("invalid number")
                    has_dot = True
                index += 1

            number = expression[start:index]
            if number == ".":
                raise CalculatorError("invalid number")

            try:
                tokens.append(float(number) if "." in number else int(number))
            except ValueError as error:
                raise CalculatorError("invalid number") from error
            continue

        raise CalculatorError("invalid character")

    return tokens


def validate(tokens: list[Token]) -> None:
    if not tokens:
        raise CalculatorError("empty expression")

    balance = 0
    expect_operand = True

    for token in tokens:
        if expect_operand:
            if isinstance(token, (int, float)):
                expect_operand = False
            elif token in ("+", "-"):
                continue
            elif token == "(":
                balance += 1
            else:
                raise CalculatorError("missing operand")
        elif token in ("+", "-", "*", "/"):
            expect_operand = True
        elif token == ")":
            balance -= 1
            if balance < 0:
                raise CalculatorError("mismatched parentheses")
        else:
            raise CalculatorError("missing operator")

    if expect_operand:
        raise CalculatorError("missing operand")
    if balance != 0:
        raise CalculatorError("mismatched parentheses")


def _to_rpn(tokens: list[Token]) -> list[Token]:
    output: list[Token] = []
    operators: list[str] = []

    for index, token in enumerate(tokens):
        if isinstance(token, (int, float)):
            output.append(token)
        elif token == "(":
            operators.append(token)
        elif token == ")":
            while operators and operators[-1] != "(":
                output.append(operators.pop())
            if not operators:
                raise CalculatorError("mismatched parentheses")
            operators.pop()
        elif token in ("+", "-", "*", "/"):
            is_unary = token in ("+", "-") and (
                index == 0
                or isinstance(tokens[index - 1], str)
                and tokens[index - 1] in ("+", "-", "*", "/", "(")
            )
            operator = f"u{token}" if is_unary else token

            if is_unary:
                while (
                    operators
                    and operators[-1] in OPERATOR_PRECEDENCE
                    and OPERATOR_PRECEDENCE[operators[-1]]
                    > OPERATOR_PRECEDENCE[operator]
                ):
                    output.append(operators.pop())
            else:
                while (
                    operators
                    and operators[-1] in OPERATOR_PRECEDENCE
                    and OPERATOR_PRECEDENCE[operators[-1]]
                    >= OPERATOR_PRECEDENCE[operator]
                ):
                    output.append(operators.pop())
            operators.append(operator)
        else:
            raise CalculatorError("invalid token")

    while operators:
        if operators[-1] == "(":
            raise CalculatorError("mismatched parentheses")
        output.append(operators.pop())

    return output


def _eval_rpn(tokens: list[Token]) -> float:
    values: list[float] = []

    for token in tokens:
        if isinstance(token, (int, float)):
            values.append(float(token))
        elif token in ("u-", "u+"):
            if not values:
                raise CalculatorError("missing operand")
            value = values.pop()
            values.append(-value if token == "u-" else value)
        elif token in ("+", "-", "*", "/"):
            if len(values) < 2:
                raise CalculatorError("missing operand")
            right = values.pop()
            left = values.pop()
            if token == "+":
                values.append(left + right)
            elif token == "-":
                values.append(left - right)
            elif token == "*":
                values.append(left * right)
            elif right == 0:
                raise CalculatorError("division by zero")
            else:
                values.append(left / right)
        else:
            raise CalculatorError("invalid token")

    if len(values) != 1:
        raise CalculatorError("invalid expression")
    return values[0]


def calculate(expression: str) -> float:
    tokens = tokenize(expression)
    validate(tokens)
    return _eval_rpn(_to_rpn(tokens))
