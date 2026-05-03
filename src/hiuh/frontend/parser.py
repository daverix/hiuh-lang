# -*- coding: utf-8 -*-
from hiuh.frontend.ast import *

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        # Dynamic Scope Stack. Built-ins included.
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
            self.consume(); return UnaryOpNode("kasta", self.parse_greedy_expression())
        if t.type == "T_KEYWORD_GIVE":
            self.consume(); return ReturnNode(self.expression())
        return self.expression()

    def parse_assignment(self):
        self.consume("T_KEYWORD_SET")
        parts = []
        while self.peek() and self.peek().type == "T_IDENTIFIER":
            parts.append(self.consume().value)
        name = " ".join(parts)

        target = None
        if self.peek() and self.peek().type == "T_KEYWORD_IN":
            self.consume()
            target_parts = []
            while self.peek() and self.peek().type == "T_IDENTIFIER":
                target_parts.append(self.consume().value)
            target = " ".join(target_parts)

        self.consume("T_KEYWORD_TO")
        val = self.parse_greedy_expression()
        if not target: self.define_var(name)
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

        # 2. Scope & Trigger Scan
        checkpoint = self.pos
        i = 0
        all_identifiers_known = True
        has_expression_trigger = False
        token_count = 0

        while self.peek(i) and self.peek(i).type not in ["T_NEWLINE", "T_DEDENT", "T_COMMENT"]:
            tok = self.peek(i)
            token_count += 1
            if tok.type == "T_IDENTIFIER":
                if not self.is_var_known(tok.value) and tok.value != "lista":
                    all_identifiers_known = False
            # Check for math/logic triggers
            if tok.type in ["T_KEYWORD_WITH", "T_OP_ADD", "T_OP_MUL", "T_OP_SUB", "T_OP_DIV",
                            "T_OP_IS", "T_KEYWORD_GREATER", "T_KEYWORD_LESS", "T_OP_OR", "T_OP_AND"]:
                # Special Case: 'större' or 'mindre' alone are NOT triggers
                # They only trigger if there is more than one token on the line
                has_expression_trigger = True
            i += 1

        # 3. Decision Logic
        is_hard_literal = t.type in ["T_LITERAL_INT", "T_LITERAL_FLOAT", "T_LITERAL_TRUE", "T_LITERAL_FALSE", "T_KEYWORD_FUNC"]

        # If it's a single keyword (token_count == 1), skip expression parsing to allow StringNode fallback
        should_try_expression = False
        if is_hard_literal:
            should_try_expression = True
        elif token_count > 1 and has_expression_trigger and all_identifiers_known:
            should_try_expression = True
        elif token_count == 1 and t.type == "T_IDENTIFIER" and (t.value == "lista" or self.is_var_known(t.value)):
            should_try_expression = True

        if should_try_expression:
            try:
                expr = self.expression()
                if not self.peek() or self.peek().type in ["T_NEWLINE", "T_DEDENT", "T_COMMENT"]:
                    return expr
                self.pos = checkpoint
            except:
                self.pos = checkpoint

        # 4. Fallback: Greedy String (This will catch 'större' as a single word)
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
                while self.peek() and (self.peek().type in ["T_KEYWORD_GREATER", "T_KEYWORD_LESS", "T_KEYWORD_EQUAL", "T_KEYWORD_THAN", "T_KEYWORD_WITH", "T_OP_OR", "T_OP_AND"] or (self.peek().type == "T_IDENTIFIER" and self.peek().value in ["eller", "lika", "med", "än", "och"])):
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

        if t.type == "T_KEYWORD_FUNC":
            self.consume(); p = []
            if self.peek() and self.peek().type == "T_KEYWORD_WITH":
                self.consume()
                while self.peek() and self.peek().type == "T_IDENTIFIER":
                    p.append(self.consume().value)
                    if self.peek() and self.peek().type == "T_COMMA": self.consume()
                    else: break
            return FunctionDefNode(p, self.parse_block(params=p))

        if t.type in ["T_IDENTIFIER", "T_KEYWORD_GREATER", "T_KEYWORD_LESS", "T_KEYWORD_EQUAL"]:
            # Greedily consume identifiers for multi-word variables like 'min bil'
            parts = [self.consume().value]
            while self.peek() and self.peek().type == "T_IDENTIFIER":
                combined = " ".join(parts + [self.peek().value])
                if self.is_var_known(combined): parts.append(self.consume().value)
                else: break
            name = " ".join(parts)

            # Property read: 'märke i min bil'
            if self.peek() and self.peek().type == "T_KEYWORD_IN":
                self.consume(); t_parts = []
                while self.peek() and self.peek().type == "T_IDENTIFIER":
                    t_parts.append(self.consume().value)
                return VarAccessNode(name, target=" ".join(t_parts))

            # Call: 'hälsa med Hiuh'
            if self.peek() and self.peek().type == "T_KEYWORD_WITH":
                self.consume(); args = []
                while True:
                    args.append(self.expression())
                    if self.peek() and self.peek().type == "T_COMMA": self.consume()
                    else: break
                return FunctionCallNode(name, args)

            if name == "lista": return FunctionCallNode(name, [])
            return VarAccessNode(name)

        if t.type == "T_LITERAL_INT": return IntNode(self.consume().value)
        if t.type == "T_LITERAL_FLOAT": return FloatNode(self.consume().value)
        if t.type == "T_LITERAL_TRUE": self.consume(); return BoolNode(True)
        if t.type == "T_LITERAL_FALSE": self.consume(); return BoolNode(False)
        raise SyntaxError(f"Unexpected {t.type} at line {t.line}")

    def parse_block(self, params=None):
        while self.peek() and self.peek().type == "T_NEWLINE": self.consume()
        self.consume("T_INDENT"); self.enter_scope()
        if params:
            for p in params: self.define_var(p)
        stmts = []
        while self.peek() and self.peek().type != "T_DEDENT":
            if self.peek().type in ["T_NEWLINE", "T_COMMENT"]:
                self.consume(); continue
            stmts.append(self.statement())
        self.exit_scope()
        if self.peek() and self.peek().type == "T_DEDENT": self.consume("T_DEDENT")
        return stmts

    def parse_if(self):
        self.consume("T_KEYWORD_IF"); cond = self.expression(); true_b = self.parse_block()
        false_b = None
        if self.peek() and self.peek().type == "T_KEYWORD_ELSE":
            self.consume(); false_b = self.parse_block()
        return IfNode(cond, true_b, false_b)

    def parse_while(self):
        self.consume("T_KEYWORD_WHILE"); return WhileNode(self.expression(), self.parse_block())

    def parse_try_catch(self):
        self.consume("T_KEYWORD_TRY"); try_b = self.parse_block()
        self.consume("T_KEYWORD_CATCH"); err = self.consume("T_IDENTIFIER").value
        return TryCatchNode(try_b, err, self.parse_block(params=[err]))

    def parse_type_def(self):
        self.consume("T_KEYWORD_TYPE"); name = self.consume("T_IDENTIFIER").value
        self.define_var(name); f = []
        if self.peek() and self.peek().type == "T_KEYWORD_WITH":
            self.consume()
            while self.peek() and self.peek().type == "T_IDENTIFIER":
                f.append(self.consume().value)
                if self.peek() and self.peek().type == "T_COMMA": self.consume()
                else: break
        return TypeDefNode(name, f)
