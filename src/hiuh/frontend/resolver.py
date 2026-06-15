# -*- coding: utf-8 -*-
"""
Resolver: Resolves imports and symbol references across modules.

Uses ModuleRegistry to store each module's AST and symbol table together.
Does NOT flatten imports - keeps ImportNode intact for backends to resolve.

Two-pass:
  1. Collect all declarations into symbol table (via ModuleRegistry)
  2. Resolve symbol references and transform AST
"""

import os
from hiuh.frontend.ast import *
from hiuh.frontend.tokenizer import TOKEN_STRING
from hiuh.frontend.module_registry import ModuleRegistry, FunctionSignature


class Resolver:
    def __init__(self, module_registry: ModuleRegistry, stdlib_path: str | None = None, target_dir: None | str = None):
        self.stdlib_path = stdlib_path
        self.target_dir = target_dir
        self.errors = []
        self.main_module = None

        # Module registry: stores AST and symbol table for each module
        self.module_registry = module_registry

        # Internal module storage for raw AST parsing
        self.modules = {}  # name -> ModuleInfo (parsed AST)

        # Local variables tracked per module (for scope resolution)
        self.local_vars = {}  # module_name -> set of variable names

        self._current_module = None
        self._registering = False  # True during registration pass, False during resolution
        
        # Context for file write detection
        self._in_print_context = False
        self._print_write_to_file = None  # Target variable name if "till var" pattern detected

        # Store original parts for expressions (keyed by node id) for stringification
        self._original_parts = {}  # node_id -> {'left': [...], 'op': '...', 'right': [...]}

        # Track current function's return type for validation
        self._current_return_type = None  # e.g. 'basnod', 'lista av basnod', or None
        self._var_types = {}  # variable_name -> type_name (simple type tracking)

        self._register_builtins()

    # --- ExpressionPart helpers ---

    @staticmethod
    def _parts_to_strings(parts):
        """Convert a list of ExpressionPart to a list of plain strings."""
        return [p.value for p in parts]

    @staticmethod
    def _index_of_part(parts, value):
        """Find index of an ExpressionPart with the given string value."""
        for i, p in enumerate(parts):
            if p.value == value:
                return i
        raise ValueError(f"'{value}' not in parts")

    @staticmethod
    def _part_in(parts, value):
        """Check if any ExpressionPart in parts has the given string value."""
        return any(p.value == value for p in parts)

    @staticmethod
    def _slice_eq(parts, i, values):
        """Check if a slice of parts matches a list of string values."""
        if i + len(values) > len(parts):
            return False
        return all(parts[i + j].value == values[j] for j in range(len(values)))

    def _parts_to_str(self, parts):
        """Join parts to a string, filtering out AST nodes."""
        return ' '.join(self._parts_to_strings([p for p in parts if isinstance(p, (str, ExpressionPart))]))
    
    def _register_builtins(self):
        """Register built-in symbols."""
        for mod in ['__main__', 'main']:
            self.module_registry.add_module(mod, "")

        # Built-in variables (including type references like heltal, sträng, etc.)
        for mod in ['__main__', 'main']:
            self.module_registry.modules[mod].add_symbol("SANT", "var")
            self.module_registry.modules[mod].add_symbol("FALSKT", "var")
            self.module_registry.modules[mod].add_symbol("mellanrum", "var")
            self.module_registry.modules[mod].add_symbol("ny", "var")
            self.module_registry.modules[mod].add_symbol("rad", "var")
            self.module_registry.modules[mod].add_symbol("lista", "var")
            self.module_registry.modules[mod].add_symbol("inmatning", "var")
            self.module_registry.modules[mod].add_symbol("heltal", "var")
            self.module_registry.modules[mod].add_symbol("text", "var")
            self.module_registry.modules[mod].add_symbol("sträng", "var")
            self.module_registry.modules[mod].add_symbol("flyttal", "var")
            self.module_registry.modules[mod].add_symbol("boolesk", "var")
            self.module_registry.modules[mod].add_symbol("argument", "var")

        # Built-in functions
        for mod in ['__main__', 'main']:
            self.module_registry.modules[mod].add_symbol("lista", "func", FunctionSignature(params=[]))
            self.module_registry.modules[mod].add_symbol("inmatning", "func", FunctionSignature(params=[]))
            # Ordlista built-in functions
            self.module_registry.modules[mod].add_symbol("ordlista", "func", FunctionSignature(params=[]))
            self.module_registry.modules[mod].add_symbol("putta", "func", FunctionSignature(params=["nyckel", "värde", "mål"]))
            self.module_registry.modules[mod].add_symbol("hämta", "func", FunctionSignature(params=["nyckel", "källa"]))
            self.module_registry.modules[mod].add_symbol("finns", "func", FunctionSignature(params=["nyckel", "källa"]))
            self.module_registry.modules[mod].add_symbol("rensa", "func", FunctionSignature(params=["nyckel", "mål"]))

    def _add_local_var(self, module_name: str, name: str):
        """Add a local variable to the module's scope."""
        if module_name not in self.local_vars:
            self.local_vars[module_name] = set()
        self.local_vars[module_name].add(name)

    def register_module_source(self, name: str, source: str):
        """Register a module by parsing source code string (for testing).

        Args:
            name: Module name (e.g., "test_verktyg")
            source: Source code as string
        """
        from hiuh.frontend.tokenizer import Tokenizer
        from hiuh.frontend.parser import Parser

        tokenizer = Tokenizer()
        tokens = tokenizer.tokenize(source)
        parser = Parser(tokens)
        ast = parser.parse()

        module = ModuleInfo(name, "<in_memory>")
        module.source = source
        module.tokens = tokens
        module.ast = ast
        self.modules[name] = module

        # Register in module registry
        self.module_registry.add_module(name, "<in_memory>", ast)

        # Register all declarations using visitor
        self._current_module = name
        self._registering = True
        for node in ast:
            self.visit(node)
        self._registering = False

    def discover_imports(self, module_name: str):
        """Discover and load imports for an already registered module."""
        module = self.modules.get(module_name)
        if not module or not module.ast:
            return

        for node in module.ast:
            if isinstance(node, ImportNode):
                # If the imported module is already registered, skip
                if node.module_name in self.modules:
                    continue

                # Try to load from disk
                if module.path and module.path != "<in_memory>" and os.path.exists(module.path):
                    if os.path.isdir(module.path):
                        base_dir = module.path
                    elif os.path.isfile(module.path):
                        base_dir = os.path.dirname(module.path)
                    else:
                        base_dir = module.path
                else:
                    # Use stdlib_path if available
                    base_dir = self.stdlib_path if self.stdlib_path else "."

                file_path = self._find_module_file(node.module_name, module_name)
                if file_path:
                    self._load_module(node.module_name, file_path, base_dir)
                    self.discover_imports(node.module_name)

    def discover_modules(self, main_file_path: str):
        main_dir = os.path.dirname(os.path.abspath(main_file_path))
        main_name = self._path_to_module_name(main_file_path, main_dir)

        for root, dirs, files in os.walk(main_dir):
            for filename in files:
                if filename.endswith('.hiuh'):
                    full_path = os.path.join(root, filename)
                    module_name = self._path_to_module_name(full_path, main_dir)
                    self._load_module(module_name, full_path, main_dir)

        self.main_module = main_name
        return main_name

    def discover_modules_from_ast(self, module_name: str, ast: list, script_dir: str):
        module = ModuleInfo(module_name, script_dir or "")
        module.ast = ast
        self.modules[module_name] = module
        self.main_module = module_name

        # Register in module registry
        self.module_registry.add_module(module_name, script_dir or "", ast)

        # Register all declarations - only collect names, don't visit expression values
        self._current_module = module_name
        self._register_declarations_only(ast)

        # If script_dir is provided, also use it as stdlib_path fallback
        if script_dir and not self.stdlib_path:
            self.stdlib_path = script_dir

    def _register_declarations_only(self, nodes: list):
        """Register declarations without visiting expression values.
        
        This avoids issues with ExpressionPartsNode needing variables to be
        defined before they can be resolved.
        """
        for node in nodes:
            if isinstance(node, AssignNode):
                if isinstance(node.value, FunctionDefNode):
                    is_infix = getattr(node.value, 'is_infix', False)
                    self.module_registry.modules[self._current_module].add_symbol(
                        node.name, "func", FunctionSignature(params=node.value.params), is_infix=is_infix
                    )
                elif isinstance(node.value, TypeDefNode):
                    self.module_registry.modules[self._current_module].add_symbol(node.name, "type")
                else:
                    self.module_registry.modules[self._current_module].add_symbol(node.name, "var")
                self._add_local_var(self._current_module, node.name)
                
            elif isinstance(node, TypeDefNode):
                self.module_registry.modules[self._current_module].add_symbol(node.name, "type")
                self._add_local_var(self._current_module, node.name)

            elif isinstance(node, FunctionTypeNode):
                self.module_registry.modules[self._current_module].add_symbol(node.name, "type")
                self._add_local_var(self._current_module, node.name)
                
            elif isinstance(node, ImportNode):
                # Record the import so we can check imported symbols later
                self.module_registry.add_import(self._current_module, node.module_name)
                # Also track in ModuleInfo for AST-based lookups
                if not hasattr(self.modules[self._current_module], 'imports'):
                    self.modules[self._current_module].imports = []
                if node.module_name not in self.modules[self._current_module].imports:
                    self.modules[self._current_module].imports.append(node.module_name)
                
            elif isinstance(node, (IfNode, WhileNode, ForEachNode, TryCatchNode)):
                # Statement blocks - recursively register declarations
                self._register_declarations_only(node.conditions if hasattr(node, 'conditions') else [])
                if hasattr(node, 'body') and node.body:
                    self._register_declarations_only(node.body)
                if hasattr(node, 'else_block') and node.else_block:
                    self._register_declarations_only(node.else_block)
                if hasattr(node, 'try_block') and node.try_block:
                    self._register_declarations_only(node.try_block)
                if hasattr(node, 'catch_block') and node.catch_block:
                    self._register_declarations_only(node.catch_block)
                if hasattr(node, 'finally_block') and node.finally_block:
                    self._register_declarations_only(node.finally_block)

    def _path_to_module_name(self, file_path: str, base_dir: str) -> str:
        rel = os.path.relpath(file_path, base_dir)
        name = rel.replace('.hiuh', '').replace(os.sep, '.')
        if name.endswith('.index'):
            name = name[:-6]
        return name

    def _load_module(self, module_name: str, file_path: str, base_dir: str):
        if module_name in self.modules:
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()

        from hiuh.frontend.tokenizer import Tokenizer
        from hiuh.frontend.parser import Parser

        tokenizer = Tokenizer()
        tokens = tokenizer.tokenize(source)
        parser = Parser(tokens)
        ast = parser.parse()

        module = ModuleInfo(module_name, file_path)
        module.source = source
        module.tokens = tokens
        module.ast = ast
        self.modules[module_name] = module

        # Register in module registry
        self.module_registry.add_module(module_name, file_path, ast)

        # Register all declarations without visiting expression values
        self._current_module = module_name
        self._register_declarations_only(ast)

    def _find_module_file(self, module_name: str, from_module: str) -> str:
        from_module_info = self.modules.get(from_module)
        search_dirs = []

        # Collect search directories
        if from_module_info and from_module_info.path:
            if os.path.isdir(from_module_info.path):
                search_dirs.append(from_module_info.path)
            elif os.path.isfile(from_module_info.path):
                search_dirs.append(os.path.dirname(from_module_info.path))

        if self.stdlib_path and os.path.isdir(self.stdlib_path):
            search_dirs.append(self.stdlib_path)

        # Also check current working directory
        search_dirs.append(os.getcwd())

        path_parts = module_name.split('.')

        # Try each search directory for a flat file (verktyg.matematik -> verktyg.matematik.hiuh)
        for search_dir in search_dirs:
            local_path = os.path.join(search_dir, *path_parts) + '.hiuh'
            if os.path.exists(local_path):
                return local_path

        # Also check for directory modules (verktyg.matematik -> verktyg/matematik.hiuh)
        for search_dir in search_dirs:
            dir_path = os.path.join(search_dir, *path_parts[:-1])
            if os.path.isdir(dir_path):
                file_path = os.path.join(dir_path, path_parts[-1] + '.hiuh')
                if os.path.exists(file_path):
                    return file_path

        return None

    def resolve_all(self):
        # Single pass: collect local vars AND transform AST (imports resolved via visitor)
        self._pass = 1
        for module_name, module in list(self.modules.items()):
            self._current_module = module_name
            module.ast = self._visit_nodes(module.ast)
            
            # Also update the module_registry's AST so the interpreter sees resolved code
            if module_name in self.module_registry.modules:
                self.module_registry.modules[module_name].ast = module.ast

        # Check for wildcard import conflicts after all imports are resolved
        self._check_wildcard_import_conflicts()

        # Save symbol tables to target directory
        self.module_registry.save()

        return len(self.errors) == 0

    # === Visitor Pattern Implementation ===

    def _visit_nodes(self, nodes: list) -> list:
        """Visit a list of nodes, returning transformed list."""
        return [self.visit(node) for node in nodes]

    def visit(self, node: ASTNode) -> ASTNode:
        """Main visitor dispatch method."""
        if node is None:
            return None

        method_name = f"visit_{type(node).__name__}"
        visitor = getattr(self, method_name, None)

        if visitor is None:
            return node  # No visitor method, return as-is

        return visitor(node)

    # === Literal nodes - return as-is ===

    # === ImportNode - mark as resolved ===

    def visit_ImportNode(self, node):
        """Visit an import node."""
        if self._registering:
            # Registration pass: just record the import
            self.module_registry.add_import(self._current_module, node.module_name)
            # Also track in ModuleInfo for AST-based lookups
            if self._current_module in self.modules:
                if not hasattr(self.modules[self._current_module], 'imports'):
                    self.modules[self._current_module].imports = []
                if node.module_name not in self.modules[self._current_module].imports:
                    self.modules[self._current_module].imports.append(node.module_name)
        else:
            # Resolution pass: load module if not already loaded
            if node.module_name not in self.modules:
                file_path = self._find_module_file(node.module_name)
                if file_path:
                    self._load_module(node.module_name, file_path, os.path.dirname(file_path))
                    # Recursively discover imports in the newly loaded module
                    self._visit_imports_in_module(node.module_name)

        node.resolved = True
        return node

    def _find_module_file(self, module_name: str, from_module: str = None) -> str | None:
        """Find the file path for a module, searching from the given module's location."""
        from_module_info = self.modules.get(from_module or self._current_module)
        search_dirs = []

        if from_module_info and from_module_info.path and from_module_info.path != "<in_memory>":
            if os.path.isdir(from_module_info.path):
                search_dirs.append(from_module_info.path)
            elif os.path.isfile(from_module_info.path):
                search_dirs.append(os.path.dirname(from_module_info.path))

        if self.stdlib_path and os.path.isdir(self.stdlib_path):
            search_dirs.append(self.stdlib_path)

        search_dirs.append(os.getcwd())

        path_parts = module_name.split('.')

        # Try flat file first (verktyg.matematik -> verktyg.matematik.hiuh)
        for search_dir in search_dirs:
            local_path = os.path.join(search_dir, *path_parts) + '.hiuh'
            if os.path.exists(local_path):
                return local_path

        # Try directory module (verktyg.matematik -> verktyg/matematik.hiuh)
        for search_dir in search_dirs:
            dir_path = os.path.join(search_dir, *path_parts[:-1])
            if os.path.isdir(dir_path):
                candidate = os.path.join(dir_path, path_parts[-1] + '.hiuh')
                if os.path.exists(candidate):
                    return candidate

        return None

    def _visit_imports_in_module(self, module_name: str):
        """Visit all ImportNodes in a module to trigger loading of dependencies."""
        module = self.modules.get(module_name)
        if not module or not module.ast:
            return

        for node in module.ast:
            if isinstance(node, ImportNode):
                self.visit(node)

    def _check_wildcard_import_conflicts(self):
        """Check for symbol conflicts between wildcard imports in each module."""
        for module_name, module in self.modules.items():
            if module_name not in self.module_registry.modules:
                continue

            importing_module = self.module_registry.modules[module_name]

            # Track which module each symbol comes from (for conflict reporting)
            imported_symbols = {}  # symbol_name -> module_name

            for node in module.ast:
                if isinstance(node, ImportNode) and node.import_all:
                    if node.module_name in self.modules and node.module_name != module_name:
                        imported_module_info = self.modules[node.module_name]
                        for stmt in imported_module_info.ast or []:
                            if isinstance(stmt, AssignNode):
                                symbol_name = stmt.name
                                # Check for conflict with existing symbol
                                if symbol_name in importing_module.symbols:
                                    # Conflict with existing symbol in module
                                    raise SyntaxError(
                                        f"Symbol '{symbol_name}' is already defined in '{module_name}' "
                                        f"(conflicts with wildcard import from '{node.module_name}')"
                                    )
                                if symbol_name in imported_symbols:
                                    # Conflict between two wildcard imports
                                    other_module = imported_symbols[symbol_name]
                                    if other_module != node.module_name:
                                        raise SyntaxError(
                                            f"Symbol '{symbol_name}' is defined in both "
                                            f"'{other_module}' and '{node.module_name}'"
                                        )
                                imported_symbols[symbol_name] = node.module_name

    # === VarAccessNode - resolve or stringify ===

    def visit_VarAccessNode(self, node):
        return self._resolve_var_access(node)

    # === Expression nodes - transform children ===

    def visit_AddNode(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if left is node.left and right is node.right:
            return node
        return AddNode(node.line, node.column, left=left, right=right)

    def visit_SubNode(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if left is node.left and right is node.right:
            return node
        return SubNode(node.line, node.column, left=left, right=right)

    def visit_MulNode(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if left is node.left and right is node.right:
            return node
        return MulNode(node.line, node.column, left=left, right=right)

    def visit_DivNode(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if left is node.left and right is node.right:
            return node
        return DivNode(node.line, node.column, left=left, right=right)

    def visit_ModNode(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if left is node.left and right is node.right:
            return node
        return ModNode(node.line, node.column, left=left, right=right)

    def visit_NotNode(self, node):
        condition = self.visit(node.condition)
        if condition is node.condition:
            return node
        return NotNode(node.line, node.column, condition=condition)

    def visit_UnaryOpNode(self, node):
        operand = self.visit(node.operand)
        if operand is node.operand:
            return node
        return UnaryOpNode(node.line, node.column, op=node.op, operand=operand)

    def visit_ExpressionPartsNode(self, node):
        """Transform ExpressionPartsNode to the correct node type based on parts."""
        parts = node.parts
        assert all(isinstance(p, ExpressionPart) for p in parts), f"All parts must be ExpressionPart, got {[type(p).__name__ for p in parts]}"

        if len(parts) == 0:
            return self.visit(StringNode(node.line, node.column, ''))

        # Check for file write pattern: "X till var" when in print context
        if self._in_print_context and self._part_in(parts, 'till'):
            till_idx = self._index_of_part(parts, 'till')
            value_parts = parts[:till_idx]
            target_var_parts = parts[till_idx + 1:]
            if value_parts and target_var_parts:
                target_var = target_var_parts[0]
                if target_var and target_var.value.isidentifier():
                    self._print_write_to_file = target_var
                    if len(value_parts) == 1:
                        return self._part_to_node(value_parts[0], node)
                    return self.visit(ExpressionPartsNode(node.line, node.column, value_parts))

        # Single part - convert to appropriate node
        if len(parts) == 1:
            return self._part_to_node(parts[0], node)

        # Check if the entire parts joined is a defined name (multi-word name)
        full_name = ' '.join(self._parts_to_strings(parts))
        if self._is_defined(full_name, self._current_module):
            # Check if it is a function with no required parameters (grej without params)
            # Check AST directly for robustness
            if self._is_function_def_with_empty_params(full_name, self._current_module):
                return FunctionCallNode(node.line, node.column, full_name, [])
            return VarAccessNode(node.line, node.column, full_name, target=None)

        # Special case: "ny rad" -> newline string (two tokens)
        if len(parts) == 2 and parts[0].value == 'ny' and parts[1].value == 'rad':
            return self.visit(StringNode(node.line, node.column, '\n'))

        # Check for negation: "inte X" -> NotNode(X)
        if parts[0].value == 'inte':
            inner_parts = parts[1:]
            if inner_parts:
                inner_node = ExpressionPartsNode(node.line, node.column, inner_parts)
                inner_result = self.visit(inner_node)
                return NotNode(node.line, node.column, inner_result)

        # Check for type casting: "X som Y" -> CastNode(value=X, target_type=Y)
        # But don't create CastNode if:
        # 1. There's a comma anywhere (it's a function call argument, not a cast)
        # 2. 'som' is a string literal (not the keyword)
        if self._part_in(parts, 'som') and not self._part_in(parts, ','):
            som_idx = self._index_of_part(parts, 'som')
            value_parts = parts[:som_idx]
            target_parts = parts[som_idx + 1:]
            if value_parts and target_parts:
                value_node = self.visit(ExpressionPartsNode(node.line, node.column, value_parts))
                target_type = ' '.join(self._parts_to_strings(target_parts))
                return CastNode(node.line, node.column, value=value_node, target_type=target_type)

        # Check for type query: "typ av X" -> TypeOfNode
        if len(parts) >= 3 and parts[0].value == 'typ' and parts[1].value == 'av':
            inner_parts = parts[2:]
            inner_node = ExpressionPartsNode(node.line, node.column, inner_parts)
            inner_result = self.visit(inner_node)
            return TypeOfNode(node.line, node.column, inner_result)

        # Check for hämta-style call: "fn thing från source" where fn has kind='hämta'
        result = self._try_hämta_call(parts, node)
        if result:
            return self.visit(result)

        # Check for property access: "X från Y" -> VarAccessNode with target
        result = self._try_property_access(parts, node)
        if result:
            return self.visit(result)

        # Check for generic function call/instantiation: "fn av T1, T2, ..."
        result = self._try_generic_call(parts, node)
        if result:
            return self.visit(result)

        # Check for function call with "med" separator: "fn med arg1, arg2, ..."
        result = self._try_function_call(parts, node)
        if result:
            return self.visit(result)

        # Check for operators (arithmetic, comparison)
        result = self._try_operator(parts, node)
        if result:
            return self.visit(result)

        # No special pattern - treat as string
        joined = ' '.join(self._parts_to_strings(parts))
        # Clean up comma spacing: "a , b" -> "a, b"
        while ' ,' in joined:
            joined = joined.replace(' ,', ',')
        return self.visit(StringNode(node.line, node.column, joined))

    def _part_to_node(self, s, token):
        """Convert a string (or ExpressionPart) to the appropriate AST node."""
        token_type = None
        if isinstance(s, ExpressionPart):
            token_type = s.token_type
            str_val = s.value
        else:
            str_val = str(s)
        
        # Check for known literals
        if token_type == TOKEN_STRING:
            return StringNode(token.line, token.column, str_val)
        elif str_val.lower() == 'sant':
            return BoolNode(token.line, token.column, True)
        elif str_val.lower() == 'falskt':
            return BoolNode(token.line, token.column, False)
        elif str_val.isdigit():
            return IntNode(token.line, token.column, str_val)
        elif self._is_float(str_val):
            value = float(str_val.replace(',', '.'))
            return FloatNode(token.line, token.column, value)
        elif self._is_defined(str_val, self._current_module):
            # Check if it's a built-in function that should be called (like 'lista')
            # Built-in functions are in __main__ module
            is_builtin = False
            
            # Check if the symbol exists in __main__ as a func
            if '__main__' in self.module_registry.modules:
                main_mod = self.module_registry.modules['__main__']
                if hasattr(main_mod, 'symbols') and str_val in main_mod.symbols:
                    symbol = main_mod.symbols[str_val]
                    if symbol.type == 'func':
                        is_builtin = True
            
            if is_builtin:
                if str_val in self._get_generic_required():
                    raise Exception(
                        f"okänd_typ: '{str_val}' kräver en typ-parameter. "
                        f"Använd '{str_val} av <typ>' (t.ex. '{str_val} av heltal')"
                    )
                return FunctionCallNode(token.line, token.column, str_val, [])
            
            # Check if it's a user-defined function with no required parameters
            # Grej functions with empty params should be called automatically
            # Check AST directly for robustness
            if self._is_function_def_with_empty_params(str_val, self._current_module):
                return FunctionCallNode(token.line, token.column, str_val, [])
            
            return VarAccessNode(token.line, token.column, str_val, target=None)
        else:
            return StringNode(token.line, token.column, str_val)

    def _is_function_def_with_empty_params(self, name, module_name):
        """Check if a name is defined as a FunctionDefNode with empty params in the AST."""
        # Check current module first
        module = self.modules.get(module_name)
        if module and module.ast:
            for node in module.ast:
                if isinstance(node, AssignNode) and node.name == name:
                    if isinstance(node.value, FunctionDefNode):
                        params = getattr(node.value, 'params', [])
                        return len(params) == 0

        # Check imported modules
        if module_name in self.modules:
            mod = self.modules[module_name]
            if hasattr(mod, 'imports'):
                for imported_mod_name in mod.imports:
                    imported_module = self.modules.get(imported_mod_name)
                    if imported_module and imported_module.ast:
                        for node in imported_module.ast:
                            if isinstance(node, AssignNode) and node.name == name:
                                if isinstance(node.value, FunctionDefNode):
                                    params = getattr(node.value, 'params', [])
                                    return len(params) == 0
        
        return False

    def _string_to_node(self, s, token):
        """Alias for _part_to_node for compatibility."""
        return self._part_to_node(s, token)

    def _try_property_access(self, parts, node):
        """Try to parse as property or element access.
        
        'element X från Y' -> ElementAccessNode(index=X, target=Y)
        'längd från Y' -> PropertyAccessNode(property_name='längd', target=Y)
        'fn från mod med args' -> FunctionCallNode(name=VarAccessNode(fn, target=mod), args)
        """
        if not self._part_in(parts, 'från'):
            return None

        från_idx = self._index_of_part(parts, 'från')
        left_parts = parts[:från_idx]
        right_parts = parts[från_idx + 1:]

        if not left_parts or not right_parts:
            return None

        # Check if there are any lower-precedence operators (arithmetic, comparison, boolean)
        # that should be evaluated after property access.
        is_module_call = self._part_in(parts, 'med') and self._index_of_part(parts, 'med') > från_idx
        operators = ['plus', 'minus', 'gånger', 'delat', 'och', 'eller']
        comparison_keywords = ['är', 'större', 'mindre', 'lika']
        
        if not is_module_call:
            if any(self._part_in(left_parts, op) or self._part_in(right_parts, op) for op in operators + comparison_keywords):
                return None
        else:
            mod_parts = parts[från_idx + 1:self._index_of_part(parts, 'med')]
            if any(self._part_in(left_parts, op) or self._part_in(mod_parts, op) for op in operators + comparison_keywords):
                return None

        # Check if left_parts contains a multi-word comparison operator - if so, this is not property access
        # but rather a comparison with property access as the right side
        # Only check for multi-word operators, not single-word 'i' or 'är'
        comparison_ops = [
            'är inte lika med',
            'större än eller lika med', 'mindre än eller lika med',
            'större än', 'mindre än', 'är inte',
            'lika med'
        ]
        for op in comparison_ops:
            op_tokens = op.split()
            for i in range(len(left_parts) - len(op_tokens) + 1):
                if self._slice_eq(left_parts, i, op_tokens):
                    # Found a comparison operator - let _try_operator handle this
                    return None

        # Also check if right_parts contains 'är' followed by registered infix operators
        # This handles cases like "element x från helhet är lika med del"
        # where 'helhet' is the target and 'är X Y' is a comparison or infix call
        # Look for 'är' anywhere in right_parts
        if 'är' in right_parts:
            är_idx = self._index_of_part(right_parts, 'är')
            remaining = right_parts[är_idx + 1:]
            
            # Check for registered infix functions starting with 'är'
            infix_ops = self._get_registered_infix_ops()
            for op in infix_ops:
                if op.startswith('är '):
                    op_suffix = op[3:]  # Get the part after 'är '
                    op_tokens = op_suffix.split()
                    if len(remaining) >= len(op_tokens) and remaining[:len(op_tokens)] == op_tokens:
                        return None
            
            # Also check for multi-word comparison operators
            multi_word_comparisons = [
                'lika med', 'mindre än', 'större än', 
                'mindre än eller lika med', 'större än eller lika med'
            ]
            for op in multi_word_comparisons:
                op_tokens = op.split()
                if len(remaining) >= len(op_tokens) and remaining[:len(op_tokens)] == op_tokens:
                    return None

        # Handle "element X från Y" -> ElementAccessNode
        if left_parts[0].value in ['element', 'index'] and len(left_parts) >= 2:
            idx_parts = left_parts[1:]
            target_parts = right_parts
            
            # Create index node - convert to appropriate node type
            if len(idx_parts) == 1 and idx_parts[0].value.isdigit():
                idx_node = IntNode(node.line, node.column, idx_parts[0].value)
            elif len(idx_parts) == 1:
                # Single variable - use VarAccessNode directly
                idx_node = VarAccessNode(node.line, node.column, idx_parts[0].value, target=None)
            else:
                # Multi-word expression - resolve precedence
                idx_node = self._resolve_precedence(idx_parts, token=node)
            
            # Create target node - prefer VarAccessNode for property access targets
            target_name = ' '.join(self._parts_to_strings(target_parts))
            # If it's a defined local variable, use VarAccessNode (not built-in FunctionCallNode)
            if self._is_defined(target_name, self._current_module):
                target_node = VarAccessNode(node.line, node.column, target_name, target=None)
            else:
                target_node = self._part_to_node(target_name, node)
            
            return ElementAccessNode(node.line, node.column, index=idx_node, target=target_node)

        # Check if this is a function call: "fn med args från target"
        # This handles callbacks like "anrop med element x från värden"
        if self._part_in(parts, 'med'):
            med_idx = self._index_of_part(parts, 'med')
            
            if med_idx > från_idx:
                # 'med' is after 'från' - module function call pattern
                fn_name = ' '.join(self._parts_to_strings(left_parts))
                # Find the module name (everything between 'från' and 'med') if present
                mod_parts = parts[från_idx + 1:med_idx]
                mod_name = ' '.join(self._parts_to_strings(mod_parts)) if mod_parts else None
                args_parts = parts[med_idx + 1:]
                
                # Create function reference
                if mod_name:
                    fn_ref = VarAccessNode(node.line, node.column, fn_name, target=mod_name)
                else:
                    fn_ref = VarAccessNode(node.line, node.column, fn_name, target=None)
                
                # Parse arguments
                args = []
                i = 0
                while i < len(args_parts):
                    part = args_parts[i]
                    if part.value == ',':
                        i += 1
                        continue
                    # Collect argument parts until comma
                    current_arg = [part]
                    i += 1
                    while i < len(args_parts) and args_parts[i].value != ',':
                        current_arg.append(args_parts[i])
                        i += 1
                    args.append(ExpressionPartsNode(node.line, node.column, current_arg))
                
                return FunctionCallNode(node.line, node.column, name=fn_ref, args=args)
            
            elif med_idx < från_idx:
                # 'med' is before 'från' - callback function call pattern
                # Example: "anrop med element x från värden"
                # Only match if no commas are present (commas indicate a
                # regular multi-arg function call like "nod med arg1, arg2")
                if self._part_in(parts, ','):
                    return None
                fn_name = parts[:med_idx][0]  # 'anrop'
                args_parts = parts[med_idx + 1:från_idx]  # ['element', 'x']
                target_name = ' '.join(self._parts_to_strings(parts[från_idx + 1:]))  # 'värden'
                
                # Create function reference (no module)
                fn_ref = VarAccessNode(node.line, node.column, fn_name, target=None)
                
                # Parse argument - handle element access pattern
                if len(args_parts) >= 2 and args_parts[0].value == 'element':
                    # "element x från target" -> ElementAccessNode
                    index_name = args_parts[1]
                    index_node = IntNode(node.line, node.column, index_name) if index_name.value.isdigit() else VarAccessNode(node.line, node.column, index_name, target=None)
                    target_node = VarAccessNode(node.line, node.column, target_name, target=None)
                    arg = ElementAccessNode(node.line, node.column, index=index_node, target=target_node)
                elif len(args_parts) == 1 and args_parts[0].value.isdigit():
                    arg = IntNode(node.line, node.column, args_parts[0].value)
                elif len(args_parts) == 1:
                    arg = VarAccessNode(node.line, node.column, args_parts[0].value, target=None)
                else:
                    arg = ExpressionPartsNode(node.line, node.column, args_parts)
                
                return FunctionCallNode(node.line, node.column, name=fn_ref, args=[arg])

        # Handle property access: "X från Y" -> PropertyAccessNode
        prop_name = ' '.join(self._parts_to_strings(left_parts))
        
        # If right_parts contains arithmetic operators, let _try_operator handle it
        # This prevents creating PropertyAccessNode with string target like "värden minus 1"
        if 'minus' in right_parts or 'plus' in right_parts or 'gånger' in right_parts or 'delat' in right_parts:
            return None
        
        # Create target node - prefer VarAccessNode for property access targets
        target_name = ' '.join(self._parts_to_strings(right_parts))
        # If it's a defined local variable, use VarAccessNode (not built-in FunctionCallNode)
        if self._is_defined(target_name, self._current_module):
            target_node = VarAccessNode(node.line, node.column, target_name, target=None)
        else:
            target_node = self._part_to_node(target_name, node)

        return PropertyAccessNode(node.line, node.column, property_name=prop_name, target=target_node)

    def _try_function_call(self, parts, node):
        """Try to parse as function call: 'fn med arg1, arg2' -> FunctionCallNode"""
        if not self._part_in(parts, 'med'):
            return None

        med_idx = self._index_of_part(parts, 'med')

        # If arithmetic/comparison operators appear before 'med', this is
        # an expression like 'n gånger fakultet med n' — let _try_operator
        # split on the operator first, then _try_function_call will be
        # called on the right sub-expression.
        pre_med = parts[:med_idx]
        for op in ['plus', 'minus', 'gånger', 'delat', 'och', 'eller']:
            if op in pre_med:
                return None

        fn_name = ' '.join(self._parts_to_strings(parts[:med_idx]))

        # Strip generic type params: 'lista av heltal med ...' -> fn_name='lista'
        if self._part_in(parts[:med_idx], 'av'):
            av_pos = self._index_of_part(parts, 'av')
            if av_pos < med_idx:
                base_fn = ' '.join(self._parts_to_strings(parts[:av_pos]))
                # Only strip if the base function is known (not modulo 'resten av x')
                if self._is_defined(base_fn, self._current_module):
                    type_parts = parts[av_pos + 1:med_idx]
                    known_types = self._get_all_known_types()
                    nesting = 0
                    for p in type_parts:
                        if p.value == ',':
                            continue
                        if p.value == 'av':
                            nesting += 1
                            continue
                        if nesting > 0:
                            continue
                        if p.value not in known_types:
                            raise Exception(
                                f"Okänd typ '{p}' i '{base_fn} av ...'"
                            )
                    fn_name = base_fn

        args_parts = parts[med_idx + 1:]

        if not self._is_defined(fn_name, self._current_module):
            return None

        # Check if this function has known parameter names (for named-arg detection)
        known_param_names = None
        symbol = self.module_registry.resolve_symbol(fn_name, self._current_module)
        if symbol and symbol.type == 'func' and symbol.signature and symbol.signature.params:
            known_param_names = set()
            for p in symbol.signature.params:
                if isinstance(p, tuple):
                    known_param_names.add(p[0])
                else:
                    known_param_names.add(p)
        elif symbol and symbol.type == 'type':
            # Type constructor: get field names
            for mod_info in self.modules.values():
                if mod_info.ast:
                    for n in mod_info.ast:
                        if hasattr(n, 'name') and n.name == fn_name and hasattr(n, 'fields'):
                            known_param_names = set()
                            for f in n.fields:
                                if isinstance(f, tuple):
                                    known_param_names.add(f[0])
                                else:
                                    known_param_names.add(f)
                            break
                    if known_param_names is not None:
                        break

        # Parse arguments: detect named vs positional.
        # Named args are exactly 2 tokens (name value). If every arg follows
        # this pattern and starts with a known name, treat all as named.
        # Otherwise everything is positional.
        args = []
        i = 0

        all_named = known_param_names is not None and len(known_param_names) > 0
        if all_named:
            temp_i = 0
            while temp_i < len(args_parts):
                if args_parts[temp_i].value == ',':
                    temp_i += 1
                    continue
                start = temp_i
                while temp_i < len(args_parts) and args_parts[temp_i].value != ',':
                    temp_i += 1
                if temp_i - start != 2 or args_parts[start].value not in known_param_names:
                    all_named = False
                    break
            if not all_named:
                known_param_names = None

        i = 0
        while i < len(args_parts):
            part = args_parts[i]

            if part.value == ',':
                i += 1
                continue

            if all_named and part.value in known_param_names and i + 1 < len(args_parts):
                value = self._part_to_node(args_parts[i + 1], node)
                args.append(NamedArgNode(node.line, node.column, part, value))
                i += 2
                continue

            # Positional argument
            arg_parts = [part]
            i += 1
            while i < len(args_parts) and args_parts[i].value != ',':
                arg_parts.append(args_parts[i])
                i += 1
            args.append(ExpressionPartsNode(node.line, node.column, arg_parts))

        return FunctionCallNode(node.line, node.column, fn_name, args)

    def _get_all_known_types(self):
        """Return set of all known type names (built-in + user-defined + type params)."""
        types = {"heltal", "sträng", "flyttal", "boolesk", "lista", "grej",
                 "text", "tecken", "tal"}
        # Add user-defined types from all modules
        for mod_info in self.modules.values():
            if mod_info.ast:
                for n in mod_info.ast:
                    if hasattr(n, 'name') and (hasattr(n, 'fields') or hasattr(n, 'params')):
                        types.add(n.name)
                    # Also add type params declared on generic types
                    if hasattr(n, 'type_params'):
                        for tp in (n.type_params or []):
                            types.add(tp)
                # Also add type params from generic function definitions
                for n in mod_info.ast:
                    if isinstance(n, AssignNode) and isinstance(n.value, FunctionDefNode):
                        for tp in (n.value.type_params or []):
                            types.add(tp)
        return types

    def _get_generic_required(self):
        """Return set of built-in functions that require type params via 'av'."""
        return {"lista", "ordlista"}

    def _function_has_kind(self, fn_name, kind):
        """Check if a function is defined with the given kind (e.g., 'hämtagrej', 'skickagrej', 'verbgrej')."""
        for mod_info in self.modules.values():
            if mod_info.ast:
                for n in mod_info.ast:
                    if isinstance(n, AssignNode) and n.name == fn_name:
                        if isinstance(n.value, FunctionDefNode):
                            if getattr(n.value, 'kind', 'grej') == kind:
                                return True
        return False

    def _try_hämta_call(self, parts, node):
        """Try to parse as hämta-style call: 'fn thing från source' -> FunctionCallNode(fn, [thing, source]).
        Only matches if fn is defined with kind='hämta'."""
        if not self._part_in(parts, 'från'):
            return None
        från_idx = self._index_of_part(parts, 'från')
        if från_idx < 2:
            return None
        fn_name = parts[0]
        if not self._is_defined(fn_name, self._current_module):
            return None
        # Only match if fn is declared as 'hämtagrej'
        if not self._function_has_kind(fn_name, 'hämta'):
            return None
        # Split: fn is parts[0], thing is parts[1:från_idx], source is parts[från_idx+1:]
        thing_parts = parts[1:från_idx]
        source_parts = parts[från_idx + 1:]
        if not thing_parts or not source_parts:
            return None
        # Build args: split thing at commas
        args = []
        current = []
        for p in thing_parts:
            if p.value == ',':
                if current:
                    args.append(ExpressionPartsNode(node.line, node.column, current))
                current = []
            else:
                current.append(p)
        if current:
            args.append(ExpressionPartsNode(node.line, node.column, current))
        # Add source as last arg
        if len(source_parts) == 1:
            if self._is_defined(source_parts[0].value, self._current_module):
                args.append(VarAccessNode(node.line, node.column, source_parts[0].value))
            else:
                args.append(StringNode(node.line, node.column, ' '.join(self._parts_to_strings(source_parts))))
        else:
            args.append(ExpressionPartsNode(node.line, node.column, source_parts))
        return FunctionCallNode(node.line, node.column, fn_name, args)

    def _try_generic_call(self, parts, node):
        """Try to parse as generic function call: 'fn av T1, T2' -> FunctionCallNode(fn, []).
        
        Type parameters are compile-time only. At runtime, we just call the base function
        with no arguments. Validates that type params refer to known types.
        """
        if not self._part_in(parts, 'av'):
            return None

        av_idx = self._index_of_part(parts, 'av')

        # If 'av' is immediately followed by a comma, it's an argument value,
        # not a generic type marker (e.g., putta "av", ...)
        if av_idx + 1 < len(parts) and parts[av_idx + 1].value == ',':
            return None

        # If there's a 'med' after 'av', let _try_function_call handle the whole
        # expression so that 'lista av heltal med 1, 2' parses correctly.
        av_idx = self._index_of_part(parts, 'av')
        if self._part_in(parts, 'med') and self._index_of_part(parts, 'med') > av_idx:
            return None

        fn_parts = parts[:av_idx]
        fn_name = ' '.join(self._parts_to_strings(fn_parts))

        if not fn_parts:
            return None

        if not self._is_defined(fn_name, self._current_module):
            return None

        # The rest after 'av' should be type params, stopping at 'med' or other keywords.
        type_parts = parts[av_idx + 1:]
        # Truncate at 'med' — anything after is function call args, not type params
        if 'med' in type_parts:
            type_parts = type_parts[:self._index_of_part(type_parts, 'med')]
        known_types = self._get_all_known_types()
        nesting = 0
        for p in type_parts:
            if p.value == ',':
                continue
            if p.value == 'av':
                nesting += 1
                continue
            if nesting > 0:
                continue
            if p.value not in known_types:
                raise Exception(
                    f"Okänd typ '{p}' i '{fn_name} av ...'"
                )

        # Check if fn_name is callable
        symbol = self.module_registry.resolve_symbol(fn_name, self._current_module)
        is_callable = symbol and symbol.type in ('func', 'type')
        if not is_callable:
            if self._is_local_var(fn_name):
                is_callable = True
            elif self._is_builtin_function(fn_name):
                is_callable = True

        if is_callable:
            return FunctionCallNode(node.line, node.column, fn_name, [])

        return None

    def _try_operator(self, parts, node):
        """Try to parse as operator expression (arithmetic or comparison).
        
        Uses precedence-based parsing: finds the lowest precedence operator first.
        """
        # Special case: if parts form "element X från Y" or "index X från Y" where X contains
        # arithmetic operators, we need to split the index into its operator sub-expression,
        # resolve it, then build the ElementAccessNode.
        if self._part_in(parts, 'från'):
            från_idx = self._index_of_part(parts, 'från')
            left_parts = parts[:från_idx]
            right_parts = parts[från_idx + 1:]
            if left_parts and right_parts and left_parts[0].value in ['element', 'index'] and len(left_parts) >= 2:
                idx_parts = left_parts[1:]
                # Check if the index expression contains any operators
                if any(op in idx_parts for op in ['plus', 'minus', 'gånger', 'delat']):
                    # Resolve the index expression with full operator precedence
                    idx_node = self._resolve_precedence(idx_parts, token=node)
                    # Resolve the target
                    if len(right_parts) == 1:
                        target_name = right_parts[0]
                        if self._is_defined(target_name, self._current_module):
                            target_node = VarAccessNode(node.line, node.column, target_name, target=None)
                        else:
                            target_node = self._part_to_node(target_name, node)
                    else:
                        target_node = self._resolve_precedence(right_parts, token=node)
                    return ElementAccessNode(node.line, node.column, index=idx_node, target=target_node)
        # Level 2: 'och' and 'eller' - checked first to respect lowest precedence
        # Only match if both operands are booleans or comparison results
        for i, part in enumerate(parts):
            if part.value in ['och', 'eller']:
                if part.value == 'eller':
                    if i > 0 and parts[i - 1].value == 'än':
                        if i + 2 < len(parts) and parts[i + 1].value == 'lika' and parts[i + 2].value == 'med':
                            continue
                left_parts = parts[:i]
                right_parts = parts[i + 1:]
                if left_parts and right_parts:
                    left_node = self._resolve_precedence(left_parts, token=node)
                    right_node = self._resolve_precedence(right_parts, token=node)
                    # Only create AndNode or OrNode if both operands are boolean-like
                    left_is_bool_like = isinstance(left_node, (BoolNode, ComparisonNodes, FunctionCallNode))
                    right_is_bool_like = isinstance(right_node, (BoolNode, ComparisonNodes, FunctionCallNode))
                    if left_is_bool_like and right_is_bool_like:
                        node_class = AndNode if part.value == 'och' else OrNode
                        return node_class(node.line, node.column, left_node, right_node)

        # Find the lowest precedence operator
        # Precedence (low to high):
        # 1. eller
        # 2. och  
        # 3. comparisons
        # 4. plus, minus
        # 5. gånger, delat med
        
        # First, find all operators and their positions
        # Then select the one with lowest precedence
        
        # Collect all possible operators with their positions and precedence
        operators = []
        
        # Multi-word comparisons (precedence 3) - must be checked FIRST
        # to avoid splitting 'större än eller lika med' at 'eller'
        multi_word_ops = [
            'är inte lika med',
            'är större än eller lika med', 'är mindre än eller lika med',
            'är större än', 'är mindre än', 'är inte', 'är lika med',
            'större än eller lika med', 'mindre än eller lika med',
            'större än', 'mindre än',
            'lika med',
        ]
        for op_str in multi_word_ops:
            op_tokens = op_str.split()
            for i in range(len(parts) - len(op_tokens) + 1):
                if self._slice_eq(parts, i, op_tokens):
                    left_parts = parts[:i]
                    right_parts = parts[i+len(op_tokens):]
                    if left_parts and right_parts:
                        return self._create_binary_expr(left_parts, op_str, right_parts, node)

        # Check for registered infix functions dynamically
        infix_ops = self._get_registered_infix_ops()
        for op_str in infix_ops:
            op_tokens = op_str.split()
            for i in range(len(parts) - len(op_tokens) + 1):
                if self._slice_eq(parts, i, op_tokens):
                    left_parts = parts[:i]
                    right_parts = parts[i+len(op_tokens):]
                    if left_parts and right_parts:
                        return self._create_binary_expr(left_parts, op_str, right_parts, node)

        # Level 4: addition/subtraction (left-associative - find last operator)
        # Find the last occurrence of + or - for left-to-right grouping
        last_plus_idx = None
        last_minus_idx = None
        for i, part in enumerate(parts):
            if part.value == 'plus':
                last_plus_idx = i
            elif part.value == 'minus':
                last_minus_idx = i
        
        # Use the rightmost + or - if found
        if last_plus_idx is not None or last_minus_idx is not None:
            if last_plus_idx is not None and (last_minus_idx is None or last_plus_idx > last_minus_idx):
                op = 'plus'
                idx = last_plus_idx
            else:
                op = 'minus'
                idx = last_minus_idx
                
            left_parts = parts[:idx]
            right_parts = parts[idx + 1:]
            if left_parts and right_parts:
                return self._create_binary_expr(left_parts, op, right_parts, node)



        # Level 5: multiplication/division/modulo
        if len(parts) >= 6 and parts[0].value == 'resten' and parts[1].value == 'av':
            # Find the position of 'delat med' or 'delat på'
            delat_idx = None
            for i in range(2, len(parts) - 1):
                if parts[i].value == 'delat' and parts[i+1].value in ('med', 'på'):
                    delat_idx = i
                    break
            if delat_idx is not None:
                left_parts = parts[2:delat_idx]
                right_parts = parts[delat_idx + 2:]
                if left_parts and right_parts:
                    left_node = self._resolve_precedence(left_parts, token=node)
                    right_node = self._resolve_precedence(right_parts, token=node)
                    return ModNode(node.line, node.column, left_node, right_node)

        for i, part in enumerate(parts):
            if part.value == 'gånger':
                left_parts = parts[:i]
                right_parts = parts[i + 1:]
                if left_parts and right_parts:
                    return self._create_binary_expr(left_parts, 'gånger', right_parts, node)
            elif part.value == 'delat' and i + 1 < len(parts) and parts[i + 1].value == 'med':
                left_parts = parts[:i]
                right_parts = parts[i + 2:]
                if left_parts and right_parts:
                    return self._create_binary_expr(left_parts, 'delat med', right_parts, node)

        return None

    def _create_binary_expr(self, left_parts, op, right_parts, node):
        """Create a binary expression node from parts, handling precedence."""
        # Get the base variable name from left_parts (first token that looks like an identifier)
        # This is for the "is defined" check for comparison operators
        left_base = left_parts[0] if left_parts else ''

        # Store original parts before any modifications for stringification
        original_left_parts = left_parts[:]
        original_op = op
        original_right_parts = right_parts[:]

        # Handle 'är' as a connector word - remove it from left_parts if it's just a connector
        # 'x är större än 2' -> left should be 'x', not 'x är'
        if left_parts and left_parts[-1].value == 'är' and len(left_parts) > 1:
            left_parts = left_parts[:-1]
            left_base = left_parts[0] if left_parts else left_base

        # Arithmetic operators - always proceed (literals are OK)
        arithmetic_ops = {
            'plus': AddNode,
            'minus': SubNode,
            'gånger': MulNode,
            'delat med': DivNode,
        }

        if op in arithmetic_ops:
            # Resolve any operators in operands with proper precedence
            left_expr = self._resolve_precedence(left_parts, token=node) if left_parts else self._part_to_node(left_base, node)
            right_expr = self._resolve_precedence(right_parts, token=node)
            return arithmetic_ops[op](node.line, node.column, left_expr, right_expr)

        comparison_ops = {
            'är inte': NotEqualNode,
            'är inte lika med': NotEqualNode,
            'lika med': EqualNode,
            'är lika med': EqualNode,
            'större än': GreaterThanNode,
            'är större än': GreaterThanNode,
            'mindre än': LessThanNode,
            'är mindre än': LessThanNode,
            'större än eller lika med': GreaterThanOrEqualNode,
            'är större än eller lika med': GreaterThanOrEqualNode,
            'mindre än eller lika med': LessThanOrEqualNode,
            'är mindre än eller lika med': LessThanOrEqualNode,
            'och': AndNode,
            'eller': OrNode,
        }

        # Boolean operators 'och' and 'eller'
        if op in ['och', 'eller']:
            left_expr = self._resolve_precedence(left_parts, token=node) if left_parts else self._part_to_node(left_base, node)
            right_expr = self._resolve_precedence(right_parts, token=node)
            return comparison_ops[op](node.line, node.column, left_expr, right_expr)

        # Infix functions create InfixCallNode (check if operator is defined as infix)
        # Check if this operator is an infix function definition
        is_infix = self._is_infix_function(op)
        if is_infix:
            left_expr = self._resolve_precedence(left_parts, token=node) if left_parts else self._part_to_node(left_base, node)
            right_expr = self._resolve_precedence(right_parts, token=node)
            return InfixCallNode(node.line, node.column, left_expr, op, right_expr)

        # For comparison operators, proceed if left base variable is defined
        # or if it looks like an identifier (not a string literal)
        # Allow comparisons with undefined variables that look like identifiers
        left_str_val = left_base.value if isinstance(left_base, ExpressionPart) else left_base
        left_is_identifier = left_str_val and left_str_val[0].isalpha() and left_str_val.replace(' ', '').isalnum()
        if not self._is_defined(left_str_val, self._current_module) and not left_is_identifier:
            left_str = ' '.join(self._parts_to_strings(left_parts)) if left_parts else left_str_val
            return StringNode(node.line, node.column, f"{left_str} {op} {' '.join(self._parts_to_strings(right_parts))}")

        # Check if left_parts contains an element access pattern: "element X från Y"
        # This handles cases like "element x från helhet är lika med del"
        # where the left side should be parsed as ElementAccessNode, not as a property access
        if 'från' in left_parts:
            från_idx = self._index_of_part(left_parts, 'från')
            left_left_parts = left_parts[:från_idx]
            left_right_parts = left_parts[från_idx + 1:]
            
            # Check if this is an element access pattern
            if len(left_left_parts) >= 2 and left_left_parts[0].value in ['element', 'index']:
                idx_parts = left_left_parts[1:]
                target_parts = left_right_parts
                
                # Create index node
                if len(idx_parts) == 1 and idx_parts[0].value.isdigit():
                    idx_node = IntNode(node.line, node.column, idx_parts[0].value)
                else:
                    idx_node = self._resolve_precedence(idx_parts, token=node)
                
                # Create target node
                target_name = ' '.join(self._parts_to_strings(target_parts))
                if self._is_defined(target_name, self._current_module):
                    target_node = VarAccessNode(node.line, node.column, target_name, target=None)
                else:
                    target_node = self._part_to_node(target_name, node)
                
                left_expr = ElementAccessNode(node.line, node.column, index=idx_node, target=target_node)
                right_expr = self._resolve_precedence(right_parts, token=node)
                result = comparison_ops[op](node.line, node.column, left_expr, right_expr)
                self._original_parts[id(result)] = {
                    'left': original_left_parts,
                    'op': original_op,
                    'right': original_right_parts
                }
                return result

        # Resolve any operators in operands with proper precedence
        # For comparison operators, always use VarAccessNode for single identifiers
        # even if they're not defined (let interpreter handle undefined vars)
        if len(left_parts) == 1 and left_parts[0].value.isidentifier():
            left_expr = VarAccessNode(node.line, node.column, left_parts[0], target=None)
        else:
            left_expr = self._resolve_precedence(left_parts, token=node) if left_parts else self._part_to_node(left_base, node)
        
        right_expr = self._resolve_precedence(right_parts, token=node)

        result = comparison_ops[op](node.line, node.column, left_expr, right_expr)
        # Store original parts in resolver for stringification
        self._original_parts[id(result)] = {
            'left': original_left_parts,
            'op': original_op,
            'right': original_right_parts
        }
        return result

    def _create_comparison_with_parts(self, left_expr, op, right_expr, token, original_parts):
        """Create a comparison node with original parts stored for stringification."""
        comparison_ops = {
            'är inte': NotEqualNode,
            'är inte lika med': NotEqualNode,
            'lika med': EqualNode,
            'är lika med': EqualNode,
            'större än': GreaterThanNode,
            'är större än': GreaterThanNode,
            'mindre än': LessThanNode,
            'är mindre än': LessThanNode,
            'större än eller lika med': GreaterThanOrEqualNode,
            'är större än eller lika med': GreaterThanOrEqualNode,
            'mindre än eller lika med': LessThanOrEqualNode,
            'är mindre än eller lika med': LessThanOrEqualNode,
            'och': AndNode,
            'eller': OrNode,
        }
        result = comparison_ops[op](token.line, token.column, left_expr, right_expr)
        self._original_parts[id(result)] = original_parts
        return result

    def _resolve_precedence(self, parts, min_prec=1, token=None):
        """Resolve expression parts with operator precedence.
        
        Precedence (low to high):
        1. eller
        2. och
        3. jämförelser (är, i, etc.)
        4. plus, minus
        5. gånger, delat med
        
        Returns an AST node.
        """
        if not parts or len(parts) == 0:
            return StringNode(token.line, token.column, '')

        if len(parts) == 1:
            return self._part_to_node(parts[0], token)

        # Try operators from lowest to highest precedence
        # When we find one, we split there and recursively resolve both sides

        # Level 1: 'eller' (lowest)
        if self._part_in(parts, 'eller'):
            idx = -1
            for i, part in enumerate(parts):
                if part.value == 'eller':
                    is_part_of_comp = False
                    if i > 0 and parts[i - 1].value == 'än':
                        if i + 2 < len(parts) and parts[i + 1].value == 'lika' and parts[i + 2].value == 'med':
                            is_part_of_comp = True
                    if not is_part_of_comp:
                        idx = i
                        break
            if idx != -1:
                left_parts = parts[:idx]
                right_parts = parts[idx + 1:]
                if left_parts and right_parts:
                    left = self._resolve_precedence(left_parts, token=token)
                    right = self._resolve_precedence(right_parts, token=token)
                    return OrNode(token.line, token.column, left, right)

        # Level 2: 'och'
        if self._part_in(parts, 'och'):
            idx = self._index_of_part(parts, 'och')
            left_parts = parts[:idx]
            right_parts = parts[idx + 1:]
            if left_parts and right_parts:
                left = self._resolve_precedence(left_parts, token=token)
                right = self._resolve_precedence(right_parts, token=token)
                return AndNode(token.line, token.column, left, right)

        # Level 3: comparisons (är, etc.)
        multi_word_ops = [
            'är inte lika med',
            'är större än eller lika med', 'är mindre än eller lika med',
            'är större än', 'är mindre än', 'är inte', 'är lika med',
            'större än eller lika med', 'mindre än eller lika med',
            'större än', 'mindre än',
            'lika med',
        ]
        for op_str in multi_word_ops:
            op_tokens = op_str.split()
            pos = self._find_op_in_parts(parts, op_tokens)
            if pos is not None:
                left_parts = parts[:pos]
                right_parts = parts[pos + len(op_tokens):]
                if left_parts and right_parts:
                    left = self._resolve_precedence(left_parts, token=token)
                    right = self._resolve_precedence(right_parts, token=token)
                    comparison_ops = {
                        'är inte': NotEqualNode,
                        'är inte lika med': NotEqualNode,
                        'lika med': EqualNode,
                        'är lika med': EqualNode,
                        'större än': GreaterThanNode,
                        'är större än': GreaterThanNode,
                        'mindre än': LessThanNode,
                        'är mindre än': LessThanNode,
                        'större än eller lika med': GreaterThanOrEqualNode,
                        'är större än eller lika med': GreaterThanOrEqualNode,
                        'mindre än eller lika med': LessThanOrEqualNode,
                        'är mindre än eller lika med': LessThanOrEqualNode,
                    }
                    return comparison_ops[op_str](token.line, token.column, left, right)
                    node_class = comparison_ops[op_str]
                    return node_class(token.line, token.column, left, right)

        # Check for infix functions dynamically
        # Get all registered infix function names
        infix_ops = self._get_registered_infix_ops()
        for op_str in infix_ops:
            op_tokens = op_str.split()
            pos = self._find_op_in_parts(parts, op_tokens)
            if pos is not None:
                left_parts = parts[:pos]
                right_parts = parts[pos + len(op_tokens):]
                if left_parts and right_parts:
                    left = self._resolve_precedence(left_parts, token=token)
                    right = self._resolve_precedence(right_parts, token=token)
                    return InfixCallNode(token.line, token.column, left, op_str, right)



        # Level 4: addition/subtraction (left-associative - find last operator)
        # Find the last occurrence of + or - for left-to-right grouping
        last_plus_idx = None
        last_minus_idx = None
        for i, part in enumerate(parts):
            if part.value == 'plus':
                last_plus_idx = i
            elif part.value == 'minus':
                last_minus_idx = i

        if last_plus_idx is not None or last_minus_idx is not None:
            if last_plus_idx is not None and (last_minus_idx is None or last_plus_idx > last_minus_idx):
                op = 'plus'
                idx = last_plus_idx
            else:
                op = 'minus'
                idx = last_minus_idx
            left_parts = parts[:idx]
            right_parts = parts[idx + 1:]
            if left_parts and right_parts:
                left = self._resolve_precedence(left_parts, token=token)
                right = self._resolve_precedence(right_parts, token=token)
                if op == 'plus':
                    return AddNode(token.line, token.column, left, right)
                else:
                    return SubNode(token.line, token.column, left, right)

        # Level 5: multiplication/division (highest)
        for op in ['gånger', 'delat']:
            if self._part_in(parts, op):
                idx = self._index_of_part(parts, op)
                # For 'delat', check if next word is 'med'
                skip = 1
                if op == 'delat' and idx + 1 < len(parts) and parts[idx + 1].value == 'med':
                    skip = 2

                left_parts = parts[:idx]
                right_parts = parts[idx + skip:]

                if left_parts and right_parts:
                    left = self._resolve_precedence(left_parts, token=token)
                    right = self._resolve_precedence(right_parts, token=token)
                    if op == 'gånger':
                        return MulNode(token.line, token.column, left, right)
                    else:
                        return DivNode(token.line, token.column, left, right)

        # Check for property access: "X från Y" -> PropertyAccessNode / ElementAccessNode
        if self._part_in(parts, 'från'):
            från_idx = self._index_of_part(parts, 'från')
            left_parts = parts[:från_idx]
            right_parts = parts[från_idx + 1:]
            if left_parts and right_parts:
                if left_parts[0].value in ['element', 'index'] and len(left_parts) >= 2:
                    idx_parts = left_parts[1:]
                    if len(idx_parts) == 1 and idx_parts[0].value.isdigit():
                        idx_node = IntNode(token.line, token.column, idx_parts[0].value)
                    elif len(idx_parts) == 1:
                        idx_node = VarAccessNode(token.line, token.column, idx_parts[0].value, target=None)
                    else:
                        idx_node = self._resolve_precedence(idx_parts, token=token)
                    
                    if len(right_parts) == 1:
                        target_name = right_parts[0]
                        if self._is_defined(target_name, self._current_module):
                            target_node = VarAccessNode(token.line, token.column, target_name, target=None)
                        else:
                            target_node = self._part_to_node(target_name, token)
                    else:
                        target_node = self._resolve_precedence(right_parts, token=token)
                    return ElementAccessNode(token.line, token.column, index=idx_node, target=target_node)

                prop_name = ' '.join(self._parts_to_strings(left_parts))
                
                # Create target node
                if len(right_parts) == 1:
                    target_name = right_parts[0]
                    if self._is_defined(target_name, self._current_module):
                        target_node = VarAccessNode(token.line, token.column, target_name, target=None)
                    else:
                        target_node = self._part_to_node(target_name, token)
                else:
                    target_node = self._resolve_precedence(right_parts, token=token)
                
                return PropertyAccessNode(token.line, token.column, property_name=prop_name, target=target_node)

        # Check for type query: "typ av X" -> TypeOfNode
        if len(parts) >= 3 and parts[0].value == 'typ' and parts[1].value == 'av':
            inner_parts = parts[2:]
            inner_node = ExpressionPartsNode(token.line, token.column, inner_parts)
            inner_result = self.visit(inner_node)
            return TypeOfNode(token.line, token.column, inner_result)

        # Check for function call: "fn med arg1, arg2" -> FunctionCallNode
        if self._part_in(parts, 'med'):
            med_idx = self._index_of_part(parts, 'med')
            pre_med = parts[:med_idx]
            # Only if no arithmetic/comparison operators appear before 'med'
            has_op_before = any(self._part_in(pre_med, op) for op in ['plus', 'minus', 'gånger', 'delat', 'och', 'eller'])
            if not has_op_before:
                fn_name = ' '.join(self._parts_to_strings(pre_med))
                # Check if the function name is a known callable
                symbol = self.module_registry.resolve_symbol(fn_name, self._current_module)
                is_callable = symbol is not None and symbol.type in ('func', 'type')
                if not is_callable:
                    is_callable = self._is_local_var(fn_name) or self._is_builtin_function(fn_name)
                if is_callable:
                    # Parse args after 'med', split by commas
                    args_parts = parts[med_idx + 1:]
                    args = []
                    current = []
                    for p in args_parts:
                        if p.value == ',':
                            if current:
                                args.append(self._resolve_precedence(current, token=token))
                            current = []
                        else:
                            current.append(p)
                    if current:
                        args.append(self._resolve_precedence(current, token=token))
                    return FunctionCallNode(token.line, token.column, fn_name, args)

        # No operator found, return as single value
        return self._part_to_node(' '.join(self._parts_to_strings(parts)), token)

    def _find_op_in_parts(self, parts, op_tokens):
        """Find operator tokens in parts list."""
        for i in range(len(parts) - len(op_tokens) + 1):
            if self._slice_eq(parts, i, op_tokens):
                return i
        return None

    def _is_float(self, s):
        """Check if string is a float."""
        try:
            float(s.value.replace(',', '.'))
            return '.' in s or ',' in s
        except:
            return False
    
    def _is_infix_function(self, name, module_name):
        """Check if a function is declared as infix."""
        if module_name and module_name in self.module_registry.modules:
            mod_info = self.module_registry.modules[module_name]
            if hasattr(mod_info, 'symbols') and name in mod_info.symbols:
                symbol = mod_info.symbols[name]
                # Check SymbolEntry.is_infix
                if hasattr(symbol, 'is_infix') and symbol.is_infix:
                    return True
                # Legacy: check if signature has is_infix
                if hasattr(symbol, 'signature') and symbol.signature:
                    if hasattr(symbol.signature, 'is_infix') and symbol.signature.is_infix:
                        return True
        
        # Also check imported modules (for wildcard imports like "använd listor")
        if module_name and module_name in self.module_registry.modules:
            mod_info = self.module_registry.modules[module_name]
            if hasattr(mod_info, 'imports'):
                for imported_module in mod_info.imports:
                    if imported_module in self.module_registry.modules:
                        imported_mod = self.module_registry.modules[imported_module]
                        if hasattr(imported_mod, 'symbols') and name in imported_mod.symbols:
                            symbol = imported_mod.symbols[name]
                            if hasattr(symbol, 'is_infix') and symbol.is_infix:
                                return True
                            if hasattr(symbol, 'signature') and symbol.signature:
                                if hasattr(symbol.signature, 'is_infix') and symbol.signature.is_infix:
                                    return True
        
        return False
    
    def _is_defined(self, name, module_name):
        """Check if a variable is defined in any scope."""
        # Check local vars tracked by resolver FIRST (local vars shadow built-ins)
        if module_name in self.local_vars and name in self.local_vars[module_name]:
            return True
        # Check built-in variables
        if name in ['SANT', 'FALSKT', 'mellanrum', 'ny', 'rad']:
            return True
        # Check built-in functions (in __main__ module)
        if '__main__' in self.module_registry.modules:
            main_mod = self.module_registry.modules['__main__']
            if hasattr(main_mod, 'symbols') and name in main_mod.symbols:
                symbol = main_mod.symbols[name]
                if symbol.type == 'func':
                    return True
        # Check module symbols
        if module_name and module_name in self.module_registry.modules:
            mod_info = self.module_registry.modules[module_name]
            if hasattr(mod_info, 'symbols') and name in mod_info.symbols:
                return True
            # Also check imported modules (for wildcard imports like "använd listor")
            if hasattr(mod_info, 'imports'):
                for imported_module in mod_info.imports:
                    if imported_module in self.module_registry.modules:
                        imported_mod = self.module_registry.modules[imported_module]
                        if hasattr(imported_mod, 'symbols') and name in imported_mod.symbols:
                            return True
        return False

    def _is_builtin_function(self, name):
        """Check if a name is a built-in function (defined in __main__ module)."""
        if '__main__' in self.module_registry.modules:
            main_mod = self.module_registry.modules['__main__']
            if hasattr(main_mod, 'symbols') and name in main_mod.symbols:
                symbol = main_mod.symbols[name]
                if symbol.type == 'func':
                    return True
        return False

    def _get_registered_infix_ops(self):
        """Get all registered infix function names as a list."""
        infix_ops = []
        for module_name in self.module_registry.modules:
            mod_info = self.module_registry.modules[module_name]
            if hasattr(mod_info, 'symbols'):
                for name, symbol in mod_info.symbols.items():
                    is_infix = False
                    if hasattr(symbol, 'is_infix') and symbol.is_infix:
                        is_infix = True
                    elif hasattr(symbol, 'signature') and hasattr(symbol.signature, 'is_infix') and symbol.signature.is_infix:
                        is_infix = True
                    if is_infix and name not in infix_ops:
                        infix_ops.append(name)
        return infix_ops

    def _is_infix_function(self, name):
        """Check if a name is defined as an infix function."""
        # Check in current module
        if self._current_module and self._current_module in self.module_registry.modules:
            mod_info = self.module_registry.modules[self._current_module]
            if hasattr(mod_info, 'symbols') and name in mod_info.symbols:
                symbol = mod_info.symbols[name]
                if hasattr(symbol, 'is_infix') and symbol.is_infix:
                    return True
            # Also check imported modules
            if hasattr(mod_info, 'imports'):
                for imported_module in mod_info.imports:
                    if imported_module in self.module_registry.modules:
                        imported_mod = self.module_registry.modules[imported_module]
                        if hasattr(imported_mod, 'symbols') and name in imported_mod.symbols:
                            symbol = imported_mod.symbols[name]
                            if hasattr(symbol, 'is_infix') and symbol.is_infix:
                                return True
        # Check in __main__ module
        if '__main__' in self.module_registry.modules:
            main_mod = self.module_registry.modules['__main__']
            if hasattr(main_mod, 'symbols') and name in main_mod.symbols:
                symbol = main_mod.symbols[name]
                if hasattr(symbol, 'is_infix') and symbol.is_infix:
                    return True
        return False


    def _visit_comparison(self, node, op_str, node_class):
        left = node.left
        right = node.right

        # Check if left is unresolved (e.g., 'a större än 2' where 'a' is unknown)
        left_unresolved = isinstance(left, VarAccessNode) and self._is_unresolved(left)

        # Check if right is a PropertyAccessNode or ElementAccessNode
        # If so, don't stringify - keep the comparison
        right_is_property = isinstance(right, (PropertyAccessNode, ElementAccessNode))

        # Stringify only if left is unresolved AND right is NOT a property/element access
        # Use original parts if available to preserve 'är' and other words
        if left_unresolved and not right_is_property:
            # Check if we have original parts stored in resolver
            node_id = id(node)
            if node_id in self._original_parts:
                parts = self._original_parts[node_id]
                left_str = ' '.join(self._parts_to_strings(parts['left'])) if parts['left'] else ''
                right_str = ' '.join(self._parts_to_strings(parts['right'])) if parts['right'] else ''
                return StringNode(node.line, node.column, f"{left_str} {parts['op']} {right_str}".strip())
            # Fallback: stringify using node values
            left_str = self._get_string_value(left)
            right_str = self._get_string_value(self.visit(right))
            return StringNode(node.line, node.column, f"{left_str} {op_str} {right_str}".strip())

        # If right is unresolved and looks like an identifier (not a number), treat it as
        # a string literal and keep the comparison for evaluation
        right_unresolved = isinstance(right, VarAccessNode) and self._is_unresolved(right)

        if right_unresolved:
            # Right is an unresolved identifier - treat as string literal
            # Keep comparison, but transform right to a StringNode
            return node_class(
                node.line, node.column,
                left=self.visit(left),
                right=StringNode(right.line, right.column, right.name),
            )

        # Normal case - transform children only if they're resolved
        new_left = self.visit(left) if not left_unresolved else left
        new_right = self.visit(right) if not right_unresolved else right

        if new_left is left and new_right is right:
            return node

        return node_class(node.line, node.column, left=new_left, right=new_right)

    def visit_EqualNode(self, node):
        return self._visit_comparison(node, 'lika med', EqualNode)

    def visit_GreaterThanNode(self, node):
        return self._visit_comparison(node, 'större än', GreaterThanNode)

    def visit_LessThanNode(self, node):
        return self._visit_comparison(node, 'mindre än', LessThanNode)

    def visit_GreaterThanOrEqualNode(self, node):
        return self._visit_comparison(node, 'större än eller lika med', GreaterThanOrEqualNode)

    def visit_LessThanOrEqualNode(self, node):
        return self._visit_comparison(node, 'mindre än eller lika med', LessThanOrEqualNode)

    def visit_AndNode(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if left is node.left and right is node.right:
            return node
        return AndNode(node.line, node.column, left=left, right=right)

    def visit_OrNode(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if left is node.left and right is node.right:
            return node
        return OrNode(node.line, node.column, left=left, right=right)

    # === Function nodes ===

    def visit_FunctionDefNode(self, node):
        # Collect params as local vars (handle both string and tuple params)
        for p in node.params:
            if isinstance(p, tuple):
                name, type_str = p
                self._validate_type_annotation(type_str, f"parametern '{name}'")
                self._var_types[name] = type_str
            else:
                name = p
            self._add_local_var(self._current_module, name)

        # Forward-declaration pass for 'rekgrej' functions: register all
        # nested names before resolving bodies so that mutually-recursive
        # functions can reference each other.  Also register the function's
        # own name so it can call itself (self-recursion).
        if getattr(node, 'kind', None) == 'rek':
            # The function's own name is not inside its body — it's on the
            # AssignNode wrapper.  Register it here so self-calls resolve.
            self._register_declarations_only(node.body)

        # Track return type for validation of 'ge' statements
        prev_return_type = self._current_return_type
        prev_var_types = dict(self._var_types)
        self._current_return_type = node.return_type

        body = self._visit_nodes(node.body)

        self._current_return_type = prev_return_type
        self._var_types = prev_var_types

        if body is node.body:
            return node
        return FunctionDefNode(node.line, node.column, 
            params=node.params,
            body=body,
            is_infix=getattr(node, 'is_infix', False),
            type_params=getattr(node, 'type_params', []),
            kind=getattr(node, 'kind', None),
            return_type=node.return_type,
        )

    def visit_FunctionCallNode(self, node):
        callee_name = node.name if isinstance(node.name, str) else getattr(node.name, 'name', None)
        
        # Check for named arguments BEFORE visiting args
        # This lets us detect named arguments before they're transformed to strings
        param_names = None
        
        if callee_name:
            # Check if this is a type constructor
            symbol = self.module_registry.resolve_symbol(callee_name, self._current_module)
            if symbol and symbol.type == 'type':
                # Find the type definition to get field names
                for mod_info in self.modules.values():
                    if mod_info.ast:
                        for n in mod_info.ast:
                            if hasattr(n, 'name') and n.name == callee_name and hasattr(n, 'fields'):
                                param_names = n.fields
                                break
            elif symbol and symbol.type == 'func' and symbol.signature:
                # It's a function - use its parameter names
                param_names = symbol.signature.params
            
            # If we found parameter names, try to transform named args
            if param_names:
                transformed = self._transform_named_args_to_positional(node.args, param_names)
                if transformed:
                    return FunctionCallNode(node.line, node.column, name=node.name, args=transformed)
        
        # Normal processing
        args = self._visit_nodes(node.args)
        if args is node.args:
            return node
        return FunctionCallNode(node.line, node.column, name=node.name, args=args)

    def _transform_named_args_to_positional(self, args, field_names):
        """Transform named arguments to positional based on field order.
        
        Handles patterns:
        1. [prop1, value1, prop2, value2] - property first, then value
        2. Multi-word: [prop_value] - where prop_value is "prop value" (prop first, then value)
        
        Reorders values to match field_names order.
        Example: args=[ålder, 37, namn David], field_names=[namn, ålder] -> [David, 37]
        """
        if not args:
            return None
        
        # Check if any arg looks like a property name (single word or multi-word)
        has_named = False
        for arg in args:
            if isinstance(arg, VarAccessNode):
                var_name = arg.name
                if var_name in field_names:
                    has_named = True
                    break
                words = var_name.split()
                if words and words[0] in field_names:
                    has_named = True
                    break
        
        if not has_named:
            return None
        
        # Parse arguments to extract prop-value pairs
        value_by_field = {}  # field_name -> value
        i = 0
        
        while i < len(args):
            arg = args[i]
            
            if isinstance(arg, VarAccessNode):
                var_name = arg.name
                words = var_name.split()
                
                # Check if this is a property (single word or first word of multi-word)
                if var_name in field_names:
                    # Single-word property - next arg is the value
                    if i + 1 < len(args):
                        value_by_field[var_name] = args[i + 1]
                        i += 2
                        continue
                elif words and words[0] in field_names:
                    # Multi-word: first word is property, rest is value
                    prop_name = words[0]
                    if len(words) > 1:
                        value_str = ' '.join(words[1:])
                        value_by_field[prop_name] = StringNode(arg.line, arg.column, value_str)
                    i += 1
                    continue
            
            # Non-VarAccessNode or not a property - skip
            i += 1
        
        # Reorder values to match field_names order
        result = []
        for field in field_names:
            if field in value_by_field:
                result.append(value_by_field[field])
        
        # Only return if we found all fields
        if len(result) == len(field_names):
            return result

        # Reorder values to match field_names order
        result = []
        for field in field_names:
            if field in value_by_field:
                result.append(value_by_field[field])
        
        # Only return if we found all fields
        if len(result) == len(field_names):
            return result
        
        return None

    def visit_ReturnNode(self, node):
        value = self.visit(node.value)
        if self._current_return_type:
            self._validate_return_value(value, self._current_return_type, node)
        if value is node.value:
            return node
        return ReturnNode(node.line, node.column, value=value)

    def _validate_return_value(self, value, declared_type, node):
        """Validate that the returned value matches the declared return type."""
        parsed = self._parse_type_annotation(declared_type)
        if parsed is None:
            return

        type_name, type_args = parsed

        # Resolve variable references to their inferred types
        if isinstance(value, VarAccessNode):
            inferred = self._infer_type(value)
            if inferred and not self._types_compatible(inferred, declared_type):
                raise Exception(
                    f"Typfel: 'ge' returnerar '{inferred}' men funktionen "
                    f"är deklarerad att returnera '{declared_type}'"
                )
            return

        if type_name == 'lista':
            self._validate_list_return(value, type_args, node)
        else:
            self._validate_struct_return(value, type_name, node)

    def _validate_struct_return(self, value, type_name, node):
        """Validate that value matches the struct type."""
        # Only check FunctionCallNode patterns
        if not isinstance(value, FunctionCallNode):
            return
        if value.name != type_name:
            # Wrong constructor called — but might be a variable, skip
            return

        # Get the struct's field definitions
        field_defs = self._get_type_field_definitions(type_name)
        if not field_defs:
            return

        # Build a map of field name -> declared type
        field_types = {}
        for f in field_defs:
            if isinstance(f, tuple):
                field_types[f[0]] = f[1]
            else:
                field_types[f] = None

        for arg in value.args:
            if isinstance(arg, NamedArgNode):
                field_name = arg.name
                arg_value = arg.value
                expected = field_types.get(field_name)
                if expected:
                    inferred = self._infer_type(arg_value)
                    if inferred and not self._types_compatible(inferred, expected):
                        raise Exception(
                            f"Typfel: fältet '{field_name}' i '{type_name}' "
                            f"har typen '{inferred}' men förväntade '{expected}'"
                        )

    def _get_type_field_definitions(self, type_name):
        """Get the raw field definitions for a type, including type annotations."""
        for mod_info in self.modules.values():
            if mod_info.ast:
                for n in mod_info.ast:
                    if hasattr(n, 'name') and n.name == type_name and hasattr(n, 'fields'):
                        return n.fields
        return None

    def _validate_list_return(self, value, element_types, node):
        """Validate that value is a list where all elements match element_types.

        Currently checks FunctionCallNode('lista', args) patterns.
        """
        if not isinstance(value, FunctionCallNode):
            # Can't statically validate non-literal list returns
            return
        if value.name != 'lista':
            return

        element_type = element_types[0] if element_types else None
        if element_type is None:
            return

        for arg in value.args:
            if isinstance(arg, NamedArgNode):
                arg = arg.value
            self._validate_element_type(arg, element_type, node)

    def _validate_element_type(self, arg, expected_type, node):
        """Validate that arg is compatible with expected_type."""
        # 'inget av basnod' → null value of basnod, always valid
        if isinstance(arg, StringNode) and arg.value.startswith('inget av '):
            # TODO: check that the type after 'inget av' matches expected_type
            return

        # VarAccessNode → check if the variable name is a known type
        # For now, we primarily check for heltal (int) mixed into basnod lists
        inferred = self._infer_type(arg)
        if inferred and not self._types_compatible(inferred, expected_type):
            raise Exception(
                f"Typfel: 'ge' returnerar '{inferred}' men funktionen "
                f"är deklarerad att returnera 'lista av {expected_type}'"
            )

    def _infer_type(self, node):
        """Infer the type of an AST node."""
        if isinstance(node, VarAccessNode):
            name = node.name
            # Check tracked variable types (from params/assignments)
            if name in self._var_types:
                return self._var_types[name]
            # Check if it's a known type name
            if name in self._get_all_known_types():
                return name
            return None
        if isinstance(node, StringNode):
            return 'sträng'
        if isinstance(node, IntNode):
            return 'heltal'
        if isinstance(node, FloatNode):
            return 'flyttal'
        if isinstance(node, BoolNode):
            return 'boolesk'
        if isinstance(node, FunctionCallNode):
            if node.name == 'lista':
                return 'lista'
        return None

    def _types_compatible(self, inferred, expected):
        """Check if inferred type is compatible with expected type."""
        if inferred == expected:
            return True
        # Unparameterized 'lista' is compatible with 'lista av X' for any X
        inferred_parsed = self._parse_type_annotation(inferred)
        expected_parsed = self._parse_type_annotation(expected)
        if inferred_parsed and expected_parsed:
            if inferred_parsed[0] == expected_parsed[0] == 'lista':
                return True  # lista is compatible with lista av X
        return self._is_subtype(inferred, expected)

    def _is_subtype(self, type_name, parent_type):
        """Check if type_name is a subtype of parent_type."""
        if type_name == parent_type:
            return True
        # Check type hierarchy via type definitions in AST
        for mod_info in self.modules.values():
            if mod_info.ast:
                for n in mod_info.ast:
                    if hasattr(n, 'name') and n.name == type_name:
                        if hasattr(n, 'parent_types') and n.parent_types:
                            for pt in n.parent_types:
                                if pt[0] == parent_type:
                                    return True
                                if self._is_subtype(pt[0], parent_type):
                                    return True
        return False

    def _parse_type_annotation(self, type_str):
        """Parse a type annotation string into (type_name, [type_args]).

        Examples:
            'heltal' -> ('heltal', [])
            'lista av basnod' -> ('lista', ['basnod'])
            'lista av heltal' -> ('lista', ['heltal'])
        """
        if not type_str:
            return None
        parts = type_str.split()
        if 'av' in parts:
            av_idx = parts.index('av')
            return (parts[0], parts[av_idx + 1:])
        return (type_str, [])

    # === Statement nodes - transform children ===

    def visit_AddAssignNode(self, node):
        if self._registering:
            return node
        value = self.visit(node.value)
        if value is node.value:
            return node
        return AddAssignNode(node.line, node.column, target=node.target, value=value)

    def visit_SubAssignNode(self, node):
        if self._registering:
            return node
        value = self.visit(node.value)
        if value is node.value:
            return node
        return SubAssignNode(node.line, node.column, target=node.target, value=value)

    def visit_MultiplyAssignNode(self, node):
        if self._registering:
            return node
        value = self.visit(node.value)
        if value is node.value:
            return node
        return MultiplyAssignNode(node.line, node.column, target=node.target, value=value)

    def visit_DivideAssignNode(self, node):
        if self._registering:
            return node
        value = self.visit(node.value)
        if value is node.value:
            return node
        return DivideAssignNode(node.line, node.column, target=node.target, value=value)

    def visit_AssignNode(self, node):
        if self._registering:
            # Registration pass: register symbol in module registry
            if isinstance(node.value, FunctionDefNode):
                is_infix = getattr(node.value, 'is_infix', False)
                self.module_registry.modules[self._current_module].add_symbol(
                    node.name, "func", FunctionSignature(params=node.value.params), is_infix=is_infix
                )
            else:
                self.module_registry.modules[self._current_module].add_symbol(node.name, "var")
        else:
            # Check for reassignment of built-in functions
            if self._is_builtin_function(node.name):
                raise Exception(f"Kan inte omdefiniera inbyggd funktion '{node.name}'")

        # Always collect the variable name as a local var
        self._add_local_var(self._current_module, node.name)

        value = self.visit(node.value)

        # Propagate type info: if we can infer the value's type, track it
        inferred = self._infer_type(value)
        if inferred:
            self._var_types[node.name] = inferred

        if value is node.value:
            return node
        return AssignNode(node.line, node.column, name=node.name, value=value, target_type=node.target_type)

    def visit_ElementAssignNode(self, node):
        """Resolve an element assignment node."""
        # Resolve the index - convert to appropriate node type
        if node.index.isdigit():
            idx = IntNode(node.line, node.column, node.index)
        else:
            idx = VarAccessNode(node.line, node.column, node.index, target=None)
        
        # Resolve the target list
        if self._is_defined(node.target, self._current_module):
            target = VarAccessNode(node.line, node.column, node.target, target=None)
        else:
            target = self._part_to_node(node.target, node)
        
        # Resolve the value
        value = self.visit(node.value)
        
        return ElementAssignNode(node.line, node.column, index=idx, target=target, value=value)

    def visit_PrintNode(self, node):
        # Set context for expression resolution
        self._in_print_context = True
        self._print_write_to_file = None
        
        value = self.visit(node.value)
        
        # Reset context
        self._in_print_context = False
        
        # Check if this should be a FileWriteNode
        if self._print_write_to_file:
            target_var = self._print_write_to_file
            self._print_write_to_file = None
            return FileWriteNode(node.line, node.column, value=value, target_var=target_var)
        
        if value is node.value:
            return node
        return PrintNode(node.line, node.column, value=value)

    def visit_IfNode(self, node):
        # Resolve each condition-block pair
        resolved_conditions = []
        for cond_block in node.conditions:
            resolved_test = self.visit(cond_block.test)
            resolved_block = self._visit_nodes(cond_block.block)
            resolved_conditions.append(IfCondition(cond_block.line, cond_block.column, resolved_test, resolved_block))
        
        # Resolve else block
        resolved_else = self._visit_nodes(node.else_block) if node.else_block else None

        return IfNode(node.line, node.column, resolved_conditions, resolved_else)

    def visit_WhileNode(self, node):
        condition = self.visit(node.condition)
        body = self._visit_nodes(node.body or [])

        if condition is node.condition and body is node.body:
            return node

        return WhileNode(node.line, node.column, condition=condition, body=body)

    def visit_ForEachNode(self, node):
        """Resolve a for-each loop.
        
        The loop variable is registered as a local var before visiting the body.
        This allows expressions in the body to reference the loop variable.
        """
        # Register the loop variable as a local var
        self._add_local_var(self._current_module, node.variable)
        
        # Resolve the iterable expression
        iterable = self.visit(node.iterable)
        
        # Visit the body with the loop variable registered
        body = self._visit_nodes(node.body or [])

        if iterable is node.iterable and body is node.body:
            return node

        return ForEachNode(node.line, node.column, variable=node.variable, iterable=iterable, body=body)

    def visit_BreakNode(self, node):
        return node

    def visit_ContinueNode(self, node):
        return node

    def visit_TryCatchNode(self, node):
        if node.error_var:
            self._add_local_var(self._current_module, node.error_var)

        try_block = self._visit_nodes(node.try_block)
        catch_block = self._visit_nodes(node.catch_block) if node.catch_block else []
        finally_block = self._visit_nodes(node.finally_block) if node.finally_block else None

        if try_block is node.try_block and catch_block is node.catch_block and finally_block is node.finally_block:
            return node

        return TryCatchNode(node.line, node.column, try_block=try_block,
            error_var=node.error_var,
            catch_block=catch_block,
            finally_block=finally_block)

    def visit_TypeDefNode(self, node):
        if self._registering:
            self.module_registry.modules[self._current_module].add_symbol(node.name, "type")
        else:
            # Check for field name collisions in inherited types
            if node.parent_types:
                seen = set()
                for parent_name, _ in node.parent_types:
                    parent_fields = self._get_type_fields(parent_name)
                    for fname in parent_fields:
                        if fname in seen:
                            raise Exception(
                                f"Fältet '{fname}' finns i flera ärvda typer för '{node.name}'"
                            )
                        seen.add(fname)
                # Check own fields don't collide with inherited
                for f in node.fields:
                    fname = f if isinstance(f, str) else f[0]
                    if fname in seen:
                        raise Exception(
                            f"Fältet '{fname}' i '{node.name}' krockar med ärvt fält"
                        )
            # Validate field type annotations
            for f in node.fields:
                if isinstance(f, tuple):
                    self._validate_type_annotation(f[1], f"fältet '{f[0]}' i '{node.name}'")
        return node

    def _validate_type_annotation(self, type_str, context):
        """Validate a type annotation string like 'lista' or 'lista av heltal'."""
        if not type_str:
            return
        parts = type_str.split()
        base_type = parts[0].rstrip(',')
        # Check if base type requires generics
        if base_type in self._get_generic_required():
            if 'av' not in parts:
                raise Exception(
                    f"okänd_typ: '{base_type}' i {context} saknar typ-parameter. "
                    f"Använd '{base_type} av <typ>' (t.ex. '{base_type} av heltal')"
                )
        # Validate type params after 'av'
        if 'av' in parts:
            av_idx = parts.index('av')
            known_types = self._get_all_known_types()
            nesting = 0
            for p in parts[av_idx + 1:]:
                p = p.rstrip(',')
                if not p:
                    continue
                if p == 'av':
                    nesting += 1
                    continue
                if nesting > 0:
                    continue
                if p not in known_types:
                    raise Exception(
                        f"Okänd typ '{p}' i {context} ({type_str})"
                    )

    def _get_type_fields(self, type_name):
        """Return field names for a type, including inherited fields."""
        # Check built-in types first
        builtins = {
            "lista": [],
            "sträng": [],
            "heltal": [],
            "flyttal": [],
            "boolesk": [],
            "grej": [],
            "text": [],
        }
        if type_name in builtins:
            return list(builtins[type_name])

        for mod_info in self.modules.values():
            if mod_info.ast:
                for n in mod_info.ast:
                    if hasattr(n, 'name') and n.name == type_name and hasattr(n, 'fields'):
                        fields = list(n.get_field_names())
                        # Recursively collect parent fields
                        if n.parent_types:
                            for pname, _ in n.parent_types:
                                pfields = self._get_type_fields(pname)
                                for pf in pfields:
                                    if pf not in fields:
                                        fields.insert(0, pf)
                        return fields
        return []

    def visit_CopyWithPropNode(self, node):
        """Handle CopyWithPropNode - register the target variable name."""
        # Register the variable name as a local var
        self._add_local_var(self._current_module, node.name)
        
        # Also register in module registry if in registration pass
        if self._registering:
            self.module_registry.modules[self._current_module].add_symbol(node.name, "var")
        
        return node

    def visit_CastNode(self, node):
        value = self.visit(node.value)
        if value is node.value:
            return node
        return CastNode(node.line, node.column, value=value, target_type=node.target_type)

    def visit_AppendNode(self, node):
        value = self.visit(node.value)
        if value is node.value:
            return node
        return AppendNode(node.line, node.column, target_list=node.target_list, value=value)

    def visit_RemoveIndexNode(self, node):
        index = self.visit(node.index)
        if index is node.index:
            return node
        return RemoveIndexNode(node.line, node.column, target_list=node.target_list, index=index)

    def visit_RemoveValueNode(self, node):
        value = self.visit(node.value)
        if value is node.value:
            return node
        return RemoveValueNode(node.line, node.column, target_list=node.target_list, value=value)

    def visit_FileWriteNode(self, node):
        value = self.visit(node.value)
        if value is node.value:
            return node
        return FileWriteNode(node.line, node.column, target_var=node.target_var, value=value)

    def visit_CloseFileNode(self, node):
        return node  # No transformation needed

    # === Helper methods ===

    def _is_unresolved(self, node: VarAccessNode) -> bool:
        """Check if a VarAccessNode cannot be resolved in the current scope."""
        # If it has a target (qualified access), check that target
        if node.target:
            target = node.target.value if isinstance(node.target, ExpressionPart) else node.target
            return not self.module_registry.resolve_symbol(target, self._current_module)

        # Check if it's a known symbol in the registry (including stdlib)
        name = node.name
        name = name.value if isinstance(name, ExpressionPart) else name
        # Check local vars first
        if self._is_local_var(name):
            return False
        # Check module registry (includes stdlib symbols)
        if self.module_registry.resolve_symbol(name, self._current_module):
            return False
        # Check stdlib (__main__) directly
        if '__main__' in self.module_registry.modules and name in self.module_registry.modules['__main__'].symbols:
            return False

        return True

    def _is_local_var(self, name: str) -> bool:
        """Check if a name is a local variable in the current module."""
        return name in self.local_vars.get(self._current_module, set())

    def _get_string_value(self, node: ASTNode) -> str:
        """Get the string value of a node for stringification."""
        if isinstance(node, VarAccessNode):
            return node.name
        elif isinstance(node, StringNode):
            return node.value
        elif isinstance(node, IntNode):
            return str(node.value)
        elif isinstance(node, FloatNode):
            return str(node.value)
        elif isinstance(node, BoolNode):
            return str(node.value).lower()
        else:
            return str(node)

    def _resolve_var_access(self, node: VarAccessNode) -> ASTNode:
        """Resolve a variable/field access - return StringNode if unknown."""
        name = node.name
        name = name.value if isinstance(name, ExpressionPart) else name
        target = node.target
        target = target.value if isinstance(target, ExpressionPart) else target
        
        if target:
            symbol = self.module_registry.resolve_symbol(target, self._current_module)
            is_local = self._is_local_var(target)
            if symbol or is_local:
                return node
            if '__main__' in self.module_registry.modules and target in self.module_registry.modules['__main__'].symbols:
                return node
            return StringNode(node.line, node.column, f"{target}.{name}")

        symbol = self.module_registry.resolve_symbol(name, self._current_module)
        if symbol:
            return node

        if self._is_local_var(name):
            return node

        if '__main__' in self.module_registry.modules and name in self.module_registry.modules['__main__'].symbols:
            return node

        # Try individual parts
        name_parts = name.split()
        for part in name_parts:
            if self._is_local_var(part):
                return node
            if self.module_registry.resolve_symbol(part, self._current_module):
                return node

        # Unknown symbol - transform to string literal
        return StringNode(node.line, node.column, node.name)

    def get_ast(self, module_name: str = None) -> list:
        """Get the AST for a module."""
        if module_name is None:
            module_name = self.main_module
        return self.modules.get(module_name, ModuleInfo("", "")).ast

    def get_imports(self, module_name: str) -> list:
        """Get the list of imported module names for a module."""
        module = self.module_registry.get_module(module_name)
        if module:
            return module.imports
        return []


class ModuleInfo:
    def __init__(self, name: str, path: str):
        self.name = name
        self.path = path
        self.source = None
        self.tokens = None
        self.ast = None
        self.imports = []