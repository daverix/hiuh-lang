# -*- coding: utf-8 -*-
from hiuh.frontend.ast import *

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.scopes = [{"SANT", "FALSKT", "lista", "inmatning"}]
        self.known_types = set()

    def enter_scope(self): self.scopes.append(set())
    def exit_scope(self):
        if len(self.scopes) > 1: self.scopes.pop()
    def define_var(self, name): self.scopes[-1].add(name)
    def is_var_known(self, name):
        return any(name in scope for scope in self.scopes) or name in self.known_types

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
        while self.peek() and self.peek().type == "T_IDENTIFIER": parts.append(self.consume().value)
        name = " ".join(parts)
        target = None
        if self.peek() and self.peek().type == "T_KEYWORD_IN":
            self.consume()
            t_p = []
            while self.peek() and self.peek().type == "T_IDENTIFIER": t_p.append(self.consume().value)
            target = " ".join(t_p)
        self.consume("T_KEYWORD_TO")
        val = self.parse_greedy_expression()
        if not target: self.define_var(name)
        return AssignNode(name, val, target)

    def parse_print(self):
        self.consume("T_KEYWORD_PRINT")
        return PrintNode(self.parse_greedy_expression())

    def _is_tree_valid(self, node):
        if isinstance(node, VarAccessNode):
            if node.target: return self.is_var_known(node.target)
            return self.is_var_known(node.name)
        if isinstance(node, (AddNode, SubNode, MulNode, DivNode, ComparisonNode)):
            return self._is_tree_valid(node.left) and self._is_tree_valid(node.right)
        if isinstance(node, FunctionCallNode): return self.is_var_known(node.name)
        return True

    def parse_greedy_expression(self):
        t = self.peek()
        if not t or t.type in ["T_NEWLINE", "T_DEDENT", "T_INDENT"]: return None

        if t.type == "T_IDENTIFIER" and t.value == "ny":
            if self.peek(1) and self.peek(1).value == "rad":
                self.consume(); self.consume(); return StringNode("\n")

        # LOOKAHEAD: If the line contains an operator, it MUST be an expression
        checkpoint = self.pos
        i = 0
        has_operator = False
        while self.peek(i) and self.peek(i).type not in ["T_NEWLINE", "T_DEDENT", "T_INDENT"]:
            if self.peek(i).type in ["T_OP_ADD", "T_OP_SUB", "T_OP_MUL", "T_OP_DIV", "T_KEYWORD_IN", "T_KEYWORD_WITH"]:
                has_operator = True
                break
            i += 1

        try:
            # If we see an operator OR a literal OR a known variable, try expression
            is_known = t.type == "T_IDENTIFIER" and self.is_var_known(t.value)
            is_literal = t.type in ["T_LITERAL_INT", "T_LITERAL_FLOAT", "T_LITERAL_TRUE", "T_LITERAL_FALSE", "T_KEYWORD_FUNC"]

            if has_operator or is_known or is_literal or t.value == "lista":
                expr = self.expression()
                # If it's a function or we reached the end of the line, it's valid
                if isinstance(expr, FunctionDefNode) or (not self.peek() or self.peek().type in ["T_NEWLINE", "T_DEDENT", "T_INDENT", "T_COMMENT"]):
                    return expr
            self.pos = checkpoint
        except:
            self.pos = checkpoint

        # Fallback
        txt = []
        while self.peek() and self.peek().type not in ["T_NEWLINE", "T_DEDENT", "T_INDENT", "T_COMMENT"]:
            txt.append(str(self.consume().value))
        return StringNode(" ".join(txt))


    def expression(self):
        left = self.arithmetic()
        while self.peek() and self.peek().type not in ["T_NEWLINE", "T_INDENT", "T_DEDENT"]:
            t = self.peek()
            if t.type == "T_OP_IS": self.consume(); t = self.peek()
            if not t: break
            if t.type in ["T_KEYWORD_GREATER", "T_KEYWORD_LESS", "T_KEYWORD_EQUAL", "T_OP_OR", "T_OP_AND"]:
                op_parts = []
                while self.peek() and (self.peek().type in ["T_KEYWORD_GREATER", "T_KEYWORD_LESS", "T_KEYWORD_EQUAL", "T_KEYWORD_THAN", "T_KEYWORD_WITH", "T_OP_OR", "T_OP_AND"] or (self.peek().type == "T_IDENTIFIER" and self.peek().value in ["eller", "lika", "med", "än", "och"])):
                    op_parts.append(self.consume().value)
                left = ComparisonNode(left, " ".join(op_parts), self.arithmetic())
            else: break
        return left

    def arithmetic(self):
        left = self.term()
        # If the term returned a function/block, we MUST stop immediately.
        if isinstance(left, FunctionDefNode): return left

        while self.peek():
            # Stop if we hit a line-breaking token
            if self.peek().type in ["T_NEWLINE", "T_INDENT", "T_DEDENT"]: break
            if self.peek().type in ["T_OP_ADD", "T_OP_SUB"]:
                op = self.consume().type
                left = AddNode(left, self.term()) if op == "T_OP_ADD" else SubNode(left, self.term())
            else: break
        return left

    def term(self):
        left = self.primary()
        if isinstance(left, FunctionDefNode): return left

        while self.peek():
            if self.peek().type in ["T_NEWLINE", "T_INDENT", "T_DEDENT"]: break
            if self.peek().type in ["T_OP_MUL", "T_OP_DIV"]:
                op = self.consume().type
                if op == "T_OP_DIV" and self.peek() and self.peek().value == "med": self.consume()
                left = MulNode(left, self.primary()) if op == "T_OP_MUL" else DivNode(left, self.primary())
            else: break
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
                t_p = []
                while self.peek() and self.peek().type == "T_IDENTIFIER": t_p.append(self.consume().value)
                return VarAccessNode(name, target=" ".join(t_p))
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
            if name == "lista":
                args = []
                if self.peek() and self.peek().type == "T_KEYWORD_WITH":
                    self.consume()
                    while True:
                        args.append(self.expression())
                        if self.peek() and self.peek().type == "T_COMMA": self.consume()
                        else: break
                return FunctionCallNode(name, args)
            return VarAccessNode(name)

        if t.type == "T_LITERAL_INT": return IntNode(self.consume().value)
        if t.type == "T_LITERAL_FLOAT": return FloatNode(self.consume().value)
        if t.type == "T_LITERAL_TRUE": self.consume(); return BoolNode(True)
        if t.type == "T_LITERAL_FALSE": self.consume(); return BoolNode(False)
        raise SyntaxError(f"Unexpected {t.type} ({t.value}) at line {t.line}")

    def parse_block(self, params=None):
        # 1. Skip any newlines leading up to the indent
        while self.peek() and self.peek().type == "T_NEWLINE":
            self.consume("T_NEWLINE")

        # 2. Start the block
        self.consume("T_INDENT")
        self.enter_scope()

        if params:
            for p in params:
                self.define_var(p)

        stmts = []
        # 3. Parse until we hit the DEDENT for THIS specific block
        while self.peek() and self.peek().type != "T_DEDENT":
            if self.peek().type in ["T_NEWLINE", "T_COMMENT"]:
                self.consume()
                continue
            stmts.append(self.statement())

        self.exit_scope()

        # 4. Consume the DEDENT and any trailing newlines so the
        # parent caller doesn't see them
        self.consume("T_DEDENT")
        while self.peek() and self.peek().type == "T_NEWLINE":
            self.consume("T_NEWLINE")

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
        self.known_types.add(name)
        self.define_var(name)
        f = []
        if self.peek() and self.peek().type == "T_KEYWORD_WITH":
            self.consume()
            while self.peek() and self.peek().type == "T_IDENTIFIER":
                f.append(self.consume().value)
                if self.peek() and self.peek().type == "T_COMMA": self.consume()
                else: break
        return TypeDefNode(name, f)
