# -*- coding: utf-8 -*-

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
            "skriv": "T_KEYWORD_PRINT",
            "sätt": "T_KEYWORD_SET",
            "till": "T_KEYWORD_TO",
            "grej": "T_KEYWORD_FUNC",
            "med": "T_KEYWORD_WITH",
            "ge": "T_KEYWORD_GIVE",
            "typ": "T_KEYWORD_TYPE",
            "i": "T_KEYWORD_IN",
            "från": "T_KEYWORD_FROM",
            "om": "T_KEYWORD_IF",
            "är": "T_OP_IS",
            "större": "T_KEYWORD_GREATER",
            "mindre": "T_KEYWORD_LESS",
            "än": "T_KEYWORD_THAN",
            "lika": "T_KEYWORD_EQUAL",
            "annars": "T_KEYWORD_ELSE",
            "försök": "T_KEYWORD_TRY",
            "kasta": "T_KEYWORD_THROW",
            "fånga": "T_KEYWORD_CATCH",
            "gånger": "T_OP_MUL",
            "plus": "T_OP_ADD",
            "minus": "T_OP_SUB",
            "delat": "T_OP_DIV",
            "eller": "T_OP_OR",
            "och": "T_OP_AND",
            "medan": "T_KEYWORD_WHILE"
        }

    def is_alpha(self, char):
        return 'a' <= char <= 'z' or 'A' <= char <= 'Z' or char in 'åäöÅÄÖ'

    def is_digit(self, char):
        return '0' <= char <= '9'

    def tokenize(self, code):
        tokens = []
        lines = code.split('\n')
        indent_stack = [0]

        for line_idx, line in enumerate(lines, 1):
            if not line.strip():
                if line_idx < len(lines):
                    tokens.append(Token("T_NEWLINE", "\n", line_idx, len(line) + 1))
                continue

            indent = 0
            while indent < len(line) and line[indent] == ' ':
                indent += 1

            content = line[indent:]

            if indent > indent_stack[-1]:
                tokens.append(Token("T_INDENT", " " * indent, line_idx, 1))
                indent_stack.append(indent)
            elif indent < indent_stack[-1]:
                while indent < indent_stack[-1]:
                    indent_stack.pop()
                    tokens.append(Token("T_DEDENT", "", line_idx, 1))

            if content.startswith('.'):
                tokens.append(Token("T_COMMENT", content, line_idx, indent + 1))
                if line_idx < len(lines):
                    tokens.append(Token("T_NEWLINE", "\n", line_idx, len(line) + 1))
                continue

            i = 0
            while i < len(content):
                char = content[i]
                if char == ' ':
                    i += 1
                    continue
                if char == ',':
                    tokens.append(Token("T_COMMA", ",", line_idx, indent + i + 1))
                    i += 1
                    continue

                if self.is_digit(char):
                    start = i
                    has_comma = False
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
                    t_type = "T_LITERAL_FLOAT" if has_comma else "T_LITERAL_INT"
                    tokens.append(Token(t_type, val, line_idx, indent + start + 1))
                    continue

                if self.is_alpha(char):
                    start = i
                    while i < len(content) and (content[i].isalnum() or content[i] in '.'):
                        i += 1
                    val = content[start:i]

                    # Standardize logic for literals and keywords
                    if val.upper() == "SANT":
                        t_type = "T_LITERAL_TRUE"
                    elif val.upper() == "FALSKT":
                        t_type = "T_LITERAL_FALSE"
                    else:
                        t_type = self.keywords.get(val.lower(), "T_IDENTIFIER")

                    tokens.append(Token(t_type, val, line_idx, indent + start + 1))
                    continue
                i += 1

            if line_idx < len(lines):
                tokens.append(Token("T_NEWLINE", "\n", line_idx, len(line) + 1))

        while len(indent_stack) > 1:
            indent_stack.pop()
            tokens.append(Token("T_DEDENT", "", len(lines) + 1, 1))

        return tokens
