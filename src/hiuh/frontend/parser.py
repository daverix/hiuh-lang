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
    TOKEN_BREAK, TOKEN_CONTINUE, TOKEN_INHERITS, TOKEN_RETURNS
)

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.in_structural_statement = False
        self.infix_functions = set()
        self.verb_functions = {"öka", "minska", "gångra", "dela", "multiplicera", "dividera"}
        self.skicka_functions = {"putta", "rensa"}
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
            return BreakNode(token.line, token.column)
        if t.type == TOKEN_CONTINUE:
            token = self.consume()
            return ContinueNode(token.line, token.column)
        if t.type == TOKEN_IDENTIFIER and t.value == "grejtyp":
            return self.parse_grejtyp()
        if t.type == TOKEN_TYPE: return self.parse_type_def()
        if t.type == TOKEN_TRY: return self.parse_try_catch()
        if t.type == TOKEN_THROW:
            self.consume(); return UnaryOpNode(t.line, t.column, "kasta", self.expression())
        if t.type == TOKEN_GIVE:
            self.consume(); return ReturnNode(t.line, t.column, self.expression())
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

        return ImportNode(import_token.line, import_token.column, module_name, alias, import_all=import_all)

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
        return AppendNode(append_token.line, append_token.column, val, target)

    def parse_remove(self):
        remove_token = self.consume() # ta
        self.consume() # bort
        is_index_based = False
        if self.peek() and self.peek().value in ["element", "index"]:
            self.consume()
            is_index_based = True

        val = self._collect_until(TOKEN_FROM)
        self.consume(TOKEN_FROM)

        parts = []
        while self.peek() and self.peek().type == TOKEN_IDENTIFIER:
            parts.append(self.consume().value)
        list_name = " ".join(parts)

        if is_index_based:
            return RemoveIndexNode(remove_token.line, remove_token.column, val, list_name)
        return RemoveValueNode(remove_token.line, remove_token.column, val, list_name)

    def _parse_verb_call(self):
        """Parse 'öka <target> med <value>' as AddAssignNode etc."""
        verb_token = self.consume()
        verb_name = verb_token.value
        target_parts = []
        while self.peek() and self.peek().type != TOKEN_WITH:
            target_parts.append(self.consume().value)
        target = " ".join(target_parts)
        self.consume(TOKEN_WITH)
        val = self.expression()
        node_map = {
            "öka": AddAssignNode, "minska": SubAssignNode,
            "gångra": MultiplyAssignNode, "multiplicera": MultiplyAssignNode,
            "dela": DivideAssignNode, "dividera": DivideAssignNode,
        }
        node_class = node_map.get(verb_name)
        if node_class:
            return node_class(verb_token.line, verb_token.column, target, val)
        return AssignNode(verb_token.line, verb_token.column, target,
            FunctionCallNode(verb_token.line, verb_token.column, verb_name,
                [VarAccessNode(verb_token.line, verb_token.column, target), val]))

    def _parse_fn_with_target(self, separator_type, assign_result=True):
        """Parse 'fn <thing> sep <target>' pattern used by skicka/hämta calls."""
        fn_token = self.consume()
        fn_name = fn_token.value
        # Collect thing parts until separator
        thing_parts = self._collect_until(separator_type)
        self.consume(separator_type)
        # Collect target
        target_parts = []
        while self.peek() and self.peek().type not in [TOKEN_NEWLINE, TOKEN_INDENT, TOKEN_DEDENT]:
            target_parts.append(self.consume().value)
        target = " ".join(target_parts)
        # Split thing parts into args at commas
        call_args = self._split_args_at_commas(thing_parts, fn_token)
        call_args.append(VarAccessNode(fn_token.line, fn_token.column, target))
        func_call = FunctionCallNode(fn_token.line, fn_token.column, fn_name, call_args)
        if assign_result:
            return AssignNode(fn_token.line, fn_token.column, target, func_call)
        return func_call

    def _split_args_at_commas(self, expr_or_parts, token):
        """Split an ExpressionPartsNode or list of string parts at commas into args."""
        if isinstance(expr_or_parts, ExpressionPartsNode):
            parts = expr_or_parts.parts
        else:
            parts = expr_or_parts
        args = []
        current = []
        for p in parts:
            if p.value == ',':
                if current:
                    args.append(ExpressionPartsNode(token.line, token.column, current))
                current = []
            else:
                current.append(p)
        if current:
            args.append(ExpressionPartsNode(token.line, token.column, current))
        return args

    def _parse_skicka_call(self):
        return self._parse_fn_with_target(TOKEN_TO, assign_result=True)

    def _parse_hämta_call(self):
        return self._parse_fn_with_target(TOKEN_FROM, assign_result=False)

    def parse_open_file(self):
        open_token = self.consume(TOKEN_OPEN)
        self.in_structural_statement = True
        try:
            t = self.peek()
            if t.type == TOKEN_STRING:
                path_expr = StringNode(t.line, t.column, self.consume().value)
            elif t.type == TOKEN_IDENTIFIER:
                path_expr = VarAccessNode(t.line, t.column, self.consume().value)
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

        function_call_args = [path_expr, StringNode(mode_token.line, mode_token.column, mode)]
        function_call_node = FunctionCallNode(open_token.line, open_token.column, "öppna", function_call_args)
        return AssignNode(assign_token.line, assign_token.column, var_name, function_call_node, target_type=None)

    def parse_close_file(self):
        close_file_token = self.consume(TOKEN_CLOSE)
        parts = []
        while self.peek() and self.peek().type == TOKEN_IDENTIFIER:
            parts.append(self.consume().value)
        if not parts:
            raise SyntaxError(f"Förväntade en filvariabel efter 'stäng'")
        target = " ".join(parts)
        return CloseFileNode(close_file_token.line, close_file_token.column, target)

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
                return ElementAssignNode(assign_token.line, assign_token.column, " ".join(idx_parts), target, val)
            
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
        is_grej = self.peek() and self.peek().type == TOKEN_FUNC and self.peek().value == 'grej'
        is_infixgrej = (
            self.peek() and self.peek().type == TOKEN_IDENTIFIER and self.peek().value == 'infixgrej'
        )
        is_verbgrej = (
            self.peek() and self.peek().type == TOKEN_IDENTIFIER and self.peek().value == 'verbgrej'
        )
        is_skickagrej = (
            self.peek() and self.peek().type == TOKEN_IDENTIFIER and self.peek().value == 'skickagrej'
        )
        is_hämtagrej = (
            self.peek() and self.peek().type == TOKEN_IDENTIFIER and self.peek().value == 'hämtagrej'
        )
        is_rekgrej = (
            self.peek() and self.peek().type == TOKEN_IDENTIFIER and self.peek().value == 'rekgrej'
        )
        
        if is_grej or is_infixgrej or is_verbgrej or is_skickagrej or is_hämtagrej or is_rekgrej:
            is_infix = False
            if is_infixgrej:
                self.consume()  # consume 'infixgrej'
                is_infix = True
            elif is_verbgrej:
                self.consume()  # consume 'verbgrej'
            elif is_skickagrej:
                self.consume()  # consume 'skickagrej'
            elif is_hämtagrej:
                self.consume()  # consume 'hämtagrej'
            elif is_rekgrej:
                self.consume()  # consume 'rekgrej'
            if is_grej:
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

            # Parse required return type: 'returnera typ'
            return_type = self._parse_return_type()

            # Parse body (indented block)
            body = self.parse_block(params=self._extract_param_names(params))
            func_def = FunctionDefNode(assign_token.line, assign_token.column, params, body, is_infix=is_infix, type_params=type_params, return_type=return_type)
            if is_infixgrej:
                func_def.kind = 'infix'
            if is_verbgrej:
                func_def.kind = 'verb'
                self.verb_functions.add(name)
            if is_skickagrej:
                func_def.kind = 'skicka'
                self.skicka_functions.add(name)
            if is_hämtagrej:
                func_def.kind = 'hämta'
                self.hämta_functions.add(name)
            if is_rekgrej:
                func_def.kind = 'rek'
            return AssignNode(assign_token.line, assign_token.column, name, func_def, target_type=None)
        
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
                        return CopyWithPropNode(assign_token.line, assign_token.column, name, source, updates)
        
        # Standard assignment - parse expression value
        val = self.expression()
        return AssignNode(assign_token.line, assign_token.column, name, val, target_type=None)

    def parse_print(self):
        print_token = self.consume(TOKEN_PRINT)
        checkpoint = self.pos
        try:
            val = self.expression()
            if self.peek() and self.peek().type == TOKEN_TO:
                self.consume()
                if self.peek() and self.peek().type == TOKEN_IDENTIFIER:
                    target_var = self.consume().value
                    return FileWriteNode(print_token.line, print_token.column, val, target_var)
        except:
            pass
        self.pos = checkpoint
        val = self.expression()
        return PrintNode(print_token.line, print_token.column, val)

    def _collect_until(self, *stop_conditions):
        """Collect tokens until we hit one of the stop conditions.
        
        Each condition can be:
          - A string: stops when an IDENTIFIER token with that value is found
          - An int: stops when a token with that type is found
        Preserves ExpressionPart token types."""
        parts = []
        while self.peek():
            t = self.peek()
            for cond in stop_conditions:
                if isinstance(cond, str):
                    if t.type == TOKEN_IDENTIFIER and t.value == cond:
                        break
                elif isinstance(cond, int):
                    if t.type == cond:
                        break
            else:
                tok = self.consume()
                parts.append(ExpressionPart(tok.value, tok.type, tok.line, tok.column))
                continue
            break
        return ExpressionPartsNode(self.peek().line if self.peek() else None, self.peek().column if self.peek() else None, parts)

    def expression(self):
        """Parse expression - collect all tokens as ExpressionPart for resolver to handle."""
        parts = []
        t = self.peek()
        
        while t and t.type not in [TOKEN_NEWLINE, TOKEN_INDENT, TOKEN_DEDENT]:
            tok = self.consume()
            parts.append(ExpressionPart(tok.value, tok.type, tok.line, tok.column))
            t = self.peek()

        return ExpressionPartsNode(self.peek().line if self.peek() else None, self.peek().column if self.peek() else None, parts)

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
            return StringNode(t.line, t.column, "")
        
        if t.type == TOKEN_LITERAL_INT:
            self.consume()
            return IntNode(t.line, t.column, t.value)
        if t.type == TOKEN_LITERAL_FLOAT:
            self.consume()
            return FloatNode(t.line, t.column, t.value)
        if t.type == TOKEN_LITERAL_TRUE:
            self.consume()
            return BoolNode(t.line, t.column, True)
        if t.type == TOKEN_LITERAL_FALSE:
            self.consume()
            return BoolNode(t.line, t.column, False)
        if t.type == TOKEN_STRING:
            self.consume()
            return StringNode(t.line, t.column, t.value)
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
                return FunctionCallNode(t.line, t.column, name, args)
            return VarAccessNode(t.line, t.column, name)
        
        val = self.consume().value
        return StringNode(t.line, t.column, val)

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
        first_condition = IfCondition(if_token.line, if_token.column, first_cond, first_block)
        
        conditions = [first_condition]
        
        while self.peek() and self.peek().type == TOKEN_ELSE:
            self.consume()
            if self.peek() and self.peek().type == TOKEN_IF:
                self.consume()
                elif_cond = self.expression()
                elif_block = self.parse_block()
                elif_condition = IfCondition(elif_cond.line, elif_cond.column, elif_cond, elif_block)
                conditions.append(elif_condition)
            else:
                else_block = self.parse_block()
                return IfNode(if_token.line, if_token.column, conditions, else_block)
        
        return IfNode(if_token.line, if_token.column, conditions)

    def parse_while(self):
        while_token = self.consume(TOKEN_WHILE)
        return WhileNode(while_token.line, while_token.column, self.expression(), self.parse_block())

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
        
        return ForEachNode(for_token.line, for_token.column, variable, iterable, body)

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

        return TryCatchNode(try_token.line, try_token.column, try_b, err_var, catch_b, finally_b)

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

    def _parse_return_type(self):
        """Parse required 'returnera typ' on same line after function parameters.

        Returns the return type string, or raises an error if missing.
        """
        if not self.peek() or self.peek().type != TOKEN_RETURNS:
            raise Exception(
                "Funktionsdefinition saknar 'ger typ' efter parametrar"
            )
        self.consume()  # consume 'returnera'
        # Parse return type (supports generics like 'lista av heltal')
        type_parts = []
        while self.peek() and self.peek().type in (TOKEN_IDENTIFIER, TOKEN_FUNC, TOKEN_OF, TOKEN_COMMA):
            # Stop if we hit a newline
            if self.peek().type == TOKEN_NEWLINE:
                break
            type_parts.append(self.consume().value)
        if not type_parts:
            raise Exception(
                "Förväntade en typ efter 'ger' (t.ex. 'ger heltal')"
            )
        return_type = ' '.join(type_parts)
        # Clean up comma spacing
        while ' ,' in return_type:
            return_type = return_type.replace(' ,', ',')
        return return_type

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

        return TypeDefNode(type_def_token.line, type_def_token.column, name, fields, type_params=type_params,
                          parent_types=parent_types)

    def parse_grejtyp(self):
        """Parse a function type declaration: grejtyp namn med params ger returtyp"""
        from hiuh.frontend.ast import FunctionTypeNode
        token = self.consume()  # consume 'grejtyp'
        name = self.consume(TOKEN_IDENTIFIER).value

        params = []
        if self.peek() and self.peek().type == TOKEN_WITH:
            self.consume()  # consume 'med'
            params = self._parse_typed_params()

        return_type = self._parse_return_type()

        return FunctionTypeNode(token.line, token.column, name, params, return_type)

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
                field_type = ' '.join(type_parts).replace(' ,', ',').replace(', ', ', ').replace(',', ',')
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
