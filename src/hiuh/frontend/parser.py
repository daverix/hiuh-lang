# -*- coding: utf-8 -*-
from hiuh.frontend.ast import *

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        # Dynamic Scope Stack. Built-ins included.
        self.scopes = [{"SANT", "FALSKT", "lista", "inmatning", "heltal", "text", "flyttal", "mellanrum", "ny", "rad"}]
        self.known_types = set()
        self.in_structural_statement = False

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
            t = self.peek()
            if t.type in ["T_NEWLINE", "T_COMMENT", "T_DEDENT"]:
                self.consume(); continue
            nodes.append(self.statement())
        return nodes

    def statement(self):
        t = self.peek()
        if not t: return None

        if t.type == "T_KEYWORD_IMPORT":
            return self.parse_import()

        if t.type == "T_KEYWORD_OPEN":
            return self.parse_open_file()
        if t.type == "T_KEYWORD_CLOSE":
            return self.parse_close_file()

        if t.type == "T_IDENTIFIER" and t.value == "lägg":
            if self.peek(1) and self.peek(1).value == "till":
                return self.parse_append()
        if t.type == "T_IDENTIFIER" and t.value == "ta":
            if self.peek(1) and self.peek(1).value == "bort":
                return self.parse_remove()
        if t.type == "T_KEYWORD_SET": return self.parse_assignment()
        if t.type == "T_KEYWORD_PRINT": return self.parse_print()
        if t.type == "T_KEYWORD_IF": return self.parse_if()
        if t.type == "T_KEYWORD_WHILE": return self.parse_while()
        if t.type == "T_KEYWORD_TYPE": return self.parse_type_def()
        if t.type == "T_KEYWORD_TRY": return self.parse_try_catch()
        if t.type == "T_KEYWORD_THROW":
            self.consume(); return UnaryOpNode("kasta", self.parse_greedy_expression(), token=t)
        if t.type == "T_KEYWORD_GIVE":
            self.consume(); return ReturnNode(self.expression(), token=t)
        return self.expression()

    def parse_import(self):
        import_token = self.consume("T_KEYWORD_IMPORT") # använd

        # Parse module name (greedy string to support filenames/multiword paths)
        # Note: because we made 'som' a hard boundary before, parse_greedy_expression will stop perfectly!
        module_expr = self.parse_greedy_expression()
        module_name = module_expr.value if hasattr(module_expr, 'value') else str(module_expr)

        alias = None
        # Support: använd matematik som matte
        if self.peek() and self.peek().value == "som":
            self.consume() # som
            parts = []
            while self.peek() and self.peek().type == "T_IDENTIFIER":
                parts.append(self.consume().value)
            alias = " ".join(parts)

        return ImportNode(module_name, alias, token=import_token)

    def parse_append(self):
        append_token = self.consume() # lägg
        self.consume() # till

        # Parse the value to add (could be an expression)
        val = self.parse_greedy_expression()

        # Expect 'i'
        self.consume("T_KEYWORD_IN")

        # Parse the list name (multi-word support)
        parts = []
        while self.peek() and self.peek().type == "T_IDENTIFIER":
            parts.append(self.consume().value)
        target = "".join(parts)

        return AppendNode(val, target, token=append_token)

    def parse_remove(self):
        remove_token = self.consume() # ta
        self.consume() # bort

        # Check if the user specified 'element' or 'index'
        is_index_based = False
        if self.peek() and self.peek().value in ["element", "index"]:
            self.consume()
            is_index_based = True

        self.in_structural_statement = True
        try:
            target_expr = self.parse_greedy_expression()
        finally:
            self.in_structural_statement = False

        self.consume("T_KEYWORD_FROM") # från

        # Parse the 'where' (the list name)
        parts = []
        while self.peek() and self.peek().type == "T_IDENTIFIER":
            parts.append(self.consume().value)
        list_name = " ".join(parts)

        if is_index_based:
            return RemoveIndexNode(target_expr, list_name, token=remove_token)

        return RemoveValueNode(target_expr, list_name, token=remove_token)

    def parse_open_file(self):
        open_token = self.consume() # öppna
        self.in_structural_statement = True
        try:
            path_expr = self.parse_greedy_expression()

            mode = "läsning"
            mode_token = open_token
            if self.peek() and self.peek().value == "för":
                self.consume() # för
                mode_token = self.consume("T_IDENTIFIER")
                mode = mode_token.value # läsning / skrivning

            if self.peek() and self.peek().value == "som":
                assign_token = self.consume() # som
            else:
                raise SyntaxError("Förväntade 'som' efter filnamnet")
        finally:
            self.in_structural_statement = False

        parts = []
        while self.peek() and self.peek().type == "T_IDENTIFIER":
            parts.append(self.consume().value)
        var_name = " ".join(parts)

        self.define_var(var_name)
        function_call_args = [path_expr, StringNode(mode, token=mode_token)]
        function_call_node = FunctionCallNode("öppna", function_call_args, token=open_token)
        return AssignNode(var_name, function_call_node, target_type=None, token=assign_token)

    def parse_close_file(self):
        close_file_token = self.consume("T_KEYWORD_CLOSE") # Consumes 'stäng'

        # Greedy identifier consumption to match multi-word file names
        parts = []
        while self.peek() and self.peek().type == "T_IDENTIFIER":
            parts.append(self.consume().value)

        if not parts:
            raise SyntaxError(f"Förväntade en filvariabel efter 'stäng' på rad {self.peek().line if self.peek() else 'EOF'}")

        target = " ".join(parts)
        return CloseFileNode(target, token=close_file_token)

    def parse_assignment(self):
        assign_token = self.consume("T_KEYWORD_SET")

        # Check for list indexing: sätt element 0 i minlista till ...
        if self.peek() and self.peek().value in ["element", "index"] and self.peek(1).type == "T_LITERAL_INT":
            self.consume() # 'element'
            idx = self.consume().value
            self.consume("T_KEYWORD_IN") # 'i'
            target_parts = []
            while self.peek() and self.peek().type == "T_IDENTIFIER":
                target_parts.append(self.consume().value)
            target = " ".join(target_parts)
            self.consume("T_KEYWORD_TO")
            val = self.parse_greedy_expression()
            return AssignNode(str(idx), val, target_type=target, token=assign_token)

        # Standard assignment
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
        return AssignNode(name, val, target_type=target, token=assign_token)

    def parse_print(self):
        print_token = self.consume("T_KEYWORD_PRINT")

        val = self.parse_greedy_expression()

        if self.peek() and self.peek().type == "T_KEYWORD_TO":
            self.consume() # till
            target_var = self.consume("T_IDENTIFIER").value
            # Create a new FileWriteNode
            return FileWriteNode(val, target_var, token=print_token)

        return PrintNode(val, token=print_token)

    def _is_tree_valid(self, node):
        if isinstance(node, StringNode):
            return True

        if isinstance(node, CloseFileNode):
            return True

        if isinstance(node, VarAccessNode):
            if hasattr(node, 'target') and node.target:
                return self.is_var_known(node.target)
            return self.is_var_known(node.name)

        if isinstance(node, AddNode):
            return self._is_tree_valid(node.left) or self._is_tree_valid(node.right)

        if isinstance(node, (SubNode, MulNode, DivNode, ComparisonNode)):
            return self._is_tree_valid(node.left) and self._is_tree_valid(node.right)

        if isinstance(node, FunctionCallNode):
            return self.is_var_known(node.name) or node.name == "lista"

        if isinstance(node, CastNode):
            return self._is_tree_valid(node.value)

        if isinstance(node, UnaryOpNode):
            return self._is_tree_valid(node.operand)
        return True

    def parse_greedy_expression(self):
        while self.peek() and self.peek().type in ["T_NEWLINE", "T_COMMENT"]:
            self.consume()

        t = self.peek()
        if not t or t.type in ["T_DEDENT", "T_INDENT"]:
            return None

        if t.type == "T_IDENTIFIER" and t.value == "ny" and self.peek(1) and self.peek(1).value == "rad":
            self.consume(); self.consume()
            return StringNode("\n", token=t)

        checkpoint = self.pos

        has_forced_trigger = False
        i = 0
        while self.peek(i) and self.peek(i).type not in ["T_NEWLINE", "T_DEDENT", "T_INDENT"]:
            tok = self.peek(i)

            if tok.value in ["för", "som", "till"] or tok.type in ["T_KEYWORD_FROM", "T_KEYWORD_IN"]:
                break

            if tok.value in ["element", "index", "inmatning", "mellanrum", "längd"] or \
               tok.type in ["T_OP_ADD", "T_OP_SUB", "T_OP_MUL", "T_OP_DIV"]:
                has_forced_trigger = True
                break

            i += 1

        try:
            expr = self.expression()
            if isinstance(expr, (FunctionDefNode, FunctionCallNode)): return expr

            nt = self.peek()
            is_at_boundary = not nt or nt.type in [
                "T_NEWLINE", "T_DEDENT", "T_INDENT", "T_COMMENT",
                "T_KEYWORD_FROM", "T_KEYWORD_IN"
            ] or (nt.type == "T_IDENTIFIER" and nt.value in ["för", "som", "till"])

            if is_at_boundary and (has_forced_trigger or self._is_tree_valid(expr)):
                return expr
        except:
            if t.type == "T_KEYWORD_FUNC": raise

        self.pos = checkpoint
        txt = []
        while self.peek():
            nt = self.peek()
            if nt.type in ["T_NEWLINE", "T_DEDENT", "T_INDENT", "T_COMMENT", "T_KEYWORD_IN", "T_KEYWORD_FROM"]:
                break

            if nt.value in ["som", "för", "till"]:
                break

            txt.append(str(self.consume().value))

        raw_value = " ".join(txt)
        if raw_value.isdigit():
            return IntNode(int(raw_value))

        if ',' in raw_value and raw_value.replace(',', '').isdigit():
            return FloatNode(raw_value, token=t)

        return StringNode(raw_value, token=t)

    def expression(self):
        t = self.peek()
        if t and t.type == "T_IDENTIFIER" and t.value == "inte":
            self.consume() # consume 'inte'
            # Recursively parse the condition that follows, then wrap it in a NotNode
            cond_node = self.expression()
            return NotNode(cond_node, token=t)

        left = self.arithmetic()
        if isinstance(left, FunctionDefNode): return left

        while True:
            t = self.peek()
            if not t or t.type in ["T_NEWLINE", "T_INDENT", "T_DEDENT"]: break

            if t.type == "T_KEYWORD_IN":
                self.consume()
                left = ComparisonNode(left, "i", self.arithmetic(), token=t)
                continue

            if t.value == "som":
                self.consume() # consume 'som'
                target = self.consume("T_IDENTIFIER").value
                left = CastNode(left, target_type=target, token=t)
                continue # look for more operators

            if t.type == "T_OP_IS": self.consume(); t = self.peek()
            if not t: break
            if t.type in ["T_KEYWORD_GREATER", "T_KEYWORD_LESS", "T_KEYWORD_EQUAL", "T_OP_OR", "T_OP_AND"]:
                op_parts = []
                while self.peek() and (self.peek().type in ["T_KEYWORD_GREATER", "T_KEYWORD_LESS", "T_KEYWORD_EQUAL", "T_KEYWORD_THAN", "T_KEYWORD_WITH", "T_OP_OR", "T_OP_AND"] or (self.peek().type == "T_IDENTIFIER" and self.peek().value in ["eller", "lika", "med", "än", "och"])):
                    op_parts.append(self.consume().value)
                left = ComparisonNode(left, " ".join(op_parts), self.arithmetic(), token=t)
            else: break
        return left

    def arithmetic(self):
        left = self.term()
        if isinstance(left, FunctionDefNode): return left

        while self.peek():
            t = self.peek()
            if t.type in ["T_NEWLINE", "T_INDENT", "T_DEDENT", "T_KEYWORD_IN", "T_KEYWORD_FROM"]: break

            if t.type == "T_OP_ADD": # 'plus'
                self.consume() # consume 'plus'

                # Check if the right side is a standard term (number/var)
                # or if we should just grab the rest of the line as a string
                checkpoint = self.pos
                try:
                    right = self.term()
                    # If the next token isn't another plus or EOL, this might be a string
                    if self.peek() and self.peek().type not in ["T_OP_ADD", "T_NEWLINE", "T_DEDENT", "T_INDENT"]:
                        raise Exception("Not a clean term")
                except:
                    self.pos = checkpoint
                    txt = []
                    # Gobble everything until the next plus or end of line
                    while self.peek() and self.peek().type not in ["T_OP_ADD", "T_NEWLINE", "T_DEDENT", "T_INDENT"]:
                        txt.append(str(self.consume().value))
                    right = StringNode(" ".join(txt), token=t)

                left = AddNode(left, right, token=t)
            elif t.type == "T_OP_SUB":
                self.consume()
                left = SubNode(left, self.term(), token=t)
            else:
                break
        return left

    def term(self):
        left = self.primary()
        if isinstance(left, FunctionDefNode): return left
        while self.peek() and self.peek().type in ["T_OP_MUL", "T_OP_DIV"]:
            if self.peek().type in ["T_NEWLINE", "T_INDENT", "T_KEYWORD_IN", "T_KEYWORD_FROM"]: break
            op_token = self.consume()
            op = op_token.type
            if op == "T_OP_DIV" and self.peek() and self.peek().value == "med": self.consume()
            right = self.primary()
            left = MulNode(left, right, token=op_token) if op == "T_OP_MUL" else DivNode(left, right, token=op_token)
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
            return FunctionDefNode(p, self.parse_block(params=p), token=t)

        if t.type == "T_IDENTIFIER" and t.value == "ny" and self.peek(1) and self.peek(1).value == "rad":
            self.consume(); self.consume(); return StringNode("\n", token=t)

        if t.type in ["T_IDENTIFIER", "T_KEYWORD_GREATER", "T_KEYWORD_LESS", "T_KEYWORD_EQUAL", "T_KEYWORD_IN"]:
            name = self.consume().value

            if name == ".":
                return StringNode(".", token=t)

            if not self.in_structural_statement:
                lookahead = 0
                while self.peek(lookahead) and self.peek(lookahead).type in ["T_IDENTIFIER", "T_KEYWORD_IN"]:
                    if self.peek(lookahead + 1) and self.peek(lookahead + 1).type == "T_KEYWORD_FROM":
                        for _ in range(lookahead + 1):
                            name += " " + self.consume().value
                        break
                    lookahead += 1

            if name == "längd":
                if self.peek() and self.peek().type == "T_KEYWORD_FROM":
                    self.consume() # från
                    t_parts = []
                    first_var_token=self.peek() if self.peek() and self.peek().type == "T_IDENTIFIER" else None
                    while self.peek() and self.peek().type == "T_IDENTIFIER":
                        t_parts.append(self.consume().value)

                    target = " ".join(t_parts)
                    # Maps 'längd från x' to a function call for the built-in
                    return FunctionCallNode("längd", [VarAccessNode(target, token=first_var_token)], token=t)

            # Index Get
            if name in ["element", "index"] and self.peek() and self.peek().type == "T_LITERAL_INT":
                idx = self.consume().value
                if self.peek() and self.peek().type == "T_KEYWORD_FROM":
                    self.consume()
                    parts = []
                    while self.peek() and self.peek().type == "T_IDENTIFIER": parts.append(self.consume().value)
                    return VarAccessNode(str(idx), target=" ".join(parts), token=t)

            # Property Get
            if not self.in_structural_statement and self.peek() and self.peek().type == "T_KEYWORD_FROM":
                self.consume()

                parts = []
                while self.peek() and self.peek().type == "T_IDENTIFIER":
                    parts.append(self.consume().value)

                target_namespace = " ".join(parts)
                prop_node = VarAccessNode(name, target=target_namespace, token=t)

                if self.peek() and self.peek().type == "T_KEYWORD_WITH":
                    self.consume() # med
                    args = []
                    while True:
                        arg_expr = self.expression()
                        if isinstance(arg_expr, VarAccessNode) and not self.is_var_known(arg_expr.name):
                            arg_expr = StringNode(arg_expr.name, token=t)
                        args.append(arg_expr)
                        if self.peek() and self.peek().type == "T_COMMA":
                            self.consume()
                        else:
                            break

                    return FunctionCallNode(prop_node, args, token=t)

                return prop_node

            # Multi-word Var
            while self.peek() and self.peek().type in ["T_IDENTIFIER", "T_KEYWORD_IN"]:
                combined = name + " " + self.peek().value
                if self.is_var_known(combined): name = combined; self.consume()
                else: break

            # Call
            if self.peek() and self.peek().type == "T_KEYWORD_WITH":
                self.consume(); args = []
                while True:
                    arg_expr = self.expression()
                    if isinstance(arg_expr, VarAccessNode) and not self.is_var_known(arg_expr.name): arg_expr = StringNode(arg_expr.name)
                    args.append(arg_expr)
                    if self.peek() and self.peek().type == "T_COMMA": self.consume()
                    else: break
                return FunctionCallNode(name, args, token=t)

            if name == "lista":
                args = []
                if self.peek() and self.peek().type == "T_KEYWORD_WITH":
                    self.consume()
                    while True:
                        args.append(self.expression())
                        if self.peek() and self.peek().type == "T_COMMA": self.consume()
                        else: break
                return FunctionCallNode(name, args, token=t)
            return VarAccessNode(name, token=t)

        if t.type == "T_LITERAL_INT": return IntNode(self.consume().value, token=t)
        if t.type == "T_LITERAL_FLOAT": return FloatNode(self.consume().value, token=t)
        if t.type == "T_LITERAL_TRUE": self.consume(); return BoolNode(True, token=t)
        if t.type == "T_LITERAL_FALSE": self.consume(); return BoolNode(False, token=t)
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
        self.exit_scope(); self.consume("T_DEDENT")
        return stmts

    def parse_if(self):
        if_token = self.consume("T_KEYWORD_IF")
        cond = self.expression()
        true_b = self.parse_block()
        false_b = None
        if self.peek() and self.peek().type == "T_KEYWORD_ELSE":
            self.consume(); false_b = self.parse_block()
        return IfNode(cond, true_b, false_b, token=if_token)

    def parse_while(self):
        while_token = self.consume("T_KEYWORD_WHILE")
        return WhileNode(self.expression(), self.parse_block(), token=while_token)

    def parse_try_catch(self):
        try_token = self.consume("T_KEYWORD_TRY")
        try_b = self.parse_block()

        err_var = None
        catch_b = None
        if self.peek() and self.peek().value == "fånga":
            self.consume() # fånga
            err_var = self.consume("T_IDENTIFIER").value
            catch_b = self.parse_block(params=[err_var])

        finally_b = None
        if self.peek() and self.peek().value == "slutligen":
            self.consume() # slutligen
            finally_b = self.parse_block()

        if not catch_b and not finally_b:
            raise SyntaxError("Ett 'försök' måste ha antingen 'fånga' eller 'slutligen'.")

        return TryCatchNode(try_b, err_var, catch_b, finally_b, token=try_token)

    def parse_type_def(self):
        type_def_token = self.consume("T_KEYWORD_TYPE")
        name = self.consume("T_IDENTIFIER").value
        self.known_types.add(name); self.define_var(name)
        f = []
        if self.peek() and self.peek().type == "T_KEYWORD_WITH":
            self.consume()
            while self.peek() and self.peek().type == "T_IDENTIFIER":
                f.append(self.consume().value)
                if self.peek() and self.peek().type == "T_COMMA": self.consume()
                else: break
        return TypeDefNode(name, f, token=type_def_token)
