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

        self._register_builtins()

    def _parts_to_str(self, parts):
        """Join parts to a string, filtering out AST nodes."""
        return ' '.join(p for p in parts if isinstance(p, str))
    
    def _register_builtins(self):
        """Register built-in symbols."""
        for mod in ['__main__', 'main']:
            self.module_registry.add_module(mod, "")

        # Built-in variables
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
            self.module_registry.modules[mod].add_symbol("flyttal", "var")
            self.module_registry.modules[mod].add_symbol("argument", "var")

        # Built-in functions
        for mod in ['__main__', 'main']:
            self.module_registry.modules[mod].add_symbol("lista", "func", FunctionSignature(params=[]))
            self.module_registry.modules[mod].add_symbol("inmatning", "func", FunctionSignature(params=[]))
            self.module_registry.modules[mod].add_symbol("heltal", "func", FunctionSignature(params=[]))
            self.module_registry.modules[mod].add_symbol("text", "func", FunctionSignature(params=[]))
            self.module_registry.modules[mod].add_symbol("flyttal", "func", FunctionSignature(params=[]))

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
                
            elif isinstance(node, ImportNode):
                # Record the import so we can check imported symbols later
                self.module_registry.add_import(self._current_module, node.module_name)
                
            elif isinstance(node, (IfNode, WhileNode, TryCatchNode)):
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
                    if node.module_name in self.modules:
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
        return AddNode(left=left, right=right, token=node)

    def visit_SubNode(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if left is node.left and right is node.right:
            return node
        return SubNode(left=left, right=right, token=node)

    def visit_MulNode(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if left is node.left and right is node.right:
            return node
        return MulNode(left=left, right=right, token=node)

    def visit_DivNode(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if left is node.left and right is node.right:
            return node
        return DivNode(left=left, right=right, token=node)

    def visit_NotNode(self, node):
        condition = self.visit(node.condition)
        if condition is node.condition:
            return node
        return NotNode(condition=condition, token=node)

    def visit_UnaryOpNode(self, node):
        operand = self.visit(node.operand)
        if operand is node.operand:
            return node
        return UnaryOpNode(op=node.op, operand=operand, token=node)

    def visit_ExpressionPartsNode(self, node):
        """Transform ExpressionPartsNode to the correct node type based on parts."""
        parts = node.parts

        if len(parts) == 0:
            return self.visit(StringNode('', token=node))

        # Check for file write pattern: "X till var" when in print context
        if self._in_print_context and 'till' in parts:
            till_idx = parts.index('till')
            value_parts = parts[:till_idx]
            target_var_parts = parts[till_idx + 1:]
            if value_parts and target_var_parts:
                target_var = target_var_parts[0]
                if target_var and target_var.isidentifier():
                    self._print_write_to_file = target_var
                    if len(value_parts) == 1:
                        return self._part_to_node(value_parts[0], node)
                    return self.visit(ExpressionPartsNode(value_parts, token=node))

        # Single part - convert to appropriate node
        if len(parts) == 1:
            return self._part_to_node(parts[0], node)

        # Special case: "ny rad" -> newline string (two tokens)
        if len(parts) == 2 and parts[0] == 'ny' and parts[1] == 'rad':
            return self.visit(StringNode('\n', token=node))

        # Check for negation: "inte X" -> NotNode(X)
        if parts[0] == 'inte':
            inner_parts = parts[1:]
            if inner_parts:
                inner_node = ExpressionPartsNode(inner_parts, token=node)
                inner_result = self.visit(inner_node)
                return NotNode(inner_result, token=node)

        # Check for type casting: "X som Y" -> CastNode(value=X, target_type=Y)
        if 'som' in parts:
            som_idx = parts.index('som')
            value_parts = parts[:som_idx]
            target_parts = parts[som_idx + 1:]
            if value_parts and target_parts:
                value_node = self.visit(ExpressionPartsNode(value_parts, token=node))
                target_type = ' '.join(target_parts)
                return CastNode(value=value_node, target_type=target_type, token=node)

        # Check for property access: "X från Y" -> VarAccessNode with target
        result = self._try_property_access(parts, node)
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
        return self.visit(StringNode(' '.join(parts), token=node))

    def _part_to_node(self, s, token):
        """Convert a string to the appropriate AST node."""
        # Check for known literals
        if s.lower() == 'sant':
            return BoolNode(True, token=token)
        elif s.lower() == 'falskt':
            return BoolNode(False, token=token)
        elif s.isdigit():
            return IntNode(s, token=token)
        elif self._is_float(s):
            # Handle both '.' and ',' as decimal separator
            value = float(s.replace(',', '.'))
            return FloatNode(value, token=token)
        elif s.startswith('"') or s.startswith("'"):
            return StringNode(s[1:-1], token=token)
        # Check if it's a defined function (with no arguments)
        elif self._is_defined(s, self._current_module):
            # Check if it's a built-in function that should be called (like 'lista')
            # Built-in functions are in __main__ module
            is_builtin = False
            
            # Check if the symbol exists in __main__ as a func
            if '__main__' in self.module_registry.modules:
                main_mod = self.module_registry.modules['__main__']
                if hasattr(main_mod, 'symbols') and s in main_mod.symbols:
                    symbol = main_mod.symbols[s]
                    if symbol.type == 'func':
                        is_builtin = True
            
            if is_builtin:
                return FunctionCallNode(s, [], token=token)
            return VarAccessNode(s, target=None, token=token)
        else:
            # Undefined - treat as string
            return StringNode(s, token=token)

    def _string_to_node(self, s, token):
        """Alias for _part_to_node for compatibility."""
        return self._part_to_node(s, token)

    def _try_property_access(self, parts, node):
        """Try to parse as property or element access.
        
        'element X från Y' -> ElementAccessNode(index=X, target=Y)
        'längd från Y' -> PropertyAccessNode(property_name='längd', target=Y)
        'fn från mod med args' -> FunctionCallNode(name=VarAccessNode(fn, target=mod), args)
        """
        if 'från' not in parts:
            return None

        från_idx = parts.index('från')
        left_parts = parts[:från_idx]
        right_parts = parts[från_idx + 1:]

        if not left_parts or not right_parts:
            return None

        # Check if left_parts contains a multi-word comparison operator - if so, this is not property access
        # but rather a comparison with property access as the right side
        # Only check for multi-word operators, not single-word 'i' or 'är'
        comparison_ops = [
            'större än eller lika med', 'mindre än eller lika med',
            'större än', 'mindre än', 'är inte', 'inte i',
            'lika med'
        ]
        for op in comparison_ops:
            op_tokens = op.split()
            for i in range(len(left_parts) - len(op_tokens) + 1):
                if left_parts[i:i+len(op_tokens)] == op_tokens:
                    # Found a comparison operator - let _try_operator handle this
                    return None

        # Handle "element X från Y" -> ElementAccessNode
        if left_parts[0] in ['element', 'index'] and len(left_parts) >= 2:
            idx_parts = left_parts[1:]
            target_parts = right_parts
            
            # Create index node (could be IntNode or VarAccessNode)
            if len(idx_parts) == 1 and idx_parts[0].isdigit():
                idx_node = IntNode(idx_parts[0], token=node)
            else:
                idx_node = ExpressionPartsNode(idx_parts, token=node)
            
            # Create target node - prefer VarAccessNode for property access targets
            target_name = ' '.join(target_parts)
            # If it's a defined local variable, use VarAccessNode (not built-in FunctionCallNode)
            if self._is_defined(target_name, self._current_module):
                target_node = VarAccessNode(target_name, target=None, token=node)
            else:
                target_node = self._part_to_node(target_name, node)
            
            return ElementAccessNode(index=idx_node, target=target_node, token=node)

        # Check if this is a module function call: "fn från mod med args"
        # If there's 'med' after 'från', this is a function call, not property access
        if 'med' in parts:
            med_idx = parts.index('med')
            if med_idx > från_idx:
                # This is a module function call
                fn_name = ' '.join(left_parts)
                # Find the module name (everything between 'från' and 'med')
                mod_parts = parts[från_idx + 1:med_idx]
                mod_name = ' '.join(mod_parts) if mod_parts else None
                args_parts = parts[med_idx + 1:]
                
                if mod_name:
                    # Create VarAccessNode for the function reference
                    fn_ref = VarAccessNode(fn_name, target=mod_name, token=node)
                    
                    # Parse arguments
                    args = []
                    i = 0
                    while i < len(args_parts):
                        part = args_parts[i]
                        if part == ',':
                            i += 1
                            continue
                        # Collect argument parts until comma
                        current_arg = [part]
                        i += 1
                        while i < len(args_parts) and args_parts[i] != ',':
                            current_arg.append(args_parts[i])
                            i += 1
                        args.append(ExpressionPartsNode(current_arg, token=node))
                    
                    return FunctionCallNode(name=fn_ref, args=args, token=node)

        # Handle property access: "X från Y" -> PropertyAccessNode
        prop_name = ' '.join(left_parts)
        
        # Create target node - prefer VarAccessNode for property access targets
        target_name = ' '.join(right_parts)
        # If it's a defined local variable, use VarAccessNode (not built-in FunctionCallNode)
        if self._is_defined(target_name, self._current_module):
            target_node = VarAccessNode(target_name, target=None, token=node)
        else:
            target_node = self._part_to_node(target_name, node)

        return PropertyAccessNode(property_name=prop_name, target=target_node, token=node)

    def _try_function_call(self, parts, node):
        """Try to parse as function call: 'fn med arg1, arg2' -> FunctionCallNode"""
        if 'med' not in parts:
            return None

        med_idx = parts.index('med')
        fn_name = ' '.join(parts[:med_idx])
        args_parts = parts[med_idx + 1:]

        if not self._is_defined(fn_name, self._current_module):
            return None

        # Parse arguments (handle commas and named args)
        args = []
        i = 0
        while i < len(args_parts):
            part = args_parts[i]

            # Skip commas
            if part == ',':
                i += 1
                continue

            # Check for named argument: identifier followed by value (where identifier is not defined)
            if i + 1 < len(args_parts) and not self._is_defined(part, self._current_module):
                next_part = args_parts[i + 1]
                if next_part != ',':
                    # Named argument
                    value = self._part_to_node(next_part, node)
                    args.append(NamedArgNode(part, value, token=node))
                    i += 2
                    continue

            # Regular positional argument - collect until comma
            current_arg = [part]
            i += 1
            while i < len(args_parts) and args_parts[i] != ',':
                current_arg.append(args_parts[i])
                i += 1
            args.append(ExpressionPartsNode(current_arg, token=node))

        return FunctionCallNode(fn_name, args, token=node)

    def _try_operator(self, parts, node):
        """Try to parse as operator expression (arithmetic or comparison).
        
        Uses precedence-based parsing: finds the lowest precedence operator first.
        """
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
            'större än eller lika med', 'mindre än eller lika med',
            'större än', 'mindre än', 'är inte', 'inte i',
            'lika med', 'innehåller',
        ]
        for op_str in multi_word_ops:
            op_tokens = op_str.split()
            for i in range(len(parts) - len(op_tokens) + 1):
                if parts[i:i+len(op_tokens)] == op_tokens:
                    left_parts = parts[:i]
                    right_parts = parts[i+len(op_tokens):]
                    if left_parts and right_parts:
                        return self._create_binary_expr(left_parts, op_str, right_parts, node)

        # Single-word operators by precedence
        # Level 1: 'eller' (lowest)
        for i, part in enumerate(parts):
            if part == 'eller':
                left_parts = parts[:i]
                right_parts = parts[i + 1:]
                if left_parts and right_parts:
                    return self._create_binary_expr(left_parts, 'eller', right_parts, node)

        # Level 2: 'och'
        for i, part in enumerate(parts):
            if part == 'och':
                left_parts = parts[:i]
                right_parts = parts[i + 1:]
                if left_parts and right_parts:
                    return self._create_binary_expr(left_parts, 'och', right_parts, node)

        # Level 4: addition/subtraction (left-associative - find last operator)
        # Find the last occurrence of + or - for left-to-right grouping
        last_plus_idx = None
        last_minus_idx = None
        for i, part in enumerate(parts):
            if part == 'plus':
                last_plus_idx = i
            elif part == 'minus':
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

        # Level 5: multiplication/division
        for i, part in enumerate(parts):
            if part == 'gånger':
                left_parts = parts[:i]
                right_parts = parts[i + 1:]
                if left_parts and right_parts:
                    return self._create_binary_expr(left_parts, 'gånger', right_parts, node)
            elif part == 'delat' and i + 1 < len(parts) and parts[i + 1] == 'med':
                left_parts = parts[:i]
                right_parts = parts[i + 2:]
                if left_parts and right_parts:
                    return self._create_binary_expr(left_parts, 'delat med', right_parts, node)

        return None

    def _create_binary_expr(self, left_parts, op, right_parts, node):
        """Create a binary expression node from parts, handling precedence."""
        # Define operator precedence (lower number = lower precedence)
        precedence = {
            'eller': 1, 'och': 1,
            'är': 2, 'är inte': 2, 'i': 2, 'inte i': 2,
            'större än': 2, 'mindre än': 2, 'större än eller lika med': 2, 'mindre än eller lika med': 2,
            'plus': 3, 'minus': 3,
            'gånger': 4, 'delat med': 4,
        }

        # Get precedence of current operator (default to 0 for unknown)
        current_prec = precedence.get(op, 0)

        # Get the base variable name from left_parts (first token that looks like an identifier)
        # This is for the "is defined" check for comparison operators
        left_base = left_parts[0] if left_parts else ''

        # Handle 'är' as a connector word - remove it from left_parts if it's just a connector
        # 'x är större än 2' -> left should be 'x', not 'x är'
        if left_parts and left_parts[-1] == 'är' and len(left_parts) > 1:
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
            return arithmetic_ops[op](left_expr, right_expr, token=node)

        # Boolean operators 'och' and 'eller' use ComparisonNode
        if op in ['och', 'eller']:
            left_expr = self._resolve_precedence(left_parts, token=node) if left_parts else self._part_to_node(left_base, node)
            right_expr = self._resolve_precedence(right_parts, token=node)
            return ComparisonNode(left_expr, op, right_expr, token=node)

        # Infix functions create InfixCallNode (check if operator is defined as infix)
        # Check if this operator is an infix function definition
        is_infix = self._is_infix_function(op)
        if is_infix:
            left_expr = self._resolve_precedence(left_parts, token=node) if left_parts else self._part_to_node(left_base, node)
            right_expr = self._resolve_precedence(right_parts, token=node)
            return InfixCallNode(left_expr, op, right_expr, token=node)

        # For comparison operators, proceed if left base variable is defined
        # or if it looks like an identifier (not a string literal)
        # Allow comparisons with undefined variables that look like identifiers
        left_is_identifier = left_base and left_base[0].isalpha() and left_base.replace(' ', '').isalnum()
        if not self._is_defined(left_base, self._current_module) and not left_is_identifier:
            left_str = ' '.join(left_parts) if left_parts else left_base
            return StringNode(f"{left_str} {op} {' '.join(right_parts)}", token=node)

        # Resolve any operators in operands with proper precedence
        # For comparison operators, always use VarAccessNode for single identifiers
        # even if they're not defined (let interpreter handle undefined vars)
        if len(left_parts) == 1 and left_parts[0].isidentifier():
            left_expr = VarAccessNode(left_parts[0], target=None, token=node)
        else:
            left_expr = self._resolve_precedence(left_parts, token=node) if left_parts else self._part_to_node(left_base, node)
        
        right_expr = self._resolve_precedence(right_parts, token=node)

        return ComparisonNode(left_expr, op, right_expr, token=node)

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
            return StringNode('', token=token)

        if len(parts) == 1:
            return self._part_to_node(parts[0], token)

        # Try operators from lowest to highest precedence
        # When we find one, we split there and recursively resolve both sides

        # Level 1: 'eller' (lowest)
        for op in ['eller']:
            if op in parts:
                idx = parts.index(op)
                left_parts = parts[:idx]
                right_parts = parts[idx + 1:]
                if left_parts and right_parts:
                    left = self._resolve_precedence(left_parts, token=token)
                    right = self._resolve_precedence(right_parts, token=token)
                    return ComparisonNode(left, op, right, token=token)

        # Level 2: 'och'
        for op in ['och']:
            if op in parts:
                idx = parts.index(op)
                left_parts = parts[:idx]
                right_parts = parts[idx + 1:]
                if left_parts and right_parts:
                    left = self._resolve_precedence(left_parts, token=token)
                    right = self._resolve_precedence(right_parts, token=token)
                    return ComparisonNode(left, op, right, token=token)

        # Check for property access: "X från Y" -> PropertyAccessNode
        # This should be checked before comparison operators
        if 'från' in parts:
            från_idx = parts.index('från')
            left_parts = parts[:från_idx]
            right_parts = parts[från_idx + 1:]
            if left_parts and right_parts:
                # Check if left_parts contains a comparison operator - if so, skip
                comparison_ops = [
                    'större än eller lika med', 'mindre än eller lika med',
                    'större än', 'mindre än', 'är inte', 'inte i',
                    'lika med', 'är', 'i'
                ]
                has_comparison = False
                for op in comparison_ops:
                    op_tokens = op.split()
                    for i in range(len(left_parts) - len(op_tokens) + 1):
                        if left_parts[i:i+len(op_tokens)] == op_tokens:
                            has_comparison = True
                            break
                    if has_comparison:
                        break
                
                if not has_comparison:
                    prop_name = ' '.join(left_parts)
                    target_name = ' '.join(right_parts)
                    
                    # Create target node
                    if self._is_defined(target_name, self._current_module):
                        target_node = VarAccessNode(target_name, target=None, token=token)
                    else:
                        target_node = self._part_to_node(target_name, token)
                    
                    return PropertyAccessNode(property_name=prop_name, target=target_node, token=token)

        # Level 3: comparisons (är, i, etc.)
        multi_word_ops = [
            'större än eller lika med', 'mindre än eller lika med',
            'större än', 'mindre än', 'är inte', 'inte i',
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
                    return ComparisonNode(left, op_str, right, token=token)

        for op in ['är', 'i']:
            if op in parts:
                idx = parts.index(op)
                left_parts = parts[:idx]
                right_parts = parts[idx + 1:]
                if left_parts and right_parts:
                    left = self._resolve_precedence(left_parts, token=token)
                    right = self._resolve_precedence(right_parts, token=token)
                    return ComparisonNode(left, op, right, token=token)

        # Level 4: addition/subtraction (left-associative - find last operator)
        # Find the last occurrence of + or - for left-to-right grouping
        last_plus_idx = None
        last_minus_idx = None
        for i, part in enumerate(parts):
            if part == 'plus':
                last_plus_idx = i
            elif part == 'minus':
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
                    return AddNode(left, right, token=token)
                else:
                    return SubNode(left, right, token=token)

        # Level 5: multiplication/division (highest)
        for op in ['gånger', 'delat']:
            if op in parts:
                idx = parts.index(op)
                # For 'delat', check if next word is 'med'
                skip = 1
                if op == 'delat' and idx + 1 < len(parts) and parts[idx + 1] == 'med':
                    skip = 2

                left_parts = parts[:idx]
                right_parts = parts[idx + skip:]

                if left_parts and right_parts:
                    left = self._resolve_precedence(left_parts, token=token)
                    right = self._resolve_precedence(right_parts, token=token)
                    if op == 'gånger':
                        return MulNode(left, right, token=token)
                    else:
                        return DivNode(left, right, token=token)

        # No operator found, return as single value
        return self._part_to_node(' '.join(parts), token)

    def _find_op_in_parts(self, parts, op_tokens):
        """Find operator tokens in parts list."""
        for i in range(len(parts) - len(op_tokens) + 1):
            if parts[i:i+len(op_tokens)] == op_tokens:
                return i
        return None

    def _is_float(self, s):
        """Check if string is a float."""
        try:
            float(s.replace(',', '.'))
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
        # Check built-in variables
        if name in ['SANT', 'FALSKT', 'mellanrum', 'ny', 'rad']:
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
        # Check local vars tracked by resolver
        if module_name in self.local_vars and name in self.local_vars[module_name]:
            return True
        return False

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


    def visit_ComparisonNode(self, node):
        op = node.op.strip() if hasattr(node, 'op') and node.op else ''

        # Membership check (i) should NOT be stringified
        if op == 'i':
            left = self.visit(node.left)
            right = self.visit(node.right)
            if left is node.left and right is node.right:
                return node
            return ComparisonNode(left=left, right=right, op=op, token=node)

        left = node.left
        right = node.right

        # Check if left is unresolved (e.g., 'a större än 2' where 'a' is unknown)
        left_unresolved = isinstance(left, VarAccessNode) and self._is_unresolved(left)

        # Check if right is a PropertyAccessNode or ElementAccessNode
        # If so, don't stringify - keep the comparison
        right_is_property = isinstance(right, (PropertyAccessNode, ElementAccessNode))

        # Stringify only if left is unresolved AND right is NOT a property/element access
        if left_unresolved and not right_is_property:
            left_str = self._get_string_value(left)
            right_str = self._get_string_value(self.visit(right))
            return StringNode(f"{left_str} {op} {right_str}".strip(), token=node)

        # If right is unresolved and looks like an identifier (not a number), treat it as
        # a string literal and keep the comparison for evaluation
        right_unresolved = isinstance(right, VarAccessNode) and self._is_unresolved(right)

        if right_unresolved:
            # Right is an unresolved identifier - treat as string literal
            # Keep comparison, but transform right to a StringNode
            return ComparisonNode(
                left=self.visit(left),
                right=StringNode(right.name, token=right),
                op=op,
                token=node
            )

        # Normal case - transform children only if they're resolved
        new_left = self.visit(left) if not left_unresolved else left
        new_right = self.visit(right) if not right_unresolved else right

        if new_left is left and new_right is right:
            return node

        return ComparisonNode(left=new_left, right=new_right, op=op, token=node)

    # === Function nodes ===

    def visit_FunctionDefNode(self, node):
        # Collect params as local vars
        for p in node.params:
            self._add_local_var(self._current_module, p)

        body = self._visit_nodes(node.body)
        if body is node.body:
            return node
        return FunctionDefNode(params=node.params, body=body, line=node.line, column=node.column, is_infix=getattr(node, 'is_infix', False))

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
                    return FunctionCallNode(name=node.name, args=transformed, token=node)
        
        # Normal processing
        args = self._visit_nodes(node.args)
        if args is node.args:
            return node
        return FunctionCallNode(name=node.name, args=args, token=node)

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
                        value_by_field[prop_name] = StringNode(value_str, token=arg)
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
        if value is node.value:
            return node
        return ReturnNode(value=value, token=node)

    # === Statement nodes - transform children ===

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

        # Always collect the variable name as a local var
        self._add_local_var(self._current_module, node.name)

        value = self.visit(node.value)
        if value is node.value:
            return node
        return AssignNode(name=node.name, value=value, target_type=node.target_type, token=node)

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
            return FileWriteNode(value=value, target_var=target_var, token=node)
        
        if value is node.value:
            return node
        return PrintNode(value=value, token=node)

    def visit_IfNode(self, node):
        # Resolve each condition-block pair
        resolved_conditions = []
        for cond_block in node.conditions:
            resolved_test = self.visit(cond_block.test)
            resolved_block = self._visit_nodes(cond_block.block)
            resolved_conditions.append(IfCondition(resolved_test, resolved_block, line=cond_block.line, column=cond_block.column))
        
        # Resolve else block
        resolved_else = self._visit_nodes(node.else_block) if node.else_block else None

        return IfNode(resolved_conditions, resolved_else, line=node.line, column=node.column)

    def visit_WhileNode(self, node):
        condition = self.visit(node.condition)
        body = self._visit_nodes(node.body or [])

        if condition is node.condition and body is node.body:
            return node

        return WhileNode(condition=condition, body=body, line=node.line, column=node.column)

    def visit_TryCatchNode(self, node):
        if node.error_var:
            self._add_local_var(self._current_module, node.error_var)

        try_block = self._visit_nodes(node.try_block)
        catch_block = self._visit_nodes(node.catch_block) if node.catch_block else []
        finally_block = self._visit_nodes(node.finally_block) if node.finally_block else None

        if try_block is node.try_block and catch_block is node.catch_block and finally_block is node.finally_block:
            return node

        return TryCatchNode(
            try_block=try_block,
            error_var=node.error_var,
            catch_block=catch_block,
            finally_block=finally_block,
            token=node
        )

    def visit_TypeDefNode(self, node):
        if self._registering:
            self.module_registry.modules[self._current_module].add_symbol(node.name, "type")
        return node  # No transformation needed

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
        return CastNode(value=value, target_type=node.target_type, token=node)

    def visit_AppendNode(self, node):
        value = self.visit(node.value)
        if value is node.value:
            return node
        return AppendNode(target_list=node.target_list, value=value, token=node)

    def visit_RemoveIndexNode(self, node):
        index = self.visit(node.index)
        if index is node.index:
            return node
        return RemoveIndexNode(target_list=node.target_list, index=index, token=node)

    def visit_RemoveValueNode(self, node):
        value = self.visit(node.value)
        if value is node.value:
            return node
        return RemoveValueNode(target_list=node.target_list, value=value, token=node)

    def visit_FileWriteNode(self, node):
        value = self.visit(node.value)
        if value is node.value:
            return node
        return FileWriteNode(target_var=node.target_var, value=value, token=node)

    def visit_CloseFileNode(self, node):
        return node  # No transformation needed

    # === Helper methods ===

    def _is_unresolved(self, node: VarAccessNode) -> bool:
        """Check if a VarAccessNode cannot be resolved in the current scope."""
        # If it has a target (qualified access), check that target
        if node.target:
            return not self.module_registry.resolve_symbol(node.target, self._current_module)

        # Check if it's a known symbol in the registry (including stdlib)
        name = node.name
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
        if node.target:
            symbol = self.module_registry.resolve_symbol(node.target, self._current_module)
            is_local = self._is_local_var(node.target)
            if symbol or is_local:
                return node
            # Check __main__ for built-in variables like 'argument'
            if '__main__' in self.module_registry.modules and node.target in self.module_registry.modules['__main__'].symbols:
                return node
            return StringNode(f"{node.target}.{node.name}", token=node)

        symbol = self.module_registry.resolve_symbol(node.name, self._current_module)
        if symbol:
            return node

        if self._is_local_var(node.name):
            return node

        # Check stdlib (__main__) for built-in constants like 'mellanrum'
        if '__main__' in self.module_registry.modules and node.name in self.module_registry.modules['__main__'].symbols:
            return node

        # Try individual parts
        name_parts = node.name.split()
        for part in name_parts:
            if self._is_local_var(part):
                return node
            if self.module_registry.resolve_symbol(part, self._current_module):
                return node

        # Unknown symbol - transform to string literal
        return StringNode(node.name, token=node)

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