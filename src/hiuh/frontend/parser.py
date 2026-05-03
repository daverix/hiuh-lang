# -*- coding: utf-8 -*-
from hiuh.frontend.ast import *

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.scopes = [{"SANT", "FALSKT", "lista", "inmatning"}]

    def enter_scope(self):
        self.scopes.append(set())

    def exit_scope(self):
        if len(self.scopes) > 1: self.scopes.pop()

    def define_var(self, name):
        self.scopes[-1].add(name)

    def is_var_known(self, name):
        return any(name in scope for scope in self.scopes)

    def peek(self, offset=0):
        if self.pos + offset >= len(self.tokens): return None
        return self.tokens[self.pos + offset]

    def consume(self, expected_type=None):
        token = self.peek()
        if not token: raise SyntaxError("Unexpected EOF")
        if expected_type and token.type != expected_type:
            raise SyntaxError(f"Expected {expected_type} but got {token.type} at line {token.line}")
        self.pos += 1
        return token

    def parse(self):
        nodes = []
        while self.peek():
            if self.peek().type in ["T_NEWLINE", "T_COMMENT"]:
                self.consume(); continue
            nodes.append(self.statement())
        return nodes

    def statement(self):
        t = self.peek()
        if not t: return None
        if t.type == "T_KEYWORD_SET": return self.parse_assignment()
        if t.type == "T_KEYWORD_PRINT": return self.parse_print()
        if t.type == "T_KEYWORD_IF": return self.parse_if()
        if t.type == "T_KEYWORD_WHILE": return self.parse_while()
        if t.type == "T_KEYWORD_TYPE": return self.parse_type_def()
        if t.type == "T_KEYWORD_TRY": return self.parse_try_catch()

        if t.type == "T_KEYWORD_THROW":
            self.consume("T_KEYWORD_THROW")
            return UnaryOpNode("kasta", self.parse_greedy_expression())

        if t.type == "T_KEYWORD_GIVE": return self.parse_return()
        return self.expression()

    def parse_assignment(self):
        self.consume("T_KEYWORD_SET")

        # 1. Consume the property/variable name (e.g., 'märke')
        parts = []
        while self.peek() and self.peek().type == "T_IDENTIFIER":
            parts.append(self.consume().value)
        name = " ".join(parts)

        target = None
        # 2. Check for the 'i' keyword (e.g., 'i min bil')
        if self.peek() and self.peek().type == "T_KEYWORD_IN":
            self.consume() # consume 'i'
            target_parts = []
            # Greedily consume identifiers for the target (e.g., 'min', 'bil')
            while self.peek() and self.peek().type == "T_IDENTIFIER":
                target_parts.append(self.consume().value)
            target = " ".join(target_parts)

        # 3. Now it must be 'till'
        self.consume("T_KEYWORD_TO")

        # 4. Parse the value
        val = self.parse_greedy_expression()

        # If it's a standard assignment, define it in scope
        if not target:
            self.define_var(name)

        return AssignNode(name, val, target)

    def parse_print(self):
        self.consume("T_KEYWORD_PRINT")
        return PrintNode(self.parse_greedy_expression())

    def parse_greedy_expression(self):
        t = self.peek()
        if not t: return None

        # 1. Newline literal: ny rad
        if t.type == "T_IDENTIFIER" and t.value == "ny":
            if self.peek(1) and self.peek(1).value == "rad":
                self.consume(); self.consume(); return StringNode("\n")

        # 2. Logic Check: If we see grej, lista, SANT, numbers, or a known variable,
        # try parsing as an expression FIRST.
        is_builtin = t.type == "T_IDENTIFIER" and t.value in ["lista", "inmatning"]
        is_known = t.type == "T_IDENTIFIER" and self.is_var_known(t.value)

        if t.type in ["T_KEYWORD_FUNC", "T_LITERAL_INT", "T_LITERAL_FLOAT", "T_LITERAL_TRUE", "T_LITERAL_FALSE"] or is_builtin or is_known:
            checkpoint = self.pos
            try:
                expr = self.expression()
                # If we are at the end of the line, the expression won!
                if not self.peek() or self.peek().type in ["T_NEWLINE", "T_DEDENT", "T_COMMENT"]:
                    return expr
                self.pos = checkpoint
            except:
                self.pos = checkpoint

        # 3. Final Fallback: Joined String
        txt = []
        while self.peek() and self.peek().type not in ["T_NEWLINE", "T_DEDENT", "T_COMMENT"]:
            txt.append(str(self.consume().value))
        return StringNode(" ".join(txt))

    def expression(self):
        left = self.arithmetic()
        while True:
            t = self.peek()
            if not t: break
            if t.type == "T_OP_IS": self.consume(); t = self.peek()
            if t and (t.type in ["T_KEYWORD_GREATER", "T_KEYWORD_LESS", "T_KEYWORD_EQUAL", "T_OP_OR", "T_OP_AND"]):
                op_parts = []
                while self.peek() and (self.peek().type in ["T_KEYWORD_GREATER", "T_KEYWORD_LESS", "T_KEYWORD_EQUAL", "T_KEYWORD_THAN", "T_KEYWORD_WITH", "T_OP_OR", "T_OP_AND"] or
                                       (self.peek().type == "T_IDENTIFIER" and self.peek().value in ["eller", "lika", "med", "än", "och"])):
                    op_parts.append(self.consume().value)
                left = ComparisonNode(left, " ".join(op_parts), self.arithmetic())
            else: break
        return left

    def arithmetic(self):
        left = self.term()
        while self.peek() and self.peek().type in ["T_OP_ADD", "T_OP_SUB"]:
            op = self.consume().type
            left = AddNode(left, self.term()) if op == "T_OP_ADD" else SubNode(left, self.term())
        return left

    def term(self):
        left = self.primary()
        while self.peek() and self.peek().type in ["T_OP_MUL", "T_OP_DIV"]:
            op = self.consume().type
            if op == "T_OP_DIV" and self.peek() and self.peek().value == "med": self.consume()
            left = MulNode(left, self.primary()) if op == "T_OP_MUL" else DivNode(left, self.primary())
        return left

    def primary(self):
        t = self.peek()
        if not t: raise SyntaxError("Expected primary")

        # 1. Function Definitions (grej ...)
        if t.type == "T_KEYWORD_FUNC":
            self.consume()  # consume 'grej'
            p = []
            if self.peek() and self.peek().type == "T_KEYWORD_WITH":
                self.consume()  # consume 'med'
                while self.peek() and self.peek().type == "T_IDENTIFIER":
                    p_name = self.consume().value
                    p.append(p_name)
                    if self.peek() and self.peek().type == "T_COMMA":
                        self.consume()
                    else:
                        break
            return FunctionDefNode(p, self.parse_block(params=p))

        # 2. Variable access, Function Calls, and Field Access
        if t.type in ["T_IDENTIFIER", "T_KEYWORD_GREATER", "T_KEYWORD_LESS", "T_KEYWORD_EQUAL"]:
            # Handle multi-word variables (e.g., 'min bil')
            parts = [self.consume().value]
            while self.peek() and self.peek().type == "T_IDENTIFIER":
                combined = " ".join(parts + [self.peek().value])
                if self.is_var_known(combined):
                    parts.append(self.consume().value)
                else:
                    break
            name = " ".join(parts)

            # Check for Field Access: 'märke i min bil'
            if self.peek() and self.peek().type == "T_KEYWORD_IN":
                self.consume() # consume 'i'
                target_parts = []
                while self.peek() and self.peek().type == "T_IDENTIFIER":
                    target_parts.append(self.consume().value)
                target_name = " ".join(target_parts)
                return VarAccessNode(name, target=target_name)

            # Check for Function Call: 'hälsa med Hiuh' or 'lista med 1, 2'
            if self.peek() and self.peek().type == "T_KEYWORD_WITH":
                self.consume() # consume 'med'
                args = []
                while True:
                    args.append(self.expression())
                    if self.peek() and self.peek().type == "T_COMMA":
                        self.consume()
                    else:
                        break
                return FunctionCallNode(name, args)

            # Built-in constructor
            if name == "lista":
                return FunctionCallNode(name, [])

            return VarAccessNode(name)

        # 3. Literals
        if t.type == "T_LITERAL_INT": return IntNode(self.consume().value)
        if t.type == "T_LITERAL_FLOAT": return FloatNode(self.consume().value)
        if t.type == "T_LITERAL_TRUE": self.consume(); return BoolNode(True)
        if t.type == "T_LITERAL_FALSE": self.consume(); return BoolNode(False)

        raise SyntaxError(f"Unexpected {t.type} ({t.value}) at line {t.line}")


    def parse_block(self, params=None):
        # Allow blocks to start either after a newline or immediately if indented
        if self.peek() and self.peek().type == "T_NEWLINE":
            self.consume("T_NEWLINE")

        self.consume("T_INDENT")
        self.enter_scope()
        if params:
            for p in params: self.define_var(p)

        stmts = []
        while self.peek() and self.peek().type != "T_DEDENT":
            if self.peek().type in ["T_NEWLINE", "T_COMMENT"]:
                self.consume(); continue
            stmts.append(self.statement())

        self.exit_scope()
        self.consume("T_DEDENT")
        return stmts

    def parse_if(self):
        self.consume("T_KEYWORD_IF")
        cond = self.expression()
        true_b = self.parse_block()
        false_b = None
        if self.peek() and self.peek().type == "T_KEYWORD_ELSE":
            self.consume()
            false_b = self.parse_block()
        return IfNode(cond, true_b, false_b)

    def parse_while(self):
        self.consume("T_KEYWORD_WHILE")
        return WhileNode(self.expression(), self.parse_block())

    def parse_try_catch(self):
        self.consume("T_KEYWORD_TRY")
        try_b = self.parse_block()
        self.consume("T_KEYWORD_CATCH")
        err = self.consume("T_IDENTIFIER").value
        return TryCatchNode(try_b, err, self.parse_block(params=[err]))

    def parse_return(self):
        self.consume("T_KEYWORD_GIVE")
        return ReturnNode(self.expression())

    def parse_throw(self):
        self.consume("T_KEYWORD_THROW")
        return UnaryOpNode("kasta", self.expression())

    def parse_type_def(self):
        self.consume("T_KEYWORD_TYPE")
        name = self.consume("T_IDENTIFIER").value
        self.define_var(name)
        f = []
        if self.peek() and self.peek().type == "T_KEYWORD_WITH":
            self.consume()
            while self.peek() and self.peek().type == "T_IDENTIFIER":
                f.append(self.consume().value)
                if self.peek() and self.peek().type == "T_COMMA": self.consume()
                else: break
        return TypeDefNode(name, f)
