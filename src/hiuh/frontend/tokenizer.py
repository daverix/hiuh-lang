# -*- coding: utf-8 -*-

# Token type constants
TOKEN_PRINT = 1
TOKEN_SET = 2
TOKEN_TO = 3
TOKEN_FUNC = 4
TOKEN_WITH = 5
TOKEN_GIVE = 6
TOKEN_TYPE = 7
TOKEN_IN = 8
TOKEN_FROM = 9
TOKEN_IF = 10
TOKEN_ELSE = 11
TOKEN_TRY = 12
TOKEN_THROW = 13
TOKEN_CATCH = 14
TOKEN_WHILE = 15
TOKEN_IMPORT = 16
TOKEN_OPEN = 17
TOKEN_CLOSE = 18
TOKEN_AS = 19
TOKEN_GREATER = 20
TOKEN_LESS = 21
TOKEN_EQUAL = 22
TOKEN_THAN = 23
TOKEN_OR = 24
TOKEN_AND = 25
TOKEN_OP_ADD = 26
TOKEN_OP_SUB = 27
TOKEN_OP_MUL = 28
TOKEN_OP_DIV = 29
TOKEN_OP_IS = 30
TOKEN_LITERAL_INT = 31
TOKEN_LITERAL_FLOAT = 32
TOKEN_LITERAL_TRUE = 33
TOKEN_LITERAL_FALSE = 34
TOKEN_STRING = 35
TOKEN_IDENTIFIER = 36
TOKEN_NEWLINE = 37
TOKEN_INDENT = 38
TOKEN_DEDENT = 39
TOKEN_COMMA = 40
TOKEN_EOF = 42
TOKEN_COPY = 43
TOKEN_OF = 44
TOKEN_INFIX = 45

class Token:
    def __init__(self, type, value, line, column):
        self.type = type
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self):
        return f"Token({self.type}, {repr(self.value)}, {self.line}, {self.column})"

    def __eq__(self, other):
        if not isinstance(other, Token):
            return False
        return (self.type == other.type and self.value == other.value and
                self.line == other.line and self.column == other.column)

class Tokenizer:
    def __init__(self):
        self.keywords = {
            "skriv": TOKEN_PRINT,
            "sätt": TOKEN_SET,
            "till": TOKEN_TO,
            "grej": TOKEN_FUNC,
            "med": TOKEN_WITH,
            "ge": TOKEN_GIVE,
            "typ": TOKEN_TYPE,
            "från": TOKEN_FROM,
            "om": TOKEN_IF,
            "är": TOKEN_OP_IS,
            "större": TOKEN_GREATER,
            "mindre": TOKEN_LESS,
            "än": TOKEN_THAN,
            "lika": TOKEN_EQUAL,
            "annars": TOKEN_ELSE,
            "försök": TOKEN_TRY,
            "kasta": TOKEN_THROW,
            "fånga": TOKEN_CATCH,
            "gånger": TOKEN_OP_MUL,
            "plus": TOKEN_OP_ADD,
            "minus": TOKEN_OP_SUB,
            "delat": TOKEN_OP_DIV,
            "eller": TOKEN_OR,
            "och": TOKEN_AND,
            "medan": TOKEN_WHILE,
            "använd": TOKEN_IMPORT,
            "öppna": TOKEN_OPEN,
            "stäng": TOKEN_CLOSE,
            "som": TOKEN_AS,
            "kopia": TOKEN_COPY,
            "av": TOKEN_OF,
            "infix": TOKEN_INFIX
        }

    def is_digit(self, char):
        return '0' <= char <= '9'

    def tokenize(self, code):
        tokens = []
        lines = code.split('\n')
        indent_stack = [0]

        for line_idx, line in enumerate(lines, 1):
            stripped_line = line.strip()
            if not stripped_line or stripped_line.startswith('.'):
                continue  # Skip empty lines and comments

            indent = 0
            while indent < len(line) and line[indent] == ' ':
                indent += 1

            content = line[indent:]

            if indent > indent_stack[-1]:
                tokens.append(Token(TOKEN_INDENT, " " * indent, line_idx, 1))
                indent_stack.append(indent)
            elif indent < indent_stack[-1]:
                while indent < indent_stack[-1]:
                    indent_stack.pop()
                    tokens.append(Token(TOKEN_DEDENT, "", line_idx, 1))

            i = 0
            while i < len(content):
                char = content[i]
                if char == ' ':
                    i += 1
                    continue

                if char == ',':
                    tokens.append(Token(TOKEN_COMMA, ",", line_idx, indent + i + 1))
                    i += 1
                    continue

                if char in ['"', "'"]:
                    quote_char = char
                    start = i
                    i += 1  # Skip the opening quote

                    while i < len(content) and content[i] != quote_char:
                        i += 1

                    if i >= len(content):
                        raise SyntaxError(f"Oavslutad textsträng på rad {line_idx}")

                    # Extract the contents without the quote characters
                    val = content[start + 1 : i]
                    i += 1  # Skip the closing quote

                    tokens.append(Token(TOKEN_STRING, val, line_idx, indent + start + 1))
                    continue

                if self.is_digit(char) or (char == '-' and i + 1 < len(content) and self.is_digit(content[i + 1])):
                    start = i
                    has_comma = False
                    # Handle negative numbers
                    if char == '-':
                        i += 1  # Skip the minus
                    while i < len(content):
                        if content[i] == ',':
                            if (i + 1) < len(content) and self.is_digit(content[i+1]):
                                has_comma = True
                                i += 1
                            else:
                                break
                        elif self.is_digit(content[i]):
                            i += 1
                        else:
                            break
                    val = content[start:i]
                    t_type = TOKEN_LITERAL_FLOAT if has_comma else TOKEN_LITERAL_INT
                    tokens.append(Token(t_type, val, line_idx, indent + start + 1))
                    continue

                start = i
                while i < len(content) and not content[i].isspace() and content[i] not in [',', '"', "'"]:
                    i += 1

                val = content[start:i]

                if val.upper() == "SANT":
                    t_type = TOKEN_LITERAL_TRUE
                elif val.upper() == "FALSKT":
                    t_type = TOKEN_LITERAL_FALSE
                else:
                    t_type = self.keywords.get(val.lower(), TOKEN_IDENTIFIER)

                tokens.append(Token(t_type, val, line_idx, indent + start + 1))

            if line_idx < len(lines):
                tokens.append(Token(TOKEN_NEWLINE, "\n", line_idx, len(line) + 1))

        while len(indent_stack) > 1:
            indent_stack.pop()
            tokens.append(Token(TOKEN_DEDENT, "", len(lines) + 1, 1))

        return tokens
