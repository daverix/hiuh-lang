# -*- coding: utf-8 -*-
from hiuh.frontend.ast import *
from hiuh.frontend.tokenizer import (
    TOKEN_PRINT, TOKEN_SET, TOKEN_TO, TOKEN_WITH, TOKEN_GIVE,
    TOKEN_TYPE, TOKEN_FROM, TOKEN_IF, TOKEN_ELSE, TOKEN_TRY,
    TOKEN_THROW, TOKEN_CATCH, TOKEN_WHILE, TOKEN_IMPORT, TOKEN_OPEN,
    TOKEN_CLOSE, TOKEN_AS, TOKEN_LITERAL_INT,
    TOKEN_LITERAL_FLOAT, TOKEN_LITERAL_TRUE, TOKEN_LITERAL_FALSE,
    TOKEN_STRING, TOKEN_IDENTIFIER, TOKEN_NEWLINE, TOKEN_INDENT,
    TOKEN_DEDENT, TOKEN_COMMA, TOKEN_COPY, TOKEN_OF,
    TOKEN_FOR, TOKEN_EACH, TOKEN_FUNC,
    TOKEN_BREAK, TOKEN_CONTINUE, TOKEN_INHERITS
)

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.in_structural_statement = False
        self.infix_functions = set()
        self.verb_functions = {"öka", "minska", "gångra", "dela", "multiplicera", "dividera"}
        self.skicka_functions = set()
        self.hämta_functions = set()
        self.in_call_args = False

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
        if t.type == TOKEN_IDENTIFIER and t.value in self.verb_functions:
            return self._parse_verb_call()
        if t.type == TOKEN_IDENTIFIER and t.value in self.skicka_functions:
            return self._parse_skicka_call()
        if t.type == TOKEN_SET: return self.parse_assignment()
        if t.type == TOKEN_PRINT: return self.parse_print()
        if t.type == TOKEN_IF: return self.parse_if()
        if t.type == TOKEN_WHILE: return self.parse_while()
        if t.type == TOKEN_FOR: return self.parse_for_each()
        if t.type == TOKEN_BREAK:
            token = self.consume()
            return BreakNode(token=token)
        if t.type == TOKEN_CONTINUE:
            token = self.consume()
            return ContinueNode(token=token)
        if t.type == TOKEN_TYPE: return self.parse_type_def()
        if t.type == TOKEN_TRY: return self.parse_try_catch()
        if t.type == TOKEN_THROW:
            self.consume(); return UnaryOpNode("kasta", self.expression(), token=t)
        if t.type == TOKEN_GIVE:
            self.consume(); return ReturnNode(self.expression(), token=t)
        return self.expression()

    def parse_import(self):
        import_token = self.consume(TOKEN_IMPORT)
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
        # Collect value parts until 'i'
        val = self._collect_until("i")
        self._consume_keyword("i")
        # Parse list name
        parts = []
        while self.peek() and self.peek().type == TOKEN_IDENTIFIER:
            parts.append(self.consume().value)
        target = "".join(parts)
        return AppendNode(val, target, token=append_token)

    def parse_remove(self):
        remove_token = self.consume() # ta
        self.consume() # bort
        is_index_based = False
        if self.peek() and self.peek().value in ["element", "index"]:
            self.consume()
            is_index_based = True

        value_parts = []
        while self.peek() and self.peek().type != TOKEN_FROM:
            value_parts.append(self.consume().value)
        target_expr = ExpressionPartsNode(value_parts, token=self.peek()) if value_parts else None

        self.consume(TOKEN_FROM)

        parts = []
        while self.peek() and self.peek().type == TOKEN_IDENTIFIER:
            parts.append(self.consume().value)
        list_name = " ".join(parts)

        if is_index_based:
            return RemoveIndexNode(target_expr, list_name, token=remove_token)
        return RemoveValueNode(target_expr, list_name, token=remove_token)

    def _parse_verb_call(self):
        """Parse 'öka <target> med <value>' as AddAssignNode etc.
        These map directly to x86 opcodes (ADD, SUB, MUL, DIV)."""
        verb_token = self.consume()
        verb_name = verb_token.value
        # Collect target until 'med'
        target_parts = []
        while self.peek() and self.peek().type != TOKEN_WITH:
            target_parts.append(self.consume().value)
        target = " ".join(target_parts)
        self.consume(TOKEN_WITH)  # consume 'med'
        val = self.expression()
        # Map verb to specialized AST node
        node_map = {
            "öka": AddAssignNode,
            "minska": SubAssignNode,
            "gångra": MultiplyAssignNode,
            "multiplicera": MultiplyAssignNode,
            "dela": DivideAssignNode,
            "dividera": DivideAssignNode,
        }
        node_class = node_map.get(verb_name)
        if node_class:
            return node_class(target, val, token=verb_token)
        # Unknown verb — fall back to function call
        return AssignNode(target, FunctionCallNode(verb_name, [VarAccessNode(target, token=verb_token), val], token=verb_token), token=verb_token)

    def _parse_skicka_call(self):
        """Parse 'skicka <thing> till <target>' as AssignNode(target, fn(args..., target))."""
        fn_token = self.consume()
        fn_name = fn_token.value
        # Collect thing parts until 'till', split at commas into multiple args
        all_thing_parts = []
        while self.peek() and self.peek().type != TOKEN_TO:
            all_thing_parts.append(self.consume().value)
        self.consume(TOKEN_TO)  # consume 'till'
        # Collect target
        target_parts = []
        while self.peek() and self.peek().type not in [TOKEN_NEWLINE, TOKEN_INDENT, TOKEN_DEDENT]:
            target_parts.append(self.consume().value)
        target = " ".join(target_parts)
        # Split thing parts into args at commas
        call_args = []
        current = []
        for p in all_thing_parts:
            if p == ',':
                if current:
                    call_args.append(ExpressionPartsNode(current, token=fn_token))
                current = []
            else:
                current.append(p)
        if current:
            call_args.append(ExpressionPartsNode(current, token=fn_token))
        # Add target as last arg
        call_args.append(VarAccessNode(target, token=fn_token))
        func_call = FunctionCallNode(fn_name, call_args, token=fn_token)
        return AssignNode(target, func_call, token=fn_token)

    def _parse_hämta_call(self):
        """Parse 'hämta <thing> från <source>' as FunctionCallNode(fn, [thing, source]).
        Unlike skicka, this does NOT assign — it just returns the value."""
        fn_token = self.consume()
        fn_name = fn_token.value
        # Collect thing parts until 'från'
        thing_parts = []
        while self.peek() and self.peek().type != TOKEN_FROM:
            thing_parts.append(self.consume().value)
        self.consume(TOKEN_FROM)  # consume 'från'
        # Collect source
        source_parts = []
        while self.peek() and self.peek().type not in [TOKEN_NEWLINE, TOKEN_INDENT, TOKEN_DEDENT]:
            source_parts.append(self.consume().value)
        source = " ".join(source_parts)
        # Build args: split thing at commas, then add source
        call_args = []
        current = []
        for p in thing_parts:
            if p == ',':
                if current:
                    call_args.append(ExpressionPartsNode(current, token=fn_token))
                current = []
            else:
                current.append(p)
        if current:
            call_args.append(ExpressionPartsNode(current, token=fn_token))
        call_args.append(VarAccessNode(source, token=fn_token))
        return FunctionCallNode(fn_name, call_args, token=fn_token)

    def parse_open_file(self):
        open_token = self.consume(TOKEN_OPEN)
        self.in_structural_statement = True
        try:
            t = self.peek()
            if t.type == TOKEN_STRING:
                path_expr = StringNode(self.consume().value, token=t)
            elif t.type == TOKEN_IDENTIFIER:
                path_expr = VarAccessNode(self.consume().value, token=t)
            else:
                raise SyntaxError("Förväntade filnamn eller sökväg")

            mode = "läsning"
            mode_token = open_token
            if self.peek() and self.peek().type == TOKEN_FOR:
                self.consume()
                mode_parts = []
                while self.peek() and self.peek().type == TOKEN_IDENTIFIER and self.peek().value not in ["som"]:
                    mode_parts.append(self.consume().value)
                mode = " ".join(mode_parts) if mode_parts else "läsning"

            if self.peek() and self.peek().type == TOKEN_AS:
                assign_token = self.consume()
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
        close_file_token = self.consume(TOKEN_CLOSE)
        parts = []
        while self.peek() and self.peek().type == TOKEN_IDENTIFIER:
            parts.append(self.consume().value)
        if not parts:
            raise SyntaxError(f"Förväntade en filvariabel efter 'stäng'")
        target = " ".join(parts)
        return CloseFileNode(target, token=close_file_token)

    def parse_assignment(self):
        assign_token = self.consume(TOKEN_SET)

        # Check for list element assignment: sätt element 0 i minlista till ...
        # Only match if "i" comes immediately after the index (the element assignment pattern)
        if self.peek() and self.peek().value in ["element", "index"]:
            # Peek ahead to check if "i" comes immediately after the index
            # We'll consume tokens only if the pattern matches
            saved_pos = self.pos
            saved_tokens = self.tokens[self.pos:]
            
            self.consume()  # consume "element" or "index"
            
            # Collect index parts (int literal or single identifier for variable)
            idx_parts = []
            while self.peek() and self.peek().type == TOKEN_LITERAL_INT:
                idx_parts.append(self.consume().value)
            if not idx_parts and self.peek() and self.peek().type == TOKEN_IDENTIFIER and self.peek().value != "i":
                idx_parts.append(self.consume().value)
            
            # Check if "i" comes immediately after
            if self.peek() and self.peek().type == TOKEN_IDENTIFIER and self.peek().value == "i":
                self.consume()  # consume "i"
                # Collect target list parts
                target_parts = []
                while self.peek() and self.peek().type == TOKEN_IDENTIFIER:
                    target_parts.append(self.consume().value)
                target = " ".join(target_parts)
                self.consume(TOKEN_TO)
                val = self.expression()
                return ElementAssignNode(" ".join(idx_parts), target, val, token=assign_token)
            
            # If "i" doesn't come immediately after, reset position and fall through
            self.pos = saved_pos

        # Collect variable name and consume 'till'
        name_parts = []
        while self.peek() and self.peek().type not in [TOKEN_TO, TOKEN_NEWLINE, TOKEN_INDENT, TOKEN_DEDENT]:
            name_parts.append(self.consume().value)
        name = " ".join(name_parts)
        self.consume(TOKEN_TO)
        
        # Check for function definition: "sätt x till grej med a, b"
        # Check by value since 'grej' can have different token types
        is_grej = self.peek() and self.peek().value == 'grej'
        is_infix_grej = (
            self.peek() and self.peek().value == 'infix'
            and self.peek(1) and self.peek(1).value == 'grej'
        )
        is_verb_grej = (
            self.peek() and self.peek().value == 'verb'
            and self.peek(1) and self.peek(1).value == 'grej'
        )
        is_skicka_grej = (
            self.peek() and self.peek().value == 'skicka'
            and self.peek(1) and self.peek(1).value == 'grej'
        )
        is_hämta_grej = (
            self.peek() and self.peek().value == 'hämta'
            and self.peek(1) and self.peek(1).value == 'grej'
        )
        
        if is_grej or is_infix_grej or is_verb_grej or is_skicka_grej or is_hämta_grej:
            is_infix = False
            if is_infix_grej:
                self.consume()  # consume 'infix'
                is_infix = True
            elif is_verb_grej:
                self.consume()  # consume 'verb'
            elif is_skicka_grej:
                self.consume()  # consume 'skicka'
            elif is_hämta_grej:
                self.consume()  # consume 'hämta'
            self.consume()  # consume 'grej'

            # Handle type parameters: 'grej av T1, T2'
            type_params = []
            if self.peek() and self.peek().type == TOKEN_OF:
                self.consume()  # consume 'av'
                while self.peek() and self.peek().type in (TOKEN_IDENTIFIER, TOKEN_FUNC, TOKEN_COMMA):
                    if self.peek().type == TOKEN_COMMA:
                        self.consume()
                    else:
                        type_params.append(self.consume().value)

            # Grej functions can have params (with 'med') or no params (just 'grej')
            params = []
            if self.peek() and self.peek().type == TOKEN_WITH:
                self.consume()  # consume 'med'
                params = self._parse_typed_params()

            # Parse body (indented block)
            body = self.parse_block(params=self._extract_param_names(params))
            func_def = FunctionDefNode(params, body, line=assign_token.line, column=assign_token.column, is_infix=is_infix, type_params=type_params)
            if is_infix_grej:
                func_def.kind = 'infix'
            if is_verb_grej:
                func_def.kind = 'verb'
                self.verb_functions.add(name)
            if is_skicka_grej:
                func_def.kind = 'skicka'
                self.skicka_functions.add(name)
            if is_hämta_grej:
                func_def.kind = 'hämta'
                self.hämta_functions.add(name)
            return AssignNode(name, func_def, target_type=None, token=assign_token)
        
        # Check for 'kopia av' pattern
        if self.peek() and self.peek().type == TOKEN_COPY:
            self.consume()
            if self.peek() and self.peek().type == TOKEN_OF:
                self.consume()
                source_parts = []
                while self.peek() and self.peek().type == TOKEN_IDENTIFIER and self.peek().value not in ["med"]:
                    source_parts.append(self.consume().value)
                source = " ".join(source_parts)
                if self.peek() and self.peek().type == TOKEN_WITH:
                    self.consume()
                    updates = self._parse_constructor_args(named_only=True)
                    if updates:
                        return CopyWithPropNode(name, source, updates, token=assign_token)
        
        # Standard assignment - parse expression value
        val = self.expression()
        return AssignNode(name, val, target_type=None, token=assign_token)

    def parse_print(self):
        print_token = self.consume(TOKEN_PRINT)
        checkpoint = self.pos
        try:
            val = self.expression()
            if self.peek() and self.peek().type == TOKEN_TO:
                self.consume()
                if self.peek() and self.peek().type == TOKEN_IDENTIFIER:
                    target_var = self.consume().value
                    return FileWriteNode(val, target_var, token=print_token)
        except:
            pass
        self.pos = checkpoint
        val = self.expression()
        return PrintNode(val, token=print_token)

    def _collect_until(self, *keywords):
        """Collect tokens until we hit one of the keywords."""
        parts = []
        while self.peek():
            t = self.peek()
            if t.type == TOKEN_IDENTIFIER and t.value in keywords:
                break
            parts.append(self.consume().value)
        
        return ExpressionPartsNode(parts, token=self.peek())

    def expression(self):
        """Parse expression - collect all tokens as strings for resolver to handle."""
        parts = []
        t = self.peek()
        
        while t and t.type not in [TOKEN_NEWLINE, TOKEN_INDENT, TOKEN_DEDENT]:
            parts.append(self.consume().value)
            t = self.peek()

        return ExpressionPartsNode(parts, token=t)

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
        """Parse a value for kopia av."""
        t = self.peek()
        if not t:
            return StringNode("", token=t)
        
        if t.type == TOKEN_LITERAL_INT:
            self.consume()
            return IntNode(t.value, token=t)
        if t.type == TOKEN_LITERAL_FLOAT:
            self.consume()
            return FloatNode(t.value, token=t)
        if t.type == TOKEN_LITERAL_TRUE:
            self.consume()
            return BoolNode(True, token=t)
        if t.type == TOKEN_LITERAL_FALSE:
            self.consume()
            return BoolNode(False, token=t)
        if t.type == TOKEN_STRING:
            self.consume()
            return StringNode(t.value, token=t)
        if t.type == TOKEN_IDENTIFIER:
            name_parts = [self.consume().value]
            while self.peek() and self.peek().type == TOKEN_IDENTIFIER and self.peek().value not in [","]:
                if self.peek(1) and self.peek(1).type == TOKEN_COMMA:
                    break
                name_parts.append(self.consume().value)
            name = " ".join(name_parts)
            # Strip optional type arguments: 'fn av T1, T2 med args' -> 'fn med args'
            if self.peek() and self.peek().type == TOKEN_OF:
                self.consume()  # consume 'av'
                # Consume type arguments until we hit 'med' or other
                while self.peek() and self.peek().type in (TOKEN_IDENTIFIER, TOKEN_FUNC, TOKEN_COMMA):
                    self.consume()
            if self.peek() and self.peek().type == TOKEN_WITH:
                self.consume()
                args = self._parse_function_call_args()
                return FunctionCallNode(name, args, token=t)
            return VarAccessNode(name, token=t)
        
        val = self.consume().value
        return StringNode(val, token=t)

    def _is_value_token(self, token):
        if token is None:
            return False
        return token.type in [
            TOKEN_LITERAL_INT, TOKEN_LITERAL_FLOAT, 
            TOKEN_LITERAL_TRUE, TOKEN_LITERAL_FALSE,
            TOKEN_STRING
        ] or (token.type == TOKEN_IDENTIFIER and token.value in ["SANT", "FALSKT"])

    def _parse_constructor_args(self, named_only=False):
        args = []
        
        while self.peek() and self.peek().type != TOKEN_NEWLINE:
            if self.peek().type == TOKEN_COMMA:
                self.consume()
                continue
            
            first_tok = self.peek()
            
            if named_only:
                if first_tok.type != TOKEN_IDENTIFIER:
                    break
                prop = self.consume().value
                value = self._parse_kopia_value()
                args.append((prop, value))
            else:
                if first_tok.type == TOKEN_IDENTIFIER:
                    next_tok = self.peek(1)
                    is_named = False
                    if next_tok and next_tok.type != TOKEN_COMMA:
                        if self._is_value_token(next_tok):
                            is_named = True
                    
                    if is_named:
                        prop = self.consume().value
                        value = self._parse_kopia_value()
                        args.append((prop, value))
                        continue
                
                value = self._parse_kopia_value()
                args.append(value)
            
            if self.peek() and self.peek().type != TOKEN_COMMA:
                break
        
        return args

    def _parse_function_call_args(self):
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

    def parse_if(self):
        if_token = self.consume(TOKEN_IF)
        first_cond = self.expression()
        first_block = self.parse_block()
        first_condition = IfCondition(first_cond, first_block, line=if_token.line, column=if_token.column)
        
        conditions = [first_condition]
        
        while self.peek() and self.peek().type == TOKEN_ELSE:
            self.consume()
            if self.peek() and self.peek().type == TOKEN_IF:
                self.consume()
                elif_cond = self.expression()
                elif_block = self.parse_block()
                elif_condition = IfCondition(elif_cond, elif_block)
                conditions.append(elif_condition)
            else:
                else_block = self.parse_block()
                return IfNode(conditions, else_block, line=if_token.line, column=if_token.column)
        
        return IfNode(conditions, line=if_token.line, column=if_token.column)

    def parse_while(self):
        while_token = self.consume(TOKEN_WHILE)
        return WhileNode(self.expression(), self.parse_block(), line=while_token.line, column=while_token.column)

    def parse_for_each(self):
        """Parse 'för varje <variable> i <expression>' loop.
        
        Syntax:
            för varje <variable> i <expression>
                <block>
        
        <variable> is collected until 'i' is encountered.
        <expression> is parsed as expression - must evaluate to a list.
        """
        for_token = self.consume(TOKEN_FOR)
        
        # Expect "varje"
        varje_tok = self.consume(TOKEN_EACH)
        if varje_tok.value != "varje":
            raise SyntaxError(f"Expected 'varje' but got '{varje_tok.value}' at line {varje_tok.line}")
        
        # Collect variable name (collect tokens until we hit 'i')
        var_parts = []
        while self.peek() and self.peek().type == TOKEN_IDENTIFIER and self.peek().value != "i":
            var_parts.append(self.consume().value)
        variable = " ".join(var_parts)
        
        if not variable:
            raise SyntaxError(f"Expected variable name after 'för varje' at line {for_token.line}")
        
        # Expect "i"
        i_tok = self.consume(TOKEN_IDENTIFIER)
        if i_tok.value != "i":
            raise SyntaxError(f"Expected 'i' but got '{i_tok.value}' at line {i_tok.line}")
        
        # Parse the iterable expression
        iterable = self.expression()
        
        # Parse the body block
        body = self.parse_block()
        
        return ForEachNode(variable, iterable, body, token=for_token)

    def parse_try_catch(self):
        try_token = self.consume(TOKEN_TRY)
        try_b = self.parse_block()

        err_var = None
        catch_b = None
        if self.peek() and self.peek().type == TOKEN_CATCH:
            self.consume()
            err_var = self.consume(TOKEN_IDENTIFIER).value
            catch_b = self.parse_block(params=[err_var])

        finally_b = None
        if self.peek() and self.peek().type == TOKEN_IDENTIFIER and self.peek().value == "slutligen":
            self.consume()
            finally_b = self.parse_block()

        if not catch_b and not finally_b:
            raise SyntaxError("Ett 'försök' måste ha antingen 'fånga' eller 'slutligen'.")

        return TryCatchNode(try_b, err_var, catch_b, finally_b, token=try_token)

    def _parse_typed_params(self):
        """Parse a comma-separated list of typed parameters after 'med'.
        
        Each parameter must have a type annotation: 'name som typ'.
        Type can be a generic type: 'lista av heltal', 'ordlista av sträng, heltal'.
        Returns a list of (name, type) tuples.
        """
        params = []
        while self.peek() and self.peek().type == TOKEN_IDENTIFIER:
            param_parts = []
            while self.peek() and self.peek().type == TOKEN_IDENTIFIER and self.peek().value not in [',']:
                param_parts.append(self.consume().value)
            if param_parts:
                param_name = ' '.join(param_parts)
                # Required type annotation
                if self.peek() and self.peek().type == TOKEN_AS:
                    self.consume()  # consume 'som'
                    # Parse type: greedy consumption until param-separator comma or end.
                    # Handles nested generics like 'lista av par av K, V'.
                    type_parts = []
                    while self.peek() and self.peek().type in (TOKEN_IDENTIFIER, TOKEN_FUNC, TOKEN_OF, TOKEN_COMMA):
                        if self.peek().type == TOKEN_COMMA:
                            # Is this comma a parameter separator?
                            # Pattern: comma + IDENTIFIER + som = new parameter.
                            next_tok = self.peek(1)
                            after_next = self.peek(2)
                            if (next_tok and next_tok.type == TOKEN_IDENTIFIER
                                    and after_next and after_next.type == TOKEN_AS):
                                break  # end of type, comma separates params
                            # Comma is part of the type (generic args) - consume it
                            type_parts.append(self.consume().value)
                        else:
                            type_parts.append(self.consume().value)
                    if type_parts:
                        param_type = ' '.join(type_parts)
                        # Clean up comma spacing: 'a , b' -> 'a, b'
                        while ' ,' in param_type:
                            param_type = param_type.replace(' ,', ',')
                        params.append((param_name, param_type))
                    else:
                        raise Exception(
                            f"Parametern/fältet '{param_name}' har en tom typ efter 'som'."
                        )
                else:
                    raise Exception(
                        f"Parametern/fältet '{param_name}' saknar typannotering. "
                        f"Använd syntaxen: 'namn som typ' (t.ex. 'text som sträng', 'start som heltal')"
                    )
            if self.peek() and self.peek().value == ',':
                self.consume()  # consume comma
            else:
                break
        return params

    def _extract_param_names(self, params):
        """Extract just the names from a list of params (which may be tuples or strings)."""
        return [p if isinstance(p, str) else p[0] for p in params]

    def parse_type_def(self):
        type_def_token = self.consume(TOKEN_TYPE)
        name = self.consume(TOKEN_IDENTIFIER).value

        # Optional generic type parameters: 'av T1, T2, ...'
        type_params = []
        if self.peek() and self.peek().type == TOKEN_OF:
            self.consume()  # consume 'av'
            # Parse type parameter names (just identifiers, no type annotation)
            while self.peek() and self.peek().type == TOKEN_IDENTIFIER:
                type_params.append(self.consume().value)
                if self.peek() and self.peek().type == TOKEN_COMMA:
                    self.consume()  # consume comma
                else:
                    break

        # Optional inheritance: 'ärver Parent1 av T1, Parent2, ...'
        parent_types = []
        if self.peek() and self.peek().type == TOKEN_INHERITS:
            self.consume()  # consume 'ärver'
            while True:
                parent_parts = []
                while self.peek() and self.peek().type == TOKEN_IDENTIFIER:
                    parent_parts.append(self.consume().value)
                parent_name = ' '.join(parent_parts)
                if not parent_name:
                    raise SyntaxError(f"Förväntade typnamn efter 'ärver'")
                parent_params = []
                if self.peek() and self.peek().type == TOKEN_OF:
                    self.consume()
                    while self.peek() and self.peek().type in (TOKEN_IDENTIFIER, TOKEN_OF, TOKEN_COMMA):
                        parent_params.append(self.consume().value)
                parent_types.append((parent_name, parent_params))
                if self.peek() and self.peek().type == TOKEN_COMMA:
                    self.consume()
                else:
                    break

        fields = []
        # Single-line form: 'med field1 som T1, field2 som T2'
        if self.peek() and self.peek().type == TOKEN_WITH:
            self.consume()
            fields = self._parse_typed_params()
        # Multi-line form: fields defined in an indented block
        elif self.peek() and self.peek().type == TOKEN_NEWLINE:
            self.consume()  # consume newline
            fields = self._parse_type_def_body(type_params)

        return TypeDefNode(name, fields, token=type_def_token, type_params=type_params,
                          parent_types=parent_types)

    def _parse_type_def_body(self, type_params):
        """Parse a multi-line typ body where each line is a field declaration.

        Each field must be a 'name som typ' declaration.
        The type can reference the type_params (e.g. K, V) declared in the typ.
        """
        fields = []
        # Expect INDENT
        if not (self.peek() and self.peek().type == TOKEN_INDENT):
            return fields
        self.consume()  # consume INDENT

        while self.peek() and self.peek().type != TOKEN_DEDENT:
            if self.peek().type == TOKEN_NEWLINE:
                self.consume()  # skip blank lines
                continue

            # Each line must start with an identifier (the field name)
            if not (self.peek() and self.peek().type == TOKEN_IDENTIFIER):
                raise Exception(
                    f"Typfält måste vara en variabeldeklaration: 'namn som typ'. "
                    f"Hittade: {self.peek().value if self.peek() else 'slut på fil'}"
                )

            field_name = self.consume().value
            # Required type annotation
            if self.peek() and self.peek().type == TOKEN_AS:
                self.consume()  # consume 'som'
                # Parse the type: consume everything until newline, dedent, or comma
                # Generic args can be on the same line, separated by commas
                type_parts = []
                while self.peek() and self.peek().type not in (TOKEN_NEWLINE, TOKEN_DEDENT):
                    if self.peek().type in (TOKEN_IDENTIFIER, TOKEN_FUNC, TOKEN_OF, TOKEN_COMMA):
                        type_parts.append(self.consume().value)
                    else:
                        break
                if not type_parts:
                    raise Exception(
                        f"Typfältet '{field_name}' har en tom typ efter 'som'."
                    )
                field_type = ' '.join(type_parts).replace(' ,', ',').replace(', ', ', ').replace(',,', ',')
                # Clean up: remove trailing commas
                field_type = field_type.strip().rstrip(',').strip()
                fields.append((field_name, field_type))
            else:
                raise Exception(
                    f"Typfältet '{field_name}' saknar typannotering. "
                    f"Använd syntaxen: 'namn som typ' (t.ex. 'värde som heltal')"
                )

            # Skip any comma (in case generic args were on same line)
            if self.peek() and self.peek().type == TOKEN_COMMA:
                self.consume()

            # Expect NEWLINE at end of field declaration
            if self.peek() and self.peek().type == TOKEN_NEWLINE:
                self.consume()
            elif self.peek() and self.peek().type == TOKEN_DEDENT:
                break
            else:
                raise Exception(
                    f"Förväntade ny rad efter typfältet '{field_name}'."
                )

        if self.peek() and self.peek().type == TOKEN_DEDENT:
            self.consume()  # consume DEDENT

        return fields
