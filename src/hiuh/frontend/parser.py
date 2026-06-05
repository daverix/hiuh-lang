# -*- coding: utf-8 -*-
from hiuh.frontend.ast import *
from hiuh.frontend.tokenizer import (
    TOKEN_PRINT, TOKEN_SET, TOKEN_TO, TOKEN_FUNC, TOKEN_WITH, TOKEN_GIVE,
    TOKEN_TYPE, TOKEN_IN, TOKEN_FROM, TOKEN_IF, TOKEN_ELSE, TOKEN_TRY,
    TOKEN_THROW, TOKEN_CATCH, TOKEN_WHILE, TOKEN_IMPORT, TOKEN_OPEN,
    TOKEN_CLOSE, TOKEN_AS, TOKEN_GREATER, TOKEN_LESS, TOKEN_EQUAL,
    TOKEN_THAN, TOKEN_OR, TOKEN_AND, TOKEN_OP_ADD, TOKEN_OP_SUB,
    TOKEN_OP_MUL, TOKEN_OP_DIV, TOKEN_OP_IS, TOKEN_LITERAL_INT,
    TOKEN_LITERAL_FLOAT, TOKEN_LITERAL_TRUE, TOKEN_LITERAL_FALSE,
    TOKEN_STRING, TOKEN_IDENTIFIER, TOKEN_NEWLINE, TOKEN_INDENT,
    TOKEN_DEDENT, TOKEN_COMMA, TOKEN_COPY, TOKEN_OF, TOKEN_INFIX
)

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.in_structural_statement = False

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

    def _consume_keyword(self, value):
        token = self.peek()
        if not token or token.type != TOKEN_IDENTIFIER or token.value != value:
            raise SyntaxError(f"Expected keyword '{value}' but got {token.value if token else 'None'} at line {token.line if token else 'EOF'}")
        self.consume()

    def parse(self):
        nodes = []
        while self.peek():
            t = self.peek()
            if t.type in [TOKEN_NEWLINE, TOKEN_DEDENT, TOKEN_INDENT]:
                self.consume(); continue
            nodes.append(self.statement())
        return nodes

    def statement(self):
        t = self.peek()
        if not t: return None

        if t.type == TOKEN_IMPORT:
            return self.parse_import()

        if t.type == TOKEN_OPEN:
            return self.parse_open_file()
        if t.type == TOKEN_CLOSE:
            return self.parse_close_file()

        if t.type == TOKEN_IDENTIFIER and t.value == "lägg":
            if self.peek(1) and self.peek(1).value == "till":
                return self.parse_append()
        if t.type == TOKEN_IDENTIFIER and t.value == "ta":
            if self.peek(1) and self.peek(1).value == "bort":
                return self.parse_remove()
        if t.type == TOKEN_SET: return self.parse_assignment()
        if t.type == TOKEN_PRINT: return self.parse_print()
        if t.type == TOKEN_IF: return self.parse_if()
        if t.type == TOKEN_WHILE: return self.parse_while()
        if t.type == TOKEN_TYPE: return self.parse_type_def()
        if t.type == TOKEN_TRY: return self.parse_try_catch()
        if t.type == TOKEN_THROW:
            self.consume(); return UnaryOpNode("kasta", self.parse_greedy_expression(), token=t)
        if t.type == TOKEN_GIVE:
            self.consume(); return ReturnNode(self.expression(), token=t)
        return self.expression()

    def parse_import(self):
        import_token = self.consume(TOKEN_IMPORT)
        # Parse module name - simple identifier or string
        t = self.peek()
        if t.type == TOKEN_STRING:
            module_name = self.consume().value
        elif t.type == TOKEN_IDENTIFIER:
            module_name = self.consume().value
        else:
            raise SyntaxError("Förväntade modulnamn")

        alias = None
        import_all = False
        if self.peek() and self.peek().type == TOKEN_AS:
            self.consume()
            parts = []
            while self.peek() and self.peek().type == TOKEN_IDENTIFIER:
                parts.append(self.consume().value)
            alias = " ".join(parts)
        else:
            import_all = True

        return ImportNode(module_name, alias, import_all=import_all, token=import_token)

    def parse_append(self):
        append_token = self.consume()  # lägg
        self.consume()  # till

        # Parse the value - use term() which stops before an 'i' identifier
        val = self.term()

        # Expect 'i'
        self._consume_keyword("i")

        # Parse the list name (multi-word support)
        parts = []
        while self.peek() and self.peek().type == TOKEN_IDENTIFIER:
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

        self.consume(TOKEN_FROM) # från

        # Parse the 'where' (the list name)
        parts = []
        while self.peek() and self.peek().type == TOKEN_IDENTIFIER:
            parts.append(self.consume().value)
        list_name = " ".join(parts)

        if is_index_based:
            return RemoveIndexNode(target_expr, list_name, token=remove_token)

        return RemoveValueNode(target_expr, list_name, token=remove_token)

    def parse_open_file(self):
        open_token = self.consume(TOKEN_OPEN)
        self.in_structural_statement = True
        try:
            # Parse path - string literal or identifier (let resolver handle conversion)
            t = self.peek()
            if t.type == TOKEN_STRING:
                path_expr = StringNode(self.consume().value, token=t)
            elif t.type == TOKEN_IDENTIFIER:
                path_expr = VarAccessNode(self.consume().value, token=t)
            else:
                raise SyntaxError("Förväntade filnamn eller sökväg")

            mode = "läsning"
            mode_token = open_token
            # Check for 'för mode' after path
            if self.peek() and self.peek().type == TOKEN_IDENTIFIER and self.peek().value == "för":
                self.consume()  # för
                # Consume mode identifier (could be multi-word)
                mode_parts = []
                while self.peek() and self.peek().type == TOKEN_IDENTIFIER and self.peek().value not in ["som"]:
                    mode_parts.append(self.consume().value)
                mode = " ".join(mode_parts) if mode_parts else "läsning"

            if self.peek() and self.peek().type == TOKEN_AS:
                assign_token = self.consume()  # som
            else:
                raise SyntaxError("Förväntade 'som' efter filnamnet")
        finally:
            self.in_structural_statement = False

        parts = []
        while self.peek() and self.peek().type == TOKEN_IDENTIFIER:
            parts.append(self.consume().value)
        var_name = " ".join(parts)


        function_call_args = [path_expr, StringNode(mode, token=mode_token)]
        function_call_node = FunctionCallNode("öppna", function_call_args, token=open_token)
        return AssignNode(var_name, function_call_node, target_type=None, token=assign_token)

    def parse_close_file(self):
        close_file_token = self.consume(TOKEN_CLOSE) # Consumes 'stäng'

        # Greedy identifier consumption to match multi-word file names
        parts = []
        while self.peek() and self.peek().type == TOKEN_IDENTIFIER:
            parts.append(self.consume().value)

        if not parts:
            raise SyntaxError(f"Förväntade en filvariabel efter 'stäng' på rad {self.peek().line if self.peek() else 'EOF'}")

        target = " ".join(parts)
        return CloseFileNode(target, token=close_file_token)

    def parse_assignment(self):
        assign_token = self.consume(TOKEN_SET)

        # Check for list indexing: sätt element 0 i minlista till ...
        if self.peek() and self.peek().value in ["element", "index"] and self.peek(1).type == TOKEN_LITERAL_INT:
            self.consume() # 'element'
            idx = self.consume().value
            self._consume_keyword("i") # 'i'
            target_parts = []
            while self.peek() and self.peek().type == TOKEN_IDENTIFIER:
                target_parts.append(self.consume().value)
            target = " ".join(target_parts)
            self.consume(TOKEN_TO)
            val = self.parse_greedy_expression()
            return AssignNode(str(idx), val, target_type=target, token=assign_token)

        # Check for 'kopia av' pattern: sätt X till kopia av Y med P V, P V, P V
        kopia_checkpoint = self.pos
        if self.peek() and self.peek().type == TOKEN_IDENTIFIER:
            # Try to detect 'kopia av' pattern
            # Collect variable name (could be multi-word)
            name_parts = [self.consume().value]
            while self.peek() and self.peek().type == TOKEN_IDENTIFIER and self.peek().value != "till":
                name_parts.append(self.consume().value)
            name = " ".join(name_parts)
            
            if self.peek() and self.peek().type == TOKEN_TO:  # till
                self.consume()  # consume 'till'
                if self.peek() and self.peek().type == TOKEN_COPY:  # kopia
                    self.consume()  # consume 'kopia'
                    if self.peek() and self.peek().type == TOKEN_OF:  # av
                        self.consume()  # consume 'av'
                        # Parse source object name (could be multi-word)
                        source_parts = []
                        while self.peek() and self.peek().type == TOKEN_IDENTIFIER and self.peek().value not in ["med"]:
                            source_parts.append(self.consume().value)
                        source = " ".join(source_parts)
                        if self.peek() and self.peek().type == TOKEN_WITH:  # med
                            self.consume()  # consume 'med'
                            # Parse named prop-value pairs (kopia av always uses named args)
                            updates = self._parse_constructor_args(named_only=True)
                            if updates:
                                return CopyWithPropNode(name, source, updates, token=assign_token)
        
        # Reset to start of assignment if we didn't match kopia av pattern
        self.pos = kopia_checkpoint
        
        # Standard assignment
        parts = []
        while self.peek() and self.peek().type == TOKEN_IDENTIFIER and self.peek().value != "till":
            parts.append(self.consume().value)
        
        name = " ".join(parts)

        self.consume(TOKEN_TO)
        val = self.parse_greedy_expression()

        return AssignNode(name, val, target_type=None, token=assign_token)

    def parse_print(self):
        print_token = self.consume(TOKEN_PRINT)

        # Check for file writing syntax first, as it's more specific
        checkpoint = self.pos
        try:
            val = self.expression()
            if self.peek() and self.peek().type == TOKEN_TO:
                self.consume() # till
                # The next token must be a plain identifier
                if self.peek() and self.peek().type == TOKEN_IDENTIFIER:
                    target_var = self.consume().value
                    return FileWriteNode(val, target_var, token=print_token)
        except Exception:
            pass # Fallback to greedy expression

        # If it wasn't a file write, reset and parse greedily
        self.pos = checkpoint
        val = self.parse_greedy_expression()
        return PrintNode(val, token=print_token)

    def parse_greedy_expression(self):
        while self.peek() and self.peek().type in [TOKEN_NEWLINE]:
            self.consume()

        t = self.peek()
        if not t or t.type in [TOKEN_DEDENT, TOKEN_INDENT]:
            return None

        if t.type == TOKEN_IDENTIFIER and t.value == "ny" and self.peek(1) and self.peek(1).value == "rad":
            self.consume(); self.consume()
            return StringNode("\n", token=t)

        checkpoint = self.pos

        try:
            expr = self.expression()
            if isinstance(expr, (FunctionDefNode, FunctionCallNode)): return expr

            nt = self.peek()
            # Check if this is a function call: expression followed by "med args"
            if nt and nt.type == TOKEN_WITH:
                # It's a function call! Consume 'med' and parse arguments
                self.consume()  # consume 'med'
                args = []
                while True:
                    arg_expr = self.expression()
                    # Keep VarAccessNode
                    args.append(arg_expr)
                    if self.peek() and self.peek().type == TOKEN_COMMA:
                        self.consume()
                    else:
                        break
                return FunctionCallNode(expr.name if hasattr(expr, 'name') else str(expr), args, token=t)

            is_at_boundary = not nt or nt.type in [
                TOKEN_NEWLINE, TOKEN_DEDENT, TOKEN_INDENT,
                TOKEN_FROM
            ] or (nt.type == TOKEN_IDENTIFIER and nt.value in ["för", "som", "till", "i"])

            if is_at_boundary:
                return expr
        except:
            if t.type == TOKEN_FUNC: raise

        self.pos = checkpoint
        txt = []
        while self.peek():
            nt = self.peek()
            if nt.type in [TOKEN_NEWLINE, TOKEN_DEDENT, TOKEN_INDENT, TOKEN_FROM]:
                break
            if nt.type == TOKEN_IDENTIFIER and nt.value in ["som", "för", "till", "i"]:
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
        if t and t.type == TOKEN_IDENTIFIER and t.value == "inte":
            self.consume() # consume 'inte'
            # Recursively parse the condition that follows, then wrap it in a NotNode
            cond_node = self.expression()
            return NotNode(cond_node, token=t)

        left = self.arithmetic()
        if isinstance(left, FunctionDefNode): return left

        while True:
            t = self.peek()
            if not t or t.type in [TOKEN_NEWLINE, TOKEN_INDENT, TOKEN_DEDENT]: break

            if t.type == TOKEN_IDENTIFIER and t.value == "i":
                self.consume()
                left = ComparisonNode(left, "i", self.arithmetic(), token=t)
                continue

            if t.value == "som":
                self.consume() # consume 'som'
                target = self.consume(TOKEN_IDENTIFIER).value
                left = CastNode(left, target_type=target, token=t)
                continue # look for more operators

            if t.type == TOKEN_OP_IS: self.consume(); t = self.peek()
            if not t: break
            if t.type in [TOKEN_GREATER, TOKEN_LESS, TOKEN_EQUAL, TOKEN_OR, TOKEN_AND]:
                op_parts = []
                while self.peek() and (self.peek().type in [TOKEN_GREATER, TOKEN_LESS, TOKEN_EQUAL, TOKEN_THAN, TOKEN_WITH, TOKEN_OR, TOKEN_AND] or (self.peek().type == TOKEN_IDENTIFIER and self.peek().value in ["eller", "lika", "med", "än", "och"])):
                    op_parts.append(self.consume().value)
                left = ComparisonNode(left, " ".join(op_parts), self.arithmetic(), token=t)
            else: break
        return left

    def arithmetic(self):
        left = self.term()
        if isinstance(left, FunctionDefNode): return left

        while self.peek():
            t = self.peek()
            if t.type in [TOKEN_NEWLINE, TOKEN_INDENT, TOKEN_DEDENT, TOKEN_FROM] or \
               (t.type == TOKEN_IDENTIFIER and t.value == "i"): 
                break

            if t.type == TOKEN_OP_ADD: # 'plus'
                self.consume() # consume 'plus'

                # Check if the right side is a standard term (number/var)
                # or if we should just grab the rest of the line as a string
                checkpoint = self.pos
                try:
                    right = self.term()
                    # If the next token isn't another plus or EOL, this might be a string
                    if self.peek() and self.peek().type not in [TOKEN_OP_ADD, TOKEN_NEWLINE, TOKEN_DEDENT, TOKEN_INDENT]:
                        raise Exception("Not a clean term")
                except:
                    self.pos = checkpoint
                    txt = []
                    # Gobble everything until the next plus or end of line
                    while self.peek() and self.peek().type not in [TOKEN_OP_ADD, TOKEN_NEWLINE, TOKEN_DEDENT, TOKEN_INDENT]:
                        txt.append(str(self.consume().value))
                    right = StringNode(" ".join(txt), token=t)

                left = AddNode(left, right, token=t)
            elif t.type == TOKEN_OP_SUB:
                self.consume()
                left = SubNode(left, self.term(), token=t)
            else:
                break
        return left

    def term(self):
        left = self.primary()
        if isinstance(left, FunctionDefNode): return left
        while self.peek() and self.peek().type in [TOKEN_OP_MUL, TOKEN_OP_DIV]:
            if self.peek().type in [TOKEN_NEWLINE, TOKEN_INDENT, TOKEN_FROM] or \
               (self.peek().type == TOKEN_IDENTIFIER and self.peek().value == "i"):
                break
            op_token = self.consume()
            op = op_token.type
            if op == TOKEN_OP_DIV and self.peek() and self.peek().value == "med": self.consume()
            right = self.primary()
            left = MulNode(left, right, token=op_token) if op == TOKEN_OP_MUL else DivNode(left, right, token=op_token)
        return left

    def primary(self):
        t = self.peek()
        if not t: raise SyntaxError("Expected primary")

        if t.type == TOKEN_FUNC:
            self.consume(); p = []
            if self.peek() and self.peek().type == TOKEN_WITH:
                self.consume()
                while self.peek() and self.peek().type == TOKEN_IDENTIFIER:
                    p.append(self.consume().value)
                    if self.peek() and self.peek().type == TOKEN_COMMA: self.consume()
                    else: break
            return FunctionDefNode(p, self.parse_block(params=p), line=t.line, column=t.column)

        if t.type == TOKEN_IDENTIFIER and t.value == "ny" and self.peek(1) and self.peek(1).value == "rad":
            self.consume(); self.consume(); return StringNode("\n", token=t)

        if t.type in [TOKEN_IDENTIFIER, TOKEN_PRINT, TOKEN_SET, TOKEN_TO, TOKEN_WITH, TOKEN_GIVE, TOKEN_FUNC, TOKEN_TYPE, TOKEN_FROM, TOKEN_IF, TOKEN_ELSE, TOKEN_WHILE, TOKEN_TRY, TOKEN_THROW, TOKEN_CATCH, TOKEN_OPEN, TOKEN_CLOSE, TOKEN_AS, TOKEN_OP_IS, TOKEN_GREATER, TOKEN_LESS, TOKEN_EQUAL, TOKEN_THAN, TOKEN_OP_MUL, TOKEN_OP_ADD, TOKEN_OP_SUB, TOKEN_OP_DIV, TOKEN_OR, TOKEN_AND, TOKEN_IMPORT]:
            name = self.consume().value

            if name == ".":
                return StringNode(".", token=t)

            # Special handling for 'element x från list' pattern (index with variable name)
            # This must come BEFORE the lookahead loop which would consume 'x'
            if name in ["element", "index"] and self.peek() and self.peek().type == TOKEN_IDENTIFIER:
                # Tokens are: element (TOKEN_IDENTIFIER), x (TOKEN_IDENTIFIER), från (TOKEN_FROM)
                if self.peek(1) and self.peek(1).type == TOKEN_FROM:
                    idx_name = self.consume().value  # consume 'x'
                    self.consume()  # consume 'från'
                    parts = []
                    while self.peek() and self.peek().type == TOKEN_IDENTIFIER:
                        parts.append(self.consume().value)
                    target = " ".join(parts)
                    return VarAccessNode(idx_name, target=target, token=t)

            if not self.in_structural_statement:
                lookahead = 0
                while self.peek(lookahead) and self.peek(lookahead).type == TOKEN_IDENTIFIER:
                    # Check if this is "i" followed by "från" - then it's part of identifier, not membership check
                    if self.peek(lookahead).value == "i":
                        if self.peek(lookahead + 1) and self.peek(lookahead + 1).type == TOKEN_FROM:
                            # "i" followed by "från" - continue extending
                            pass
                        else:
                            # "i" NOT followed by "från" - this is membership check, stop extending
                            break
                    
                    next_tok = self.peek(lookahead)
                    next_combined = name + " " + next_tok.value
                    
                    # Always extend the name by consuming identifiers
                    name = next_combined
                    self.consume()
                    lookahead = 0  # Reset to check from current position
                    continue
                
                # After the loop, check if the current name followed by "med" is a function call
                if self.peek() and self.peek().type == TOKEN_WITH:
                    # It's a function call! Check if we need to extend the name first
                    # Look ahead to see if we can build up more of the name
                    temp_pos = self.pos
                    temp_name = name
                    while self.peek() and self.peek().type == TOKEN_IDENTIFIER:
                        temp_name += " " + self.consume().value
                    
                    # Now check if next token is "med"
                    if self.peek() and self.peek().type == TOKEN_WITH:
                        name = temp_name
                        self.consume()  # consume 'med'
                        args = self._parse_call_args()
                        return FunctionCallNode(name, args, token=t)
                    else:
                        # Not a function call, restore position
                        self.pos = temp_pos

            if name == "längd":
                if self.peek() and self.peek().type == TOKEN_FROM:
                    self.consume() # från
                    t_parts = []
                    first_var_token=self.peek() if self.peek() and self.peek().type == TOKEN_IDENTIFIER else None
                    while self.peek() and self.peek().type == TOKEN_IDENTIFIER:
                        t_parts.append(self.consume().value)

                    target = " ".join(t_parts)
                    # Maps 'längd från x' to a function call for the built-in
                    return FunctionCallNode("längd", [VarAccessNode(target, token=first_var_token)], token=t)

            # Index Get (integer index: element 0 from x, or variable index: element i from x)
            if name in ["element", "index"] and self.peek() and self.peek().type == TOKEN_LITERAL_INT:
                idx_token = self.consume()
                idx = idx_token.value
                if self.peek() and self.peek().type == TOKEN_FROM:
                    self.consume()
                    parts = []
                    while self.peek() and self.peek().type == TOKEN_IDENTIFIER: parts.append(self.consume().value)
                    return VarAccessNode(str(idx), target=" ".join(parts), token=t)

            # Property Get
            if not self.in_structural_statement and self.peek() and self.peek().type == TOKEN_FROM:
                self.consume()

                parts = []
                while self.peek() and self.peek().type == TOKEN_IDENTIFIER:
                    parts.append(self.consume().value)

                target_namespace = " ".join(parts)
                prop_node = VarAccessNode(name, target=target_namespace, token=t)

                if self.peek() and self.peek().type == TOKEN_WITH:
                    self.consume() # med
                    args = []
                    while True:
                        arg_expr = self.expression()
                        args.append(arg_expr)
                        if self.peek() and self.peek().type == TOKEN_COMMA:
                            self.consume()
                        else:
                            break

                    return FunctionCallNode(prop_node, args, token=t)

                return prop_node

            # Multi-word Var
            while self.peek() and self.peek().type == TOKEN_IDENTIFIER:
                # Stop on "i" unless followed by "från" (property access pattern)
                if self.peek().value == "i":
                    if self.peek(1) and self.peek(1).type == TOKEN_FROM:
                        pass  # Continue - is property access
                    else:
                        break  # Stop - is membership check
                combined = name + " " + self.peek().value
                if combined: name = combined; self.consume()
                else: break

            # Check for property access after multi-word var (e.g., 'element i från värden')
            if not self.in_structural_statement and self.peek() and self.peek().type == TOKEN_IDENTIFIER and self.peek().value == "i":
                self.consume()  # consume 'i'
                # Check if next is 'från'
                if self.peek() and self.peek().type == TOKEN_FROM:
                    self.consume()
                    parts = []
                    while self.peek() and self.peek().type == TOKEN_IDENTIFIER:
                        parts.append(self.consume().value)
                    target_namespace = " ".join(parts)
                    prop_node = VarAccessNode(name, target=target_namespace, token=t)

                    if self.peek() and self.peek().type == TOKEN_WITH:
                        self.consume()
                        args = []
                        while True:
                            arg_expr = self.expression()
                            if isinstance(arg_expr, VarAccessNode) and not arg_expr.target:
                                arg_expr = StringNode(arg_expr.name, token=t)
                            args.append(arg_expr)
                            if self.peek() and self.peek().type == TOKEN_COMMA:
                                self.consume()
                            else:
                                break
                        return FunctionCallNode(prop_node, args, token=t)

                    return prop_node
                else:
                    # 'i' is not followed by 'från', put it back
                    self.pos -= 1
            elif not self.in_structural_statement and self.peek() and self.peek().type == TOKEN_FROM:
                # Direct 'från' property access
                self.consume()
                parts = []
                while self.peek() and self.peek().type == TOKEN_IDENTIFIER:
                    parts.append(self.consume().value)
                target_namespace = " ".join(parts)
                prop_node = VarAccessNode(name, target=target_namespace, token=t)

                if self.peek() and self.peek().type == TOKEN_WITH:
                    self.consume()
                    args = []
                    while True:
                        arg_expr = self.expression()
                        if isinstance(arg_expr, VarAccessNode) and not arg_expr.target:
                            arg_expr = StringNode(arg_expr.name, token=t)
                        args.append(arg_expr)
                        if self.peek() and self.peek().type == TOKEN_COMMA:
                            self.consume()
                        else:
                            break
                        return FunctionCallNode(prop_node, args, token=t)

                return prop_node

            # Call
            if self.peek() and self.peek().type == TOKEN_WITH:
                self.consume()  # consume 'med'
                args = self._parse_call_args()
                return FunctionCallNode(name, args, token=t)

            if name == "lista":
                args = []
                if self.peek() and self.peek().type == TOKEN_WITH:
                    self.consume()
                    args = self._parse_call_args()
                return FunctionCallNode(name, args, token=t)
            
            # Multi-word function call: check if we just parsed a known function name
            # followed by "med args"
            if self.peek() and self.peek().type == TOKEN_WITH:
                self.consume()  # consume 'med'
                args = self._parse_call_args()
                return FunctionCallNode(name, args, token=t)
            
            return VarAccessNode(name, token=t)

        if t.type == TOKEN_LITERAL_INT: return IntNode(self.consume().value, token=t)
        if t.type == TOKEN_LITERAL_FLOAT: return FloatNode(self.consume().value, token=t)
        if t.type == TOKEN_LITERAL_TRUE: self.consume(); return BoolNode(True, token=t)
        if t.type == TOKEN_LITERAL_FALSE: self.consume(); return BoolNode(False, token=t)
        if t.type == TOKEN_STRING: return StringNode(self.consume().value, token=t)
        raise SyntaxError(f"Unexpected {t.type} ({t.value}) at line {t.line}")

    def parse_block(self, params=None):
        while self.peek() and self.peek().type == TOKEN_NEWLINE: self.consume()
        self.consume(TOKEN_INDENT)
        stmts = []
        while self.peek() and self.peek().type != TOKEN_DEDENT:
            if self.peek().type in [TOKEN_NEWLINE]: self.consume(); continue
            stmts.append(self.statement())
        self.consume(TOKEN_DEDENT)
        return stmts

    def _parse_kopia_value(self):
        """Parse a value - stops at comma or end of expression.
        
        This is a simplified expression parser that handles single values like
        identifiers, numbers, strings, and simple function calls.
        """
        t = self.peek()
        if not t:
            return StringNode("", token=t)
        
        # Number literal
        if t.type == TOKEN_LITERAL_INT:
            self.consume()
            return IntNode(t.value, token=t)
        if t.type == TOKEN_LITERAL_FLOAT:
            self.consume()
            return FloatNode(t.value, token=t)
        
        # Boolean literals
        if t.type == TOKEN_LITERAL_TRUE:
            self.consume()
            return BoolNode(True, token=t)
        if t.type == TOKEN_LITERAL_FALSE:
            self.consume()
            return BoolNode(False, token=t)
        
        # String literal
        if t.type == TOKEN_STRING:
            self.consume()
            return StringNode(t.value, token=t)
        
        # Identifier - could be variable or function call
        if t.type == TOKEN_IDENTIFIER:
            # Try to build the identifier name (multi-word)
            name_parts = [self.consume().value]
            while self.peek() and self.peek().type == TOKEN_IDENTIFIER and self.peek().value not in [","]:
                # Check if next would be a comma - stop before it
                if self.peek(1) and self.peek(1).type == TOKEN_COMMA:
                    break
                name_parts.append(self.consume().value)
            name = " ".join(name_parts)
            
            # Check for function call: 'name med args'
            if self.peek() and self.peek().type == TOKEN_WITH:
                self.consume()  # consume 'med'
                args = self._parse_function_call_args()
                return FunctionCallNode(name, args, token=t)
            
            return VarAccessNode(name, token=t)
        
        # Fallback: consume as string
        val = self.consume().value
        return StringNode(val, token=t)

    def _is_value_token(self, token):
        """Check if a token could be a value (not a property name)."""
        if token is None:
            return False
        return token.type in [
            TOKEN_LITERAL_INT, TOKEN_LITERAL_FLOAT, 
            TOKEN_LITERAL_TRUE, TOKEN_LITERAL_FALSE,
            TOKEN_STRING
        ] or (token.type == TOKEN_IDENTIFIER and token.value in ["SANT", "FALSKT"])

    def _parse_constructor_args(self, named_only=False):
        """Parse constructor arguments supporting both named and positional args.
        
        Args:
            named_only: If True, always parse as named 'prop value' pairs (for kopia av)
                       If False, auto-detect based on first argument
        
        Returns:
            List of tuples for named args: [(prop, value), ...]
            List of values for positional args: [value, ...]
        """
        args = []
        
        while self.peek() and self.peek().type != TOKEN_NEWLINE:
            if self.peek().type == TOKEN_COMMA:
                self.consume()
                continue
            
            first_tok = self.peek()
            
            if named_only:
                # kopia av: always named prop value pairs
                if first_tok.type != TOKEN_IDENTIFIER:
                    break
                prop = self.consume().value
                value = self._parse_kopia_value()
                args.append((prop, value))
            else:
                # typ/grej: auto-detect named vs positional
                # Check if this looks like a named argument (prop followed by value)
                if first_tok.type == TOKEN_IDENTIFIER:
                    # Look at next token to determine if this is a property name
                    next_tok = self.peek(1)
                    
                    # If next is a value token (number, string, bool) or identifier 
                    # that could be a variable, check if we should treat as named
                    is_named = False
                    if next_tok and next_tok.type != TOKEN_COMMA:
                        # Check if pattern is: identifier (prop) followed by value-like token
                        # or identifier (prop) followed by another identifier that looks like a value
                        if self._is_value_token(next_tok):
                            is_named = True
                        elif (next_tok.type == TOKEN_IDENTIFIER and 
                              next_tok.value not in ["med", "till", "från", "som", "för", "om", "annars", "medan", "ge", "i", "eller", "och"]):
                            # Next is an identifier that could be a value - might be named
                            # But we need to look ahead more to be sure
                            pass
                    
                    if is_named:
                        prop = self.consume().value
                        value = self._parse_kopia_value()
                        args.append((prop, value))
                        continue
                
                # Positional argument
                value = self._parse_kopia_value()
                args.append(value)
            
            # Check for comma or end
            if self.peek() and self.peek().type != TOKEN_COMMA:
                break
        
        return args

    def _parse_function_call_args(self):
        """Parse function call arguments (positional only, for compatibility)."""
        args = []
        while True:
            if self.peek() and self.peek().type in [TOKEN_NEWLINE, TOKEN_DEDENT]:
                break
            if self.peek() and self.peek().type == TOKEN_COMMA:
                self.consume()
                continue
            arg = self.expression()
            if arg:
                args.append(arg)
            if self.peek() and self.peek().type != TOKEN_COMMA:
                break
        return args

    def _parse_constructor_or_function_args(self):
        """Parse arguments for typ constructors or function calls.
        
        Supports both named (prop value) and positional arguments.
        Detects format based on first token pattern.
        """
        args = []
        
        while self.peek() and self.peek().type not in [TOKEN_NEWLINE, TOKEN_DEDENT]:
            if self.peek().type == TOKEN_COMMA:
                self.consume()
                continue
            
            first_tok = self.peek()
            
            # Check if this looks like a named argument (prop followed by value)
            if first_tok.type == TOKEN_IDENTIFIER:
                next_tok = self.peek(1)
                
                # If next token is a value (number, string, bool) or an identifier
                # that could be a variable value, this might be a named argument
                if next_tok and next_tok.type != TOKEN_COMMA:
                    is_named = self._is_value_token(next_tok)
                    
                    if is_named:
                        prop = self.consume().value
                        value = self.expression()
                        args.append((prop, value))
                        continue
            
            # Positional argument - use expression parsing for full support
            arg_expr = self.expression()
            if arg_expr:
                args.append(arg_expr)
            
            # Check for comma or end
            if self.peek() and self.peek().type != TOKEN_COMMA:
                break
        
        return args

    def _parse_call_args(self):
        """Parse function call arguments, consuming all args until boundary.
        
        Unlike the previous loop, this keeps consuming until we hit a boundary
        (newline, dedent, etc.) or an unconsumed token that doesn't look like an arg.
        """
        args = []
        
        while self.peek() and self.peek().type not in [TOKEN_NEWLINE, TOKEN_DEDENT, TOKEN_INDENT]:
            if self.peek().type == TOKEN_COMMA:
                self.consume()
                continue
            
            arg_expr = self.expression()
            if arg_expr:
                args.append(arg_expr)
            else:
                # No expression parsed - probably at boundary
                break
        
        return args

    def parse_if(self):
        if_token = self.consume(TOKEN_IF)
        first_cond = self.expression()
        first_block = self.parse_block()
        first_condition = IfCondition(first_cond, first_block, line=if_token.line, column=if_token.column)
        
        conditions = [first_condition]
        
        # Handle annars om (elif) blocks
        while self.peek() and self.peek().type == TOKEN_ELSE:
            self.consume()  # consume 'annars'
            if self.peek() and self.peek().type == TOKEN_IF:
                self.consume()  # consume 'om'
                elif_cond = self.expression()
                elif_block = self.parse_block()
                elif_condition = IfCondition(elif_cond, elif_block)
                conditions.append(elif_condition)
            else:
                # Plain 'annars' (no 'om'), handle else block
                else_block = self.parse_block()
                return IfNode(conditions, else_block, line=if_token.line, column=if_token.column)
        
        return IfNode(conditions, line=if_token.line, column=if_token.column)

    def parse_while(self):
        while_token = self.consume(TOKEN_WHILE)
        return WhileNode(self.expression(), self.parse_block(), line=while_token.line, column=while_token.column)

    def parse_try_catch(self):
        try_token = self.consume(TOKEN_TRY)
        try_b = self.parse_block()

        err_var = None
        catch_b = None
        if self.peek() and self.peek().value == "fånga":
            self.consume() # fånga
            err_var = self.consume(TOKEN_IDENTIFIER).value
            catch_b = self.parse_block(params=[err_var])

        finally_b = None
        if self.peek() and self.peek().value == "slutligen":
            self.consume() # slutligen
            finally_b = self.parse_block()

        if not catch_b and not finally_b:
            raise SyntaxError("Ett 'försök' måste ha antingen 'fånga' eller 'slutligen'.")

        return TryCatchNode(try_b, err_var, catch_b, finally_b, token=try_token)

    def parse_type_def(self):
        type_def_token = self.consume(TOKEN_TYPE)
        name = self.consume(TOKEN_IDENTIFIER).value
        fields = []
        if self.peek() and self.peek().type == TOKEN_WITH:
            self.consume()
            while self.peek() and self.peek().type == TOKEN_IDENTIFIER:
                fields.append(self.consume().value)
                if self.peek() and self.peek().type == TOKEN_COMMA: self.consume()
                else: break
        return TypeDefNode(name, fields, token=type_def_token)
