from hiuh.frontend.ast import *

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self, offset=0):
        if self.pos + offset >= len(self.tokens):
            return None
        return self.tokens[self.pos + offset]

    def consume(self, expected_type=None):
        token = self.peek()
        if not token:
            raise SyntaxError("Unexpected end of input")
        if expected_type and token.type != expected_type:
            raise SyntaxError(f"Expected {expected_type} but got {token.type} at line {token.line}")
        self.pos += 1
        return token

    def parse(self):
        """Main entry point: returns a list of top-level AST nodes."""
        nodes = []
        while self.peek():
            if self.peek().type in ["T_NEWLINE", "T_COMMENT"]:
                self.consume()
                continue
            nodes.append(self.statement())
        return nodes

    def statement(self):
        t = self.peek()
        if t.type == "T_KEYWORD_SET":
            return self.parse_assignment()
        elif t.type == "T_KEYWORD_PRINT":
            return self.parse_print()
        elif t.type == "T_KEYWORD_IF":
            return self.parse_if()
        elif t.type == "T_KEYWORD_TYPE":
            return self.parse_type_def()
        elif t.type == "T_KEYWORD_TRY":
            return self.parse_try_catch()
        # Fallback for expressions as statements (like function calls)
        return self.expression()

    def parse_block(self):
        """Parses a sequence of statements inside an INDENT/DEDENT block."""
        self.consume("T_NEWLINE")
        self.consume("T_INDENT")
        statements = []
        while self.peek() and self.peek().type != "T_DEDENT":
            if self.peek().type in ["T_NEWLINE", "T_COMMENT"]:
                self.consume()
                continue
            statements.append(self.statement())
        self.consume("T_DEDENT")
        return statements

    def parse_assignment(self):
        self.consume("T_KEYWORD_SET")
        name = self.consume("T_IDENTIFIER").value

        # Handle 'sätt x i person' vs 'sätt x till'
        target_type = None
        if self.peek().type == "T_KEYWORD_IN":
            self.consume("T_KEYWORD_IN")
            target_type = self.consume("T_IDENTIFIER").value

        self.consume("T_KEYWORD_TO")
        value = self.expression()
        return AssignNode(name, value, target_type)

    def parse_print(self):
        self.consume("T_KEYWORD_PRINT")
        return PrintNode(self.expression())

    def parse_if(self):
        self.consume("T_KEYWORD_IF")
        condition = self.expression()
        true_block = self.parse_block()
        false_block = None
        if self.peek() and self.peek().type == "T_KEYWORD_ELSE":
            self.consume("T_KEYWORD_ELSE")
            false_block = self.parse_block()
        return IfNode(condition, true_block, false_block)

    def parse_type_def(self):
        self.consume("T_KEYWORD_TYPE")
        name = self.consume("T_IDENTIFIER").value
        fields = []
        if self.peek() and self.peek().type == "T_KEYWORD_WITH":
            self.consume("T_KEYWORD_WITH")
            while self.peek() and self.peek().type == "T_IDENTIFIER":
                fields.append(self.consume().value)
                if self.peek() and self.peek().type == "T_COMMA":
                    self.consume()
        return TypeDefNode(name, fields)

    def parse_try_catch(self):
        self.consume("T_KEYWORD_TRY")
        try_block = self.parse_block()
        self.consume("T_KEYWORD_CATCH")
        error_var = self.consume("T_IDENTIFIER").value
        catch_block = self.parse_block()
        return TryCatchNode(try_block, error_var, catch_block)

    def expression(self):
        """Handles binary operations and base values."""
        left = self.primary()

        # Handle multi-word operators like 'större än' or 'lika med'
        op_token = self.peek()
        if op_token and op_token.type in ["T_OP_ADD", "T_OP_MUL", "T_OP_IS", "T_KEYWORD_GREATER", "T_KEYWORD_LESS"]:
            op = self.consume().value
            # Check for 'än' or 'med' to complete the operator
            if self.peek() and self.peek().type in ["T_KEYWORD_THAN", "T_KEYWORD_WITH"]:
                op += " " + self.consume().value
            right = self.expression()
            return BinOpNode(left, op, right)

        return left

    def primary(self):
        """Handles literals, variables, and function definitions."""
        t = self.peek()

        # Handle Function Definition: 'grej med a, b'
        if t.type == "T_KEYWORD_FUNC":
            self.consume()
            params = []
            if self.peek() and self.peek().type == "T_KEYWORD_WITH":
                self.consume()
                while self.peek() and self.peek().type == "T_IDENTIFIER":
                    params.append(self.consume().value)
                    if self.peek() and self.peek().type == "T_COMMA":
                        self.consume()
            return FunctionDefNode(params, self.parse_block())

        # Handle List Creation: 'lista med 1, 2'
        if t.type == "T_IDENTIFIER" and t.value == "lista":
            self.consume()
            args = []
            if self.peek() and self.peek().type == "T_KEYWORD_WITH":
                self.consume()
                while True:
                    args.append(self.expression())
                    if self.peek() and self.peek().type == "T_COMMA":
                        self.consume()
                    else:
                        break
            return FunctionCallNode("lista", args)

        # Handle Variable Access with 'från': 'namn från p'
        if t.type == "T_IDENTIFIER":
            name = self.consume().value
            if self.peek() and self.peek().type == "T_KEYWORD_FROM":
                self.consume()
                source = self.consume("T_IDENTIFIER").value
                return VarAccessNode(name, source)

            # Check for function call: 'min_funk med 1, 2'
            if self.peek() and self.peek().type == "T_KEYWORD_WITH":
                self.consume()
                args = []
                while True:
                    args.append(self.expression())
                    if self.peek() and self.peek().type == "T_COMMA":
                        self.consume()
                    else:
                        break
                return FunctionCallNode(name, args)

            return VarAccessNode(name)

        # Basic Literals
        if t.type == "T_LITERAL_INT": return LiteralNode(self.consume().value, "INT")
        if t.type == "T_LITERAL_FLOAT": return LiteralNode(self.consume().value, "FLOAT")
        if t.type == "T_LITERAL_TRUE":
            self.consume()
            return LiteralNode(True, "BOOL")
        if t.type == "T_LITERAL_FALSE":
            self.consume()
            return LiteralNode(False, "BOOL")

        raise SyntaxError(f"Unexpected token in expression: {t}")
