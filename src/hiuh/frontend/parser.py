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
        self.infix_functions = set()
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

        self.in_structural_statement = True
        try:
            target_expr = self.parse_greedy_expression()
        finally:
            self.in_structural_statement = False

        self.consume(TOKEN_FROM)

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
            t = self.peek()
            if t.type == TOKEN_STRING:
                path_expr = StringNode(self.consume().value, token=t)
            elif t.type == TOKEN_IDENTIFIER:
                path_expr = VarAccessNode(self.consume().value, token=t)
            else:
                raise SyntaxError("Förväntade filnamn eller sökväg")

            mode = "läsning"
            mode_token = open_token
            if self.peek() and self.peek().type == TOKEN_IDENTIFIER and self.peek().value == "för":
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

        # Check for list indexing: sätt element 0 i minlista till ...
        if self.peek() and self.peek().value in ["element", "index"] and self.peek(1).type == TOKEN_LITERAL_INT:
            self.consume()
            idx = self.consume().value
            self._consume_keyword("i")
            target_parts = []
            while self.peek() and self.peek().type == TOKEN_IDENTIFIER:
                target_parts.append(self.consume().value)
            target = " ".join(target_parts)
            self.consume(TOKEN_TO)
            val = self.parse_greedy_expression()
            return AssignNode(str(idx), val, target_type=target, token=assign_token)

        # Check for 'kopia av' pattern
        kopia_checkpoint = self.pos
        if self.peek() and self.peek().type == TOKEN_IDENTIFIER:
            name_parts = [self.consume().value]
            while self.peek() and self.peek().type == TOKEN_IDENTIFIER and self.peek().value != "till":
                name_parts.append(self.consume().value)
            name = " ".join(name_parts)
            
            if self.peek() and self.peek().type == TOKEN_TO:
                self.consume()
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
        
        self.pos = kopia_checkpoint
        
        # Standard assignment - collect name then value
        name_parts = []
        while self.peek() and self.peek().type not in [TOKEN_TO, TOKEN_NEWLINE, TOKEN_INDENT, TOKEN_DEDENT]:
            if self.peek().type == TOKEN_TO:
                break
            name_parts.append(self.consume().value)
        
        if name_parts:
            name = " ".join(name_parts)
            self.consume(TOKEN_TO)
            val = self.parse_greedy_expression()
            return AssignNode(name, val, target_type=None, token=assign_token)
        
        # Fallback
        parts = []
        while self.peek() and self.peek().type == TOKEN_IDENTIFIER and self.peek().value != "till":
            parts.append(self.consume().value)
        name = " ".join(parts)
        self.consume(TOKEN_TO)
        val = self.parse_greedy_expression()
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

        return self.expression()

    def _collect_until_keyword(self, keyword):
        """Collect tokens until we hit a specific keyword."""
        parts = []
        while self.peek() and not (self.peek().type == TOKEN_IDENTIFIER and self.peek().value == keyword):
            t = self.peek()
            if t.type in [TOKEN_IDENTIFIER, TOKEN_LITERAL_INT, TOKEN_LITERAL_FLOAT, 
                         TOKEN_LITERAL_TRUE, TOKEN_LITERAL_FALSE, TOKEN_STRING]:
                parts.append(t.value)
            elif t.type in [TOKEN_OP_IS, TOKEN_OP_ADD, TOKEN_OP_SUB, TOKEN_OP_MUL, TOKEN_OP_DIV,
                           TOKEN_GREATER, TOKEN_LESS, TOKEN_EQUAL, TOKEN_THAN, TOKEN_OR, TOKEN_AND, 
                           TOKEN_WITH, TOKEN_AS, TOKEN_OF, TOKEN_FROM]:
                parts.append(t.value)
            elif t.type == TOKEN_COMMA:
                parts.append(',')
            self.consume()
        
        if parts:
            return ExpressionPartsNode(parts, token=self.peek())
        return self.primary()

    def _collect_until(self, *keywords):
        """Collect tokens until we hit one of the keywords."""
        parts = []
        while self.peek():
            t = self.peek()
            if t.type == TOKEN_IDENTIFIER and t.value in keywords:
                break
            if t.type in [TOKEN_IDENTIFIER, TOKEN_LITERAL_INT, TOKEN_LITERAL_FLOAT, 
                         TOKEN_LITERAL_TRUE, TOKEN_LITERAL_FALSE, TOKEN_STRING]:
                parts.append(t.value)
            elif t.type in [TOKEN_OP_IS, TOKEN_OP_ADD, TOKEN_OP_SUB, TOKEN_OP_MUL, TOKEN_OP_DIV,
                           TOKEN_GREATER, TOKEN_LESS, TOKEN_EQUAL, TOKEN_THAN, TOKEN_OR, TOKEN_AND, 
                           TOKEN_WITH, TOKEN_AS, TOKEN_OF, TOKEN_FROM]:
                parts.append(t.value)
            elif t.type == TOKEN_COMMA:
                parts.append(',')
            self.consume()
        
        if parts:
            return ExpressionPartsNode(parts, token=self.peek())
        return self.primary()

    def expression(self):
        """Parse expression - just collect all tokens as parts for resolver to handle."""
        t = self.peek()
        
        # Handle 'inte' prefix
        if t and t.type == TOKEN_IDENTIFIER and t.value == "inte":
            self.consume()
            inner = self.expression()
            return NotNode(inner, token=t)
        
        # Collect all tokens until boundary
        parts = []
        t = self.peek()
        
        while t and t.type not in [TOKEN_NEWLINE, TOKEN_INDENT, TOKEN_DEDENT]:
            if t.type in [TOKEN_IDENTIFIER, TOKEN_LITERAL_INT, TOKEN_LITERAL_FLOAT, 
                         TOKEN_LITERAL_TRUE, TOKEN_LITERAL_FALSE, TOKEN_STRING]:
                parts.append(t.value)
            elif t.type in [TOKEN_OP_IS, TOKEN_OP_ADD, TOKEN_OP_SUB, TOKEN_OP_MUL, TOKEN_OP_DIV,
                           TOKEN_GREATER, TOKEN_LESS, TOKEN_EQUAL, TOKEN_THAN, TOKEN_OR, TOKEN_AND, 
                           TOKEN_WITH, TOKEN_AS, TOKEN_OF, TOKEN_FROM]:
                parts.append(t.value)
            elif t.type == TOKEN_COMMA:
                parts.append(',')
            self.consume()
            t = self.peek()
        
        if parts:
            return ExpressionPartsNode(parts, token=t)
        
        return self.primary()

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
        
        # Handle 'infix grej'
        if t.type == TOKEN_INFIX and self.peek(1) and self.peek(1).type == TOKEN_FUNC:
            infix_token = self.consume()
            self.consume()
            p = []
            if self.peek() and self.peek().type == TOKEN_WITH:
                self.consume()
                while self.peek() and self.peek().type == TOKEN_IDENTIFIER:
                    p.append(self.consume().value)
                    if self.peek() and self.peek().type == TOKEN_COMMA: self.consume()
                    else: break
            body = []
            while self.peek() and self.peek().type == TOKEN_NEWLINE:
                self.consume()
            if self.peek() and self.peek().type == TOKEN_INDENT:
                body = self.parse_block(params=p)
            return FunctionDefNode(p, body, line=infix_token.line, column=infix_token.column, is_infix=True)

        if t.type == TOKEN_IDENTIFIER and t.value == "ny" and self.peek(1) and self.peek(1).value == "rad":
            self.consume(); self.consume(); return StringNode("\n", token=t)

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

    def parse_try_catch(self):
        try_token = self.consume(TOKEN_TRY)
        try_b = self.parse_block()

        err_var = None
        catch_b = None
        if self.peek() and self.peek().value == "fånga":
            self.consume()
            err_var = self.consume(TOKEN_IDENTIFIER).value
            catch_b = self.parse_block(params=[err_var])

        finally_b = None
        if self.peek() and self.peek().value == "slutligen":
            self.consume()
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
