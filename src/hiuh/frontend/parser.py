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

        # STOP IMMEDIATELY if we see a newline or indent before we start
        if t.type in ["T_NEWLINE", "T_INDENT"]:
            return None

        # 1. 'ny rad' check
        if t.type == "T_IDENTIFIER" and t.value == "ny":
            if self.peek(1) and self.peek(1).value == "rad":
                self.consume(); self.consume(); return StringNode("\n")

        # 2. Block/Function Priority: 'grej' must trigger expression parsing
        if t.type == "T_KEYWORD_FUNC":
            return self.expression()

        # 3. Decision Logic: Only try expression if it's a known literal or var
        is_known = t.type == "T_IDENTIFIER" and self.is_var_known(t.value)
        if t.type in ["T_LITERAL_INT", "T_LITERAL_FLOAT", "T_LITERAL_TRUE", "T_LITERAL_FALSE"] or is_known or t.value == "lista":
            checkpoint = self.pos
            try:
                expr = self.expression()
                # If the next token is a newline or indent, the expression is valid
                if not self.peek() or self.peek().type in ["T_NEWLINE", "T_INDENT", "T_DEDENT", "T_COMMENT"]:
                    return expr
                self.pos = checkpoint
            except:
                self.pos = checkpoint

        # 4. Fallback: Joined String
        txt = []
        # MUST stop at Newline/Indent to prevent dragging line 3 into line 2
        while self.peek() and self.peek().type not in ["T_NEWLINE", "T_INDENT", "T_DEDENT", "T_COMMENT"]:
            txt.append(str(self.consume().value))
        return StringNode(" ".join(txt))


    def expression(self):
        left = self.arithmetic()
        while True:
            t = self.peek()
            # STOP if we hit a block start
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
            # STOP if next line starts
            if self.peek().type in ["T_INDENT"]: break
            op = self.consume().type
            left = AddNode(left, self.term()) if op == "T_OP_ADD" else SubNode(left, self.term())
        return left

    def term(self):
        left = self.primary()
        while self.peek() and self.peek().type in ["T_OP_MUL", "T_OP_DIV"]:
            # STOP if next line starts
            if self.peek().type in ["T_INDENT"]: break
            op = self.consume().type
            if op == "T_OP_DIV" and self.peek() and self.peek().value == "med": self.consume()
            left = MulNode(left, self.primary()) if op == "T_OP_MUL" else DivNode(left, self.primary())
        return left

    def primary(self):
        t = self.peek()
        if not t: raise SyntaxError("Expected primary")

        if t.type == "T_KEYWORD_FUNC":
            self.consume() # consume 'grej'
            p = []
            if self.peek() and self.peek().type == "T_KEYWORD_WITH":
                self.consume() # consume 'med'
                while self.peek() and self.peek().type == "T_IDENTIFIER":
                    p.append(self.consume().value)
                    if self.peek() and self.peek().type == "T_COMMA": self.consume()
                    else: break

            return FunctionDefNode(p, self.parse_block(params=p))

        if t.type in ["T_IDENTIFIER", "T_KEYWORD_GREATER", "T_KEYWORD_LESS", "T_KEYWORD_EQUAL"]:
            name = self.consume().value

            # IMPROVED: Look ahead for "i" immediately after an identifier
            if self.peek() and self.peek().type == "T_KEYWORD_IN":
                self.consume() # consume 'i'
                target_parts = []
                # Greedily grab the object name (e.g., 'min', 'bil')
                while self.peek() and self.peek().type == "T_IDENTIFIER":
                    target_parts.append(self.consume().value)
                return VarAccessNode(name, target=" ".join(target_parts))

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
        # 1. Clear any and all newlines before the indentation starts
        while self.peek() and self.peek().type == "T_NEWLINE":
            self.consume("T_NEWLINE")

        # 2. Consume the indentation
        self.consume("T_INDENT")
        self.enter_scope()

        if params:
            for p in params:
                self.define_var(p)

        stmts = []
        # 3. Parse statements until we hit the matching DEDENT
        while self.peek() and self.peek().type != "T_DEDENT":
            if self.peek().type in ["T_NEWLINE", "T_COMMENT"]:
                self.consume()
                continue
            stmts.append(self.statement())

        self.exit_scope()

        # 4. Clean up the dedent and any trailing newlines
        if self.peek() and self.peek().type == "T_DEDENT":
            self.consume("T_DEDENT")

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
