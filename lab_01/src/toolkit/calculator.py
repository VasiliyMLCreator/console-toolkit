from decimal import ROUND_HALF_EVEN, Decimal, DecimalException, localcontext

from .errors import ErrorInCorrectnessOfNumericExpression


class Token:
    """Одна часть выражения: число, знак операции или скобка.

    value - текст токена, type - его вид, например number или binary_operator.
    """
    def __init__(self, value: str, token_type: str) -> None:
        """Запоминает текст токена и его тип."""
        self.value: str = value
        self.type: str = token_type


class Calculator:
    """Вычисляет выражение, записанное строкой.

    Понимает скобки, операции + - * / // % и унарные + и -. Возвращает Decimal,
    ничего не печатает и не пишет в файлы.
    """
    def __init__(self) -> None:
        """Задаёт допустимые символы, приоритеты и ассоциативность операций.

        Точность - 28 значащих цифр. Округление ROUND_HALF_EVEN: на ровной
        середине выбирается ближайшая чётная цифра.
        """
        self.acceptable_characters: str = "0123456789+-*/%(). \t\n"

        self.operator_priorities: dict[str, int] = {
            "+": 1,
            "-": 1,
            "*": 2,
            "/": 2,
            "//": 2,
            "%": 2,
            "u+": 3,
            "u-": 3
        }

        self.operator_associativity: dict[str, str] = {
            "+": "left",
            "-": "left",
            "*": "left",
            "/": "left",
            "//": "left",
            "%": "left",
            "u+": "right",
            "u-": "right"
        }

        self.decimal_precision: int = 28
        self.decimal_rounding: str = ROUND_HALF_EVEN

    def _searching_for_erroneous_substrings_of_characters(self, tokens: list[Token]) -> bool:
        """Проверяет, что числа и операции идут в правильном порядке.

        После бинарной операции должно быть число, унарный знак или открывающая
        скобка. Возвращает True, если порядок верный. Парность скобок
        проверяется отдельно.
        """
        if not tokens:
            return False

        expect_operand: bool = True

        for token in tokens:
            if expect_operand:
                if token.type == "number":
                    expect_operand = False

                elif token.type == "unary_operator" or token.type == "left_parenthesis":
                    continue

                else:
                    return False

            else:
                if token.type == "binary_operator":
                    expect_operand = True

                elif token.type == "right_parenthesis":
                    continue

                else:
                    return False

        return not expect_operand

    def _checking_correctness_of_parenthesis_sequence(self, tokens: list[Token]) -> bool:
        """Возвращает True, если у каждой скобки есть пара."""
        stack: list[str] = []

        for token in tokens:
            if token.type == "left_parenthesis":
                stack.append(token.value)

            elif token.type == "right_parenthesis":
                if not stack:
                    return False

                stack.pop()

        return len(stack) == 0

    def _checking_correctness_of_number(self, value: str) -> bool:
        """Проверяет запись одного числа: цифры и не больше одной точки.

        Пустая строка и одиночная точка не подходят. Знак здесь не проверяется,
        он отдельный токен.
        """
        if not value:
            return False

        if value.count(".") > 1:
            return False

        if value == ".":
            return False

        for char in value:
            if char not in "0123456789.":
                return False

        return True

    def _tokenization(self, expression: str) -> list[Token]:
        """Режет expression на токены.

        Числа собираются из цифр и точки, пробелы пропускаются. + и - в начале,
        после операции или после ( становятся унарными. Незнакомые символы
        получают тип unknown, их отловит _validation. Ничего не вычисляет.
        """
        tokens: list[Token] = []
        current_number: str = ""
        index: int = 0

        while index < len(expression):
            char: str = expression[index]

            if char not in self.acceptable_characters:
                tokens.append(Token(char, "unknown"))
                index += 1
                continue

            if char.isdigit() or char == ".":
                current_number += char
                index += 1
                continue

            if current_number:
                tokens.append(Token(current_number, "number"))
                current_number = ""

            if char.isspace():
                index += 1
                continue

            if char == "(":
                tokens.append(Token(char, "left_parenthesis"))

            elif char == ")":
                tokens.append(Token(char, "right_parenthesis"))

            elif char in "+-":
                if not tokens or tokens[-1].type in (
                    "binary_operator",
                    "unary_operator",
                    "left_parenthesis"
                ):
                    tokens.append(Token(f"u{char}", "unary_operator"))

                else:
                    tokens.append(Token(char, "binary_operator"))

            elif char in "*/%":
                if char == "/" and index + 1 < len(expression):
                    if expression[index + 1] == "/":
                        tokens.append(Token("//", "binary_operator"))
                        index += 1

                    else:
                        tokens.append(Token("/", "binary_operator"))

                else:
                    tokens.append(Token(char, "binary_operator"))

            index += 1

        if current_number:
            tokens.append(Token(current_number, "number"))

        return tokens

    def _validation(self, tokens: list[Token]) -> bool | None:
        """Проверяет токены перед вычислением.

        Выражение не пустое, символы и числа допустимы, операнды и скобки стоят
        правильно. Возвращает True или бросает
        ErrorInCorrectnessOfNumericExpression.
        """
        if not tokens:
            raise ErrorInCorrectnessOfNumericExpression("The numeric expression is empty")

        for token in tokens:
            if token.type == "unknown":
                raise ErrorInCorrectnessOfNumericExpression(
                    f"Unknown character in numeric expression: {token.value!r}"
                )

            if token.type == "number" and not self._checking_correctness_of_number(token.value):
                raise ErrorInCorrectnessOfNumericExpression(
                    f"Invalid number: {token.value!r}"
                )

        if not self._searching_for_erroneous_substrings_of_characters(tokens):
            raise ErrorInCorrectnessOfNumericExpression(
                "Invalid sequence of operands and operators"
            )

        if not self._checking_correctness_of_parenthesis_sequence(tokens):
            raise ErrorInCorrectnessOfNumericExpression(
                "Unbalanced parentheses in numeric expression"
            )

        return True

    def _conversion_to_reverse_polish_notation(self, tokens: list[Token]) -> list[Token]:
        """Переводит токены в обратную польскую запись.

        Знак в ней стоит после своих чисел: «2 + 3» превращается в «2 3 +».
        Разбор идёт рекурсивным спуском с учётом приоритетов и скобок. При
        слишком глубокой вложенности бросает
        ErrorInCorrectnessOfNumericExpression.
        """
        output: list[Token] = []
        index: int = 0

        def parsing_operand() -> None:
            """Разбирает число, унарный знак с его операндом или выражение в
            скобках.

            Результат дописывается в output, index сдвигается.
            """
            nonlocal index

            token: Token = tokens[index]
            index += 1

            if token.type == "unary_operator":
                parsing_operand()
                output.append(token)

            elif token.type == "left_parenthesis":
                parsing_expression(1)
                index += 1

            else:
                output.append(token)

        def parsing_expression(minimum_priority: int) -> None:
            """Разбирает операции с приоритетом не ниже minimum_priority.

            Правый операнд разбирается рекурсивно с приоритетом на единицу
            выше. Поэтому умножение выполняется раньше сложения, а операции
            одного приоритета идут слева направо. Пишет в output, сдвигает
            index.
            """
            nonlocal index

            parsing_operand()

            while index < len(tokens):
                token: Token = tokens[index]

                if token.type != "binary_operator":
                    break

                priority: int = self.operator_priorities[token.value]

                if priority < minimum_priority:
                    break

                index += 1
                parsing_expression(priority + 1)
                output.append(token)

        try:
            parsing_expression(1)

        except RecursionError as error:
            raise ErrorInCorrectnessOfNumericExpression(
                "The numeric expression is nested too deeply"
            ) from error

        return output

    def _checking_correctness_of_reverse_polish_notation(self, tokens: list[Token]) -> bool:
        """Проверяет без вычислений, что запись можно посчитать.

        Каждой операции должно хватать чисел, а в конце должно остаться ровно
        одно. Возвращает True или False.
        """
        operands_count: int = 0

        for token in tokens:
            if token.type == "number":
                operands_count += 1

            elif token.type == "unary_operator":
                if operands_count < 1:
                    return False

            elif token.type == "binary_operator":
                if operands_count < 2:
                    return False

                operands_count -= 1

            else:
                return False

        return operands_count == 1

    def _calculation(self, tokens: list[Token]) -> Decimal:
        """Считает обратную польскую запись стеком.

        Числа кладутся в стек, операция берёт нужные числа и кладёт обратно
        результат. // округляет вниз, у % знак делителя. Возвращает Decimal.
        Деление на ноль даёт ZeroDivisionError, испорченная запись - ошибку
        выражения.
        """
        stack: list[Decimal] = []

        for token in tokens:
            if token.type == "number":
                stack.append(Decimal(token.value))
                continue

            if token.type == "unary_operator":
                if not stack:
                    raise ErrorInCorrectnessOfNumericExpression(
                        "A unary operator has no operand"
                    )

                number: Decimal = stack.pop()

                if token.value == "u+":
                    stack.append(+number)

                elif token.value == "u-":
                    stack.append(-number)

                else:
                    raise ErrorInCorrectnessOfNumericExpression(
                        f"Unknown unary operator: {token.value!r}"
                    )

                continue

            if token.type == "binary_operator":
                if len(stack) < 2:
                    raise ErrorInCorrectnessOfNumericExpression(
                        "A binary operator does not have enough operands"
                    )

                second_number: Decimal = stack.pop()
                first_number: Decimal = stack.pop()

                if token.value == "+":
                    result: Decimal = first_number + second_number

                elif token.value == "-":
                    result = first_number - second_number

                elif token.value == "*":
                    result = first_number * second_number

                elif token.value == "/":
                    if second_number == 0:
                        raise ZeroDivisionError("Division by zero")

                    result = first_number / second_number

                elif token.value == "//":
                    if second_number == 0:
                        raise ZeroDivisionError("Division by zero")

                    result = first_number // second_number

                    if first_number % second_number and (first_number < 0) != (second_number < 0):
                        result -= 1

                elif token.value == "%":
                    if second_number == 0:
                        raise ZeroDivisionError("Division by zero")

                    result = first_number % second_number

                    if result and (first_number < 0) != (second_number < 0):
                        result += second_number

                else:
                    raise ErrorInCorrectnessOfNumericExpression(
                        f"Unknown binary operator: {token.value!r}"
                    )

                stack.append(result)
                continue

            raise ErrorInCorrectnessOfNumericExpression(
                "Unknown token in reverse Polish notation"
            )

        if len(stack) != 1:
            raise ErrorInCorrectnessOfNumericExpression(
                "The calculation did not produce exactly one result"
            )

        return +stack[0]

    def __call__(self, expression: str) -> Decimal:
        """Вычисляет expression, так что Calculator()("2 + 3") работает как
        функция.

        По шагам: токены, проверка, обратная польская запись, подсчёт. Ошибки
        Decimal превращаются в ошибку выражения. Настройки Decimal за пределами
        вызова не меняются.
        """
        tokens: list[Token] = self._tokenization(expression)

        self._validation(tokens)

        reverse_polish_notation: list[Token] = self._conversion_to_reverse_polish_notation(tokens)

        if not self._checking_correctness_of_reverse_polish_notation(reverse_polish_notation):
            raise ErrorInCorrectnessOfNumericExpression(
                "Invalid reverse Polish notation"
            )

        try:
            with localcontext() as context:
                context.prec = self.decimal_precision
                context.rounding = self.decimal_rounding

                result: Decimal = self._calculation(reverse_polish_notation)

                return result

        except DecimalException as error:
            raise ErrorInCorrectnessOfNumericExpression(
                "Decimal calculation failed"
            ) from error
