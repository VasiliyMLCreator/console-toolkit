from decimal import ROUND_HALF_EVEN, Decimal, DecimalException, localcontext

from .errors import ErrorInCorrectnessOfNumericExpression


class Token:
    """Хранит одну часть математического выражения.

    Часть выражения называется токеном. Это может быть число, знак операции
    или скобка. Поле value содержит текст, а поле type показывает его вид.
    """
    def __init__(self, value: str, token_type: str) -> None:
        """Создаёт токен по его тексту и типу.

        В value передаётся строка, например «12» или «+». В token_type передаётся
        название типа, например «number». Метод сохраняет оба значения в объекте.
        """
        self.value: str = value
        self.type: str = token_type


class Calculator:
    """Вычисляет математические выражения, записанные строкой.

    Класс разбивает строку на части, проверяет их и определяет порядок действий.
    Поддерживаются скобки, обычные арифметические операции и знаки перед числами.
    Результат возвращается как Decimal, без вывода на экран и записи в файл.
    """
    def __init__(self) -> None:
        """Задаёт правила, по которым работает калькулятор.

        Сохраняет допустимые символы, приоритеты и направления выполнения операций.
        Устанавливает точность в 28 значащих цифр и округление к ближайшей чётной
        цифре, если число находится ровно посередине между двумя вариантами.
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
        """Проверяет порядок чисел, знаков операций и скобок в списке tokens.

        После бинарной операции, то есть операции с двумя числами, ожидается
        следующее число, его знак или открывающая скобка. Метод возвращает True,
        если порядок допустим, и False, если операнд пропущен или порядок нарушен.
        Правильность пар скобок проверяется отдельно.
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
        """Проверяет, что каждой открывающей скобке соответствует закрывающая.

        Принимает список tokens. Открывающие скобки складываются в список,
        а при встрече закрывающей убирается последняя открывающая.
        Возвращает False при лишней скобке и True, если все пары совпали.
        """
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
        """Проверяет запись одного числа в строке value.

        Разрешены цифры и не больше одной десятичной точки. Пустая строка,
        одиночная точка и посторонние символы дают False. Правильная запись даёт
        True. Знак числа здесь не проверяется, потому что он является отдельным токеном.
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
        """Разбивает строку expression на список токенов.

        Собирает цифры и точку в числа, выделяет операции и скобки.
        Пробелы между частями выражения пропускает. Отличает знак перед числом
        от сложения или вычитания. Неизвестные символы помечает для дальнейшей
        проверки. Возвращает список объектов Token, ещё не вычисляя результат.
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
        """Проверяет подготовленный список токенов перед вычислением.

        Проверяет, что выражение не пустое, символы и числа допустимы,
        операнды расположены правильно, а скобки образуют пары.
        При успехе возвращает True. При нарушении правил вызывает
        ErrorInCorrectnessOfNumericExpression с описанием проблемы.
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
        """Переводит проверенные токены в обратную польскую запись.

        В такой записи знак операции стоит после её чисел: «2 + 3» становится
        «2 3 +». Вложенные функции разбирают выражение с учётом приоритетов
        и скобок, вызывая друг друга при необходимости. Этот способ называется
        рекурсивным спуском. Метод возвращает новый список токенов.
        Слишком большая глубина вложенности приводит к ошибке выражения.
        """
        output: list[Token] = []
        index: int = 0

        def parsing_operand() -> None:
            """Разбирает очередное число, знак перед ним или выражение в скобках.

            Использует общий список tokens и текущую позицию index внешнего метода.
            Число добавляет в output сразу, а унарный знак — после его операнда.
            Для скобок запускает разбор выражения внутри них. Меняет index и output,
            но отдельного результата не возвращает.
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
            """Разбирает часть выражения с заданным минимальным приоритетом.

            Параметр minimum_priority определяет, какие операции нужно обработать
            на этом шаге. Сначала разбирается операнд, затем подходящие операции.
            Правая часть операции разбирается отдельным вызовом, чтобы умножение
            выполнялось раньше сложения. Функция дополняет общий список output
            и передвигает index, ничего не возвращая.
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
        """Проверяет, можно ли вычислить список tokens в обратной польской записи.

        Считает количество доступных чисел, не выполняя сами операции.
        Для унарного знака нужно одно число, для бинарной операции — два.
        Возвращает True, если чисел всегда хватает и в конце останется
        ровно один результат. В остальных случаях возвращает False.
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
        """Вычисляет результат по токенам в обратной польской записи.

        Использует стек — список, из которого первым берётся последний элемент.
        Числа кладёт в стек, а для операции достаёт нужные числа и возвращает
        в стек результат. Работает с Decimal и текущими настройками округления.
        Целочисленное деление округляет вниз, остаток получает знак делителя.
        Возвращает одно число Decimal. При делении на ноль вызывает
        ZeroDivisionError, а при неверной записи — ошибку выражения.
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
        """Вычисляет строку expression при вызове объекта как функции.

        Например, Calculator()(«2 + 3») запускает этот метод. Он последовательно
        разбивает строку, проверяет её, получает обратную польскую запись
        и вычисляет результат. Возвращает Decimal с точностью калькулятора.
        Ошибки работы Decimal превращает в ошибку выражения. Настройки Decimal
        за пределами этого вызова не меняются.
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
