# -*- coding: utf-8 -*-
from hiuh.frontend.ast import *

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        # Dynamic Scope Stack. SANT/FALSKT/lista/inmatning are built-ins.
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
            raise SyntaxError(f"Expected {expected_type} but got {token.type}")
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
        if t.type == "T_KEYWORD_THROW": return self.parse_throw()
        if t.type == "T_KEYWORD_GIVE": return self.parse_return()
        return self.expression()

    def parse_assignment(self):
        self.consume("T_KEYWORD_SET")
        parts = []
        while self.peek() and self.peek().type == "T_IDENTIFIER":
            parts.append(self.consume().value)
        name = " ".join(parts)

        target = None
        if self.peek() and self.peek().type == "T_KEYWORD_IN":
            self.consume(); target = self.consume("T_IDENTIFIER").value

        self.consume("T_KEYWORD_TO")
        # Decide if value is expression or string based on scopes
        val = self.parse_greedy_expression()
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
                self.consume(); self.consume()
                return StringNode("\n")

        # 2. Scope Lookahead: If line uses unknown variables, treat as String
        # (Handles the 'a större än 2' fallback case)
        checkpoint = self.pos
        i = 0
        all_vars_known = True
        while self.peek(i) and self.peek(i).type not in ["T_NEWLINE", "T_DEDENT", "T_COMMENT"]:
            tok = self.peek(i)
            # If we see an identifier that isn't known, it's likely a greedy string
            if tok.type == "T_IDENTIFIER" and not self.is_var_known(tok.value):
                # Exception: 'ny' is part of 'ny rad', handled above
                if tok.value != "ny":
                    all_vars_known = False; break
            i += 1

        # 3. If line has math/logic/literals AND all variables are known, parse as expression
        if all_vars_known or t.type in ["T_LITERAL_INT", "T_LITERAL_FLOAT", "T_LITERAL_TRUE", "T_LITERAL_FALSE"]:
            try:
                expr = self.expression()
                # If we are at the end of the line, expression succeeded
                if not self.peek() or self.peek().type in ["T_NEWLINE", "T_DEDENT", "T_COMMENT"]:
                    return expr
                self.pos = checkpoint # Reset for fallback
            except:
                self.pos = checkpoint # Reset for fallback

        # 4. Fallback: Multiple tokens/unknown variables -> Join into a StringNode
        parts = []
        while self.peek() and self.peek().type not in ["T_NEWLINE", "T_DEDENT", "T_COMMENT"]:
            parts.append(str(self.consume().value))
        return StringNode(" ".join(parts))

    def expression(self):
        # Level 1: Logical and Comparisons
        left = self.arithmetic()
        while True:
            t = self.peek()
            if not t: break
            if t.type == "T_OP_IS": self.consume()
            t = self.peek()
            if t and (t.type in ["T_KEYWORD_GREATER", "T_KEYWORD_LESS"] or
                      (t.type == "T_IDENTIFIER" and t.value in ["eller", "och", "lika"])):
                op_parts = []
                while self.peek() and (self.peek().type in ["T_KEYWORD_GREATER", "T_KEYWORD_LESS", "T_KEYWORD_THAN", "T_KEYWORD_WITH"] or
                                       (self.peek().type == "T_IDENTIFIER" and self.peek().value in ["eller", "lika", "med", "än", "och"])):
                    op_parts.append(self.consume().value)
                left = ComparisonNode(left, " ".join(op_parts), self.arithmetic())
            else: break
        return left

    def arithmetic(self):
        # Level 2: Addition and Subtraction
        left = self.term()
        while self.peek() and self.peek().type in ["T_OP_ADD", "T_OP_SUB"]:
            op = self.consume().type
            right = self.term()
            left = AddNode(left, right) if op == "T_OP_ADD" else SubNode(left, right)
        return left

    def term(self):
        # Level 3: Multiplication and Division
        left = self.primary()
        while self.peek() and self.peek().type in ["T_OP_MUL", "T_OP_DIV"]:
            op = self.consume().type
            if op == "T_OP_DIV" and self.peek() and self.peek().value == "med": self.consume()
            right = self.primary()
            left = MulNode(left, right) if op == "T_OP_MUL" else DivNode(left, right)
        return left

    def primary(self):
        t = self.peek()
        if not t: raise SyntaxError("Expected primary")
        if t.type in ["T_IDENTIFIER", "T_KEYWORD_GREATER", "T_KEYWORD_LESS"]:
            name = self.consume().value
            if self.peek() and self.peek().value == "med":
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
        if t.type == "T_KEYWORD_FUNC":
            self.consume(); p = []
            if self.peek() and self.peek().type == "T_KEYWORD_WITH":
                self.consume()
                while self.peek() and self.peek().type == "T_IDENTIFIER":
                    p_name = self.consume().value
                    p.append(p_name); self.define_var(p_name)
                    if self.peek() and self.peek().type == "T_COMMA": self.consume()
                    else: break
            return FunctionDefNode(p, self.parse_block())
        raise SyntaxError(f"Unexpected {t.type}")

    def parse_block(self):
        self.consume("T_NEWLINE"); self.consume("T_INDENT")
        self.enter_scope()
        stmts = []
        while self.peek() and self.peek().type != "T_DEDENT":
            if self.peek().type in ["T_NEWLINE", "T_COMMENT"]:
                self.consume(); continue
            stmts.append(self.statement())
        self.exit_scope()
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
        self.consume("T_KEYWORD_CATCH")
        err = self.consume("T_IDENTIFIER").value
        # Note: We don't enter scope here because parse_block already does it.
        # We manually define the catch var so the catch block knows it.
        self.enter_scope()
        self.define_var(err)
        # Manually parsing the block to avoid double-entering scope
        self.consume("T_NEWLINE"); self.consume("T_INDENT")
        catch_stmts = []
        while self.peek() and self.peek().type != "T_DEDENT":
            catch_stmts.append(self.statement())
        self.exit_scope()
        self.consume("T_DEDENT")
        return TryCatchNode(try_b, err, catch_stmts)

    def parse_return(self):
        self.consume("T_KEYWORD_GIVE"); return ReturnNode(self.expression())

    def parse_throw(self):
        self.consume("T_KEYWORD_THROW"); return UnaryOpNode("kasta", self.expression())

    def parse_type_def(self):
        self.consume("T_KEYWORD_TYPE"); name = self.consume("T_IDENTIFIER").value
        self.define_var(name)
        f = []
        if self.peek() and self.peek().type == "T_KEYWORD_WITH":
            self.consume()
            while self.peek() and self.peek().type == "T_IDENTIFIER":
                f.append(self.consume().value)
                if self.peek() and self.peek().type == "T_COMMA": self.consume()
                else: break
        return TypeDefNode(name, f)
