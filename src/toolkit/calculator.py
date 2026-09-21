from toolkit.errors import CalculatorError


def tokenize(expression: str) -> list:
    if not expression or not expression.strip():
        raise CalculatorError("empty expression")
    tokens = []
    i = 0
    n = len(expression)
    while i < n:
        c = expression[i]
        if c.isspace():
            i += 1
            continue
        if c in "+-*/":
            tokens.append(c)
            i += 1
            continue
        if c.isdigit() or c == ".":
            start = i
            has_dot = False
            while i < n and (expression[i].isdigit() or expression[i] == "."):
                if expression[i] == ".":
                    if has_dot:
                        raise CalculatorError("invalid number")
                    has_dot = True
                i += 1
            num_str = expression[start:i]
            if num_str == "." or (num_str.startswith(".") and len(num_str) == 1):
                raise CalculatorError("invalid number")
            try:
                if "." in num_str:
                    tokens.append(float(num_str))
                else:
                    tokens.append(int(num_str))
            except ValueError:
                raise CalculatorError("invalid number")
            continue
        raise CalculatorError("invalid character")
    return tokens


def validate(tokens: list) -> None:
    if not tokens:
        raise CalculatorError("empty expression")
    i = 0
    expect_operand = True
    while i < len(tokens):
        token = tokens[i]
        if expect_operand:
            if isinstance(token, (int, float)):
                expect_operand = False
                i += 1
            elif isinstance(token, str) and token in "+-":
                i += 1
            else:
                raise CalculatorError("missing operand")
        else:
            if isinstance(token, str) and token in "+-*/":
                expect_operand = True
                i += 1
            else:
                raise CalculatorError("missing operator")
    if expect_operand:
        raise CalculatorError("missing operand")


def _to_rpn(tokens: list) -> list:
    output = []
    stack = []
    precedence = {"+": 1, "-": 1, "*": 2, "/": 2, "u+": 3, "u-": 3}
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if isinstance(token, (int, float)):
            output.append(token)
            i += 1
        elif isinstance(token, str) and token in "+-*/":
            is_unary = False
            if token in "+-":
                if i == 0:
                    is_unary = True
                else:
                    prev = tokens[i - 1]
                    if isinstance(prev, str) and prev in "+-*/":
                        is_unary = True
            if is_unary:
                op = "u" + token
                while stack and stack[-1] in precedence and precedence[stack[-1]] > precedence[op]:
                    output.append(stack.pop())
                stack.append(op)
                i += 1
            else:
                while stack and stack[-1] in precedence and precedence[stack[-1]] >= precedence[token]:
                    output.append(stack.pop())
                stack.append(token)
                i += 1
        else:
            raise CalculatorError("invalid token")
    while stack:
        output.append(stack.pop())
    return output


def _eval_rpn(rpn: list) -> float:
    stack = []
    for token in rpn:
        if isinstance(token, (int, float)):
            stack.append(float(token))
        elif token == "u-":
            if not stack:
                raise CalculatorError("missing operand")
            stack.append(-stack.pop())
        elif token == "u+":
            if not stack:
                raise CalculatorError("missing operand")
            stack.append(+stack.pop())
        elif token in "+-*/":
            if len(stack) < 2:
                raise CalculatorError("missing operand")
            b = stack.pop()
            a = stack.pop()
            if token == "+":
                stack.append(a + b)
            elif token == "-":
                stack.append(a - b)
            elif token == "*":
                stack.append(a * b)
            elif token == "/":
                if b == 0:
                    raise CalculatorError("division by zero")
                stack.append(a / b)
        else:
            raise CalculatorError("invalid token")
    if len(stack) != 1:
        raise CalculatorError("invalid expression")
    return stack[0]


def calculate(expression: str) -> float:
    tokens = tokenize(expression)
    validate(tokens)
    rpn = _to_rpn(tokens)
    return _eval_rpn(rpn)
