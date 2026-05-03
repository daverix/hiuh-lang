# -*- coding: utf-8 -*-
from hiuh.frontend.ast import *

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        # Dynamic Scope Stack
        self.scopes = [{"SANT", "FALSKT", "lista", "inmatning"}]
        # New: Explicit registry for user-defined types
        self.known_types = set()

    def is_var_known(self, name):
        # A name is known if it's in a scope OR if it's a registered Type
        return any(name in scope for scope in self.scopes) or name in self.known_types

    def parse_type_def(self):
        self.consume("T_KEYWORD_TYPE")
        name = self.consume("T_IDENTIFIER").value

        # REGISTER THE TYPE: Now 'bil' is a valid expression trigger
        self.known_types.add(name)
        self.define_var(name)

        fields = []
        if self.peek() and self.peek().type == "T_KEYWORD_WITH":
            self.consume()
            while self.peek() and self.peek().type == "T_IDENTIFIER":
                fields.append(self.consume().value)
                if self.peek() and self.peek().type == "T_COMMA": self.consume()
                else: break
        return TypeDefNode(name, fields)

    def enter_scope(self):
        self.scopes.append(set())

    def exit_scope(self):
        if len(self.scopes) > 1: self.scopes.pop()

    def define_var(self, name):
        self.scopes[-1].add(name)

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
            t_parts = []
            while self.peek() and self.peek().type == "T_IDENTIFIER":
                t_parts.append(self.consume().value)
            target = " ".join(t_parts)

        self.consume("T_KEYWORD_TO")
        val = self.parse_greedy_expression()
        if not target: self.define_var(name)
        return AssignNode(name, val, target)

    def parse_print(self):
        self.consume("T_KEYWORD_PRINT")
        return PrintNode(self.parse_greedy_expression())

    def _is_tree_known(self, node):
        """Helper to validate if an expression tree only uses known variables."""
        if isinstance(node, VarAccessNode):
            if hasattr(node, 'target') and node.target:
                return self.is_var_known(node.target)
            return self.is_var_known(node.name)
        if isinstance(node, (AddNode, SubNode, MulNode, DivNode, ComparisonNode)):
            return self._is_tree_known(node.left) and self._is_tree_known(node.right)
        if isinstance(node, FunctionCallNode):
            return self.is_var_known(node.name)
        return True

    def parse_greedy_expression(self):
        t = self.peek()
        if not t or t.type in ["T_NEWLINE", "T_DEDENT"]: return None

        if t.type == "T_IDENTIFIER" and t.value == "ny":
            if self.peek(1) and self.peek(1).value == "rad":
                self.consume(); self.consume(); return StringNode("\n")

        # Trial Pass: Try parsing as a formal expression
        checkpoint = self.pos
        try:
            expr = self.expression()
            # Must hit end-of-line AND all vars must be known to count as expression
            if (not self.peek() or self.peek().type in ["T_NEWLINE", "T_DEDENT", "T_COMMENT"]) and self._is_tree_known(expr):
                return expr
            self.pos = checkpoint
        except:
            self.pos = checkpoint

        # Fallback Pass: Join everything until end of line as a String
        txt = []
        while self.peek() and self.peek().type not in ["T_NEWLINE", "T_DEDENT", "T_COMMENT"]:
            txt.append(str(self.consume().value))
        return StringNode(" ".join(txt))

    def expression(self):
        left = self.arithmetic()
        while True:
            t = self.peek()
            if not t or t.type in ["T_NEWLINE", "T_INDENT", "T_DEDENT"]: break
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
            if self.peek().type in ["T_INDENT"]: break
            op = self.consume().type
            left = AddNode(left, self.term()) if op == "T_OP_ADD" else SubNode(left, self.term())
        return left

    def term(self):
        left = self.primary()
        while self.peek() and self.peek().type in ["T_OP_MUL", "T_OP_DIV"]:
            if self.peek().type in ["T_INDENT"]: break
            op = self.consume().type
            if op == "T_OP_DIV" and self.peek() and self.peek().value == "med": self.consume()
            left = MulNode(left, self.primary()) if op == "T_OP_MUL" else DivNode(left, self.primary())
        return left

    def primary(self):
        t = self.peek()
        if not t: raise SyntaxError("Expected primary")

        if t.type == "T_KEYWORD_FUNC":
            self.consume()
            p = []
            if self.peek() and self.peek().type == "T_KEYWORD_WITH":
                self.consume()
                while self.peek() and self.peek().type == "T_IDENTIFIER":
                    p.append(self.consume().value)
                    if self.peek() and self.peek().type == "T_COMMA": self.consume()
                    else: break
            return FunctionDefNode(p, self.parse_block(params=p))

        if t.type in ["T_IDENTIFIER", "T_KEYWORD_GREATER", "T_KEYWORD_LESS", "T_KEYWORD_EQUAL"]:
            name = self.consume().value

            if self.peek() and self.peek().type == "T_KEYWORD_IN":
                self.consume()
                t_parts = []
                while self.peek() and self.peek().type == "T_IDENTIFIER": t_parts.append(self.consume().value)
                return VarAccessNode(name, target=" ".join(t_parts))

            while self.peek() and self.peek().type == "T_IDENTIFIER":
                combined = name + " " + self.peek().value
                if self.is_var_known(combined): name = combined; self.consume()
                else: break

            if self.peek() and self.peek().type == "T_KEYWORD_WITH":
                self.consume()
                args = []
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
        raise SyntaxError(f"Unexpected {t.type} ({t.value}) at line {t.line}")

    def parse_block(self, params=None):
        while self.peek() and self.peek().type == "T_NEWLINE": self.consume()
        self.consume("T_INDENT"); self.enter_scope()
        if params:
            for p in params: self.define_var(p)
        stmts = []
        while self.peek() and self.peek().type != "T_DEDENT":
            if self.peek().type in ["T_NEWLINE", "T_COMMENT"]: self.consume(); continue
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
