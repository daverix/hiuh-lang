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

        self._register_builtins()

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

        # Register all declarations using visitor
        self._current_module = module_name
        self._registering = True
        for node in ast:
            self.visit(node)
        self._registering = False

        # If script_dir is provided, also use it as stdlib_path fallback
        if script_dir and not self.stdlib_path:
            self.stdlib_path = script_dir

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

        # Register all declarations using visitor
        self._current_module = module_name
        self._registering = True
        for node in ast:
            self.visit(node)
        self._registering = False

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
            return node  # Can't transform empty parts
        
        # Check for property access FIRST: "X från Y" -> property X of Y
        # This must be checked before comparison handling because 'från' is not a comparison operator
        # BUT don't match if left side is a built-in function name
        if 'från' in parts:
            from_idx = parts.index('från')
            left_parts = parts[:from_idx]
            right_parts = parts[from_idx+1:]
            
            # Only treat as property access if left is a simple property name
            # and right is a defined variable (not a function call result)
            if len(left_parts) == 1 and len(right_parts) >= 1:
                prop_name = left_parts[0]
                target_str = ' '.join(right_parts)
                # Don't treat as property access if left is a built-in function
                if prop_name in ['längd', 'element', 'index']:
                    pass  # Don't treat as property access
                # Check if target is a defined variable
                elif self._is_defined(target_str, self._current_module) or \
                   (len(right_parts) == 1 and self._is_defined(right_parts[0], self._current_module)):
                    return VarAccessNode(prop_name, target=target_str, token=node)
        
        if len(parts) == 1:
            # Single part - it's a variable name or literal
            part = parts[0]
            # Check if it's a known literal
            if part.lower() == 'sant':
                return BoolNode(True, token=node)
            elif part.lower() == 'falskt':
                return BoolNode(False, token=node)
            elif part.isdigit():
                return IntNode(part, token=node)
            elif self._is_float(part):
                return FloatNode(part, token=node)
            elif part.startswith('"') or part.startswith("'"):
                return StringNode(part[1:-1], token=node)
            else:
                return VarAccessNode(part, target=None, token=node)
        
        # Check for infix function call FIRST
        # This ensures "är del av" is recognized as an infix function, not a comparison
        # Handle both "a innehåller b" and "a är del av b" (är is syntactic sugar)
        if len(parts) >= 3:
            # Try all possible splits to find an infix function
            for i in range(1, len(parts)):
                left_parts = parts[:i]
                right_parts = parts[i:]
                
                # Try all possible prefixes of right_parts as the function name
                for j in range(1, len(right_parts)):
                    fn_name = ' '.join(right_parts[:j])
                    if self._is_infix_function(fn_name, self._current_module):
                        left = self._part_to_node(' '.join(left_parts), node)
                        right = self._part_to_node(' '.join(right_parts[j:]), node)
                        return FunctionCallNode(fn_name, [left, right], token=node)
        
        # Case: Simple 3-part infix function call "a op b"
        if len(parts) == 3:
            left = self._part_to_node(parts[0], node)
            op = parts[1]
            right = self._part_to_node(parts[2], node)
            
            if self._is_infix_function(op, self._current_module):
                return FunctionCallNode(op, [left, right], token=node)
        
        # Check for built-in function call pattern "längd från X"
        # This pattern should be treated as a function call, not a comparison
        for i, part in enumerate(parts):
            # Handle both "längd från X" (separate parts) and "längd från X" (single part)
            if part == 'längd' and i + 2 < len(parts) and parts[i + 1] == 'från':
                # Found "längd från X" pattern (separate parts)
                left_parts = parts[:i]
                target = ' '.join(parts[i + 2:])
                
                # Only create function call if there's no left side (pure "längd från X")
                # If there's a left side, let the comparison handling take over
                if not left_parts:
                    return FunctionCallNode('längd', [VarAccessNode(target, target=None, token=node)], token=node)
            elif part.startswith('längd från '):
                # Found "längd från X" pattern (single part)
                left_parts = parts[:i]
                target = part[10:].strip()  # Remove 'längd från ' prefix and strip
                
                # Only create function call if there's no left side (pure "längd från X")
                # If there's a left side, let the comparison handling take over
                if not left_parts:
                    return FunctionCallNode('längd', [VarAccessNode(target, target=None, token=node)], token=node)
        
        # Multi-part expression - check for comparison operators
        comparison_ops = ['är', 'större', 'mindre', 'lika', 'än', 'inte', 'eller', 'med', 'och', 'i']
        has_comparison = any(op in parts for op in comparison_ops)
        
        if has_comparison:
            # First, check if the first part is a defined function name followed by "med"
            # This handles cases like "index på första matchande med namn_lista, matchar_hiuh"
            if parts[0] in comparison_ops or (len(parts) > 1 and ' '.join(parts[:2]) in comparison_ops):
                pass  # Continue to comparison detection
            else:
                # Check if first part or first two parts form a defined function name
                fn_name = parts[0]
                if len(parts) > 1 and parts[1] in comparison_ops:
                    pass  # First part is not a function name
                else:
                    # Try to find a function name at the start
                    found_fn = None
                    for i in range(1, len(parts)):
                        test_name = ' '.join(parts[:i])
                        if self._is_defined(test_name, self._current_module):
                            found_fn = test_name
                            # Continue to try longer names
                        elif found_fn:
                            # We found a function name before, but this longer name isn't defined
                            # Use the found function name
                            if parts[i - 1] == 'med':
                                # This is a function call with "med" separator
                                # args_parts starts after "med" (parts[i-1])
                                args_parts = parts[i:]
                                args = []
                                current_arg = []
                                for part in args_parts:
                                    if part == ',':
                                        if current_arg:
                                            arg_str = ' '.join(current_arg)
                                            args.append(self._part_to_node(arg_str, node))
                                            current_arg = []
                                    else:
                                        current_arg.append(part)
                                if current_arg:
                                    arg_str = ' '.join(current_arg)
                                    args.append(self._part_to_node(arg_str, node))
                                return FunctionCallNode(found_fn, args, token=node)
                            break
                        elif parts[i] in comparison_ops:
                            # Hit a comparison operator without finding a function name
                            break
                    
                    # If we found a function name and the next token is 'med', create the function call
                    if found_fn and i < len(parts) and parts[i] == 'med':
                        # This is a function call with "med" separator
                        args_parts = parts[i + 1:]
                        args = []
                        current_arg = []
                        for part in args_parts:
                            if part == ',':
                                if current_arg:
                                    arg_str = ' '.join(current_arg)
                                    args.append(self._part_to_node(arg_str, node))
                                    current_arg = []
                            else:
                                current_arg.append(part)
                        if current_arg:
                            arg_str = ' '.join(current_arg)
                            args.append(self._part_to_node(arg_str, node))
                        return FunctionCallNode(found_fn, args, token=node)
            
            # Check if this is a simple function call: "fn_name arg"
            # where the argument contains a pattern like "element x från lista"
            if len(parts) >= 2:
                fn_name = parts[0]
                arg_parts = parts[1:]
                arg_str = ' '.join(arg_parts)
                # Check for "element x från lista" pattern in argument
                if arg_str.startswith('element ') and ' från ' in arg_str:
                    remaining = arg_str[8:]  # Remove 'element '
                    parts_split = remaining.split(' från ')
                    if len(parts_split) == 2:
                        idx_name = parts_split[0].strip()
                        target = parts_split[1].strip()
                        arg = FunctionCallNode('element', [
                            self._part_to_node(idx_name, node),
                            VarAccessNode(target, target=None, token=node)
                        ], token=node)
                        return FunctionCallNode(fn_name, [arg], token=node)
                # Also check for "index x från lista" pattern
                elif arg_str.startswith('index ') and ' från ' in arg_str:
                    remaining = arg_str[6:]  # Remove 'index '
                    parts_split = remaining.split(' från ')
                    if len(parts_split) == 2:
                        idx_name = parts_split[0].strip()
                        target = parts_split[1].strip()
                        arg = FunctionCallNode('element', [
                            self._part_to_node(idx_name, node),
                            VarAccessNode(target, target=None, token=node)
                        ], token=node)
                        return FunctionCallNode(fn_name, [arg], token=node)
            
            # Transform to ComparisonNode
            left_parts = []
            op_parts = []
            right_parts = []
            in_op = False
            in_right = False
            
            for part in parts:
                if part in comparison_ops and not in_right:
                    in_op = True
                    in_right = False
                    op_parts.append(part)
                elif in_op and part not in comparison_ops:
                    in_right = True
                    right_parts.append(part)
                elif not in_op and not in_right:
                    left_parts.append(part)
            
            # Build left side
            left_str = ' '.join(left_parts)
            # Check for "element x från lista" pattern first (before calling _part_to_node)
            if left_str.startswith('element ') and ' från ' in left_str:
                # Transform to element access: element(x, lista)
                # Format: "element index från target"
                remaining = left_str[8:]  # Remove 'element '
                parts_split = remaining.split(' från ')
                if len(parts_split) == 2:
                    idx_name = parts_split[0].strip()
                    target = parts_split[1].strip()
                    left = FunctionCallNode('element', [
                        self._part_to_node(idx_name, node),
                        VarAccessNode(target, target=None, token=node)
                    ], token=node)
                else:
                    left = self._part_to_node(left_str, node)
            elif len(left_parts) == 1:
                left = self._part_to_node(left_parts[0], node)
            else:
                left = VarAccessNode(left_str, target=None, token=node)
            
            # Build operator
            op = ' '.join(op_parts)
            
            # Build right side
            if len(right_parts) == 1:
                right_str = right_parts[0]
                # Check for "längd från X" pattern
                if right_str.startswith('längd från '):
                    target = right_str[10:].strip()
                    right = FunctionCallNode('längd', [VarAccessNode(target, target=None, token=node)], token=node)
                else:
                    right = self._part_to_node(right_str, node)
            else:
                right_str = ' '.join(right_parts)
                # Check for "längd från X" pattern
                if right_str.startswith('längd från '):
                    target = right_str[10:].strip()
                    right = FunctionCallNode('längd', [VarAccessNode(target, target=None, token=node)], token=node)
                else:
                    right = VarAccessNode(right_str, target=None, token=node)
            
            # Build left side
            left_str = ' '.join(left_parts)
            
            # Check if left side is a defined function AND operator is 'med'
            # If so, treat as function call: "fn med args" -> fn(args)
            if len(op_parts) == 1 and op_parts[0] == 'med':
                # Check if left is a defined function
                if self._is_defined(left_str, self._current_module) or left_str in ['skriv', 'ge', 'lista', 'längd', 'element', 'inmatning']:
                    # This is a function call
                    # Build arguments from right side (split by comma)
                    right_str = ' '.join(right_parts)
                    args = []
                    current_arg = []
                    for part in right_parts:
                        if part == ',':
                            if current_arg:
                                arg_str = ' '.join(current_arg)
                                args.append(self._part_to_node(arg_str, node))
                                current_arg = []
                        else:
                            current_arg.append(part)
                    if current_arg:
                        arg_str = ' '.join(current_arg)
                        args.append(self._part_to_node(arg_str, node))
                    return FunctionCallNode(left_str, args, token=node)
            
            # Check if left side is an undefined variable - if so, treat as string
            # This handles cases like "sätt x till detta är en hemlighet"
            if isinstance(left, VarAccessNode) and not left.target:
                if not self._is_defined(left.name, self._current_module):
                    return StringNode(' '.join(parts), token=node)
            
            # If right side is an undefined variable, treat it as a string literal
            # This handles cases like "text_stycke lika med Hiuhi do" where Hiuhi do is not defined
            if isinstance(right, VarAccessNode) and not right.target:
                if not self._is_defined(right.name, self._current_module):
                    right = StringNode(right.name, token=right)
            
            # Strip leading "är " from operator (är is syntactic sugar)
            if op.startswith('är '):
                op = op[3:]
            
            return ComparisonNode(left, op, right, token=node)
        
        # Check for 'som' cast operator (e.g., "10 som tal" or "x som text")
        if len(parts) == 3 and parts[1] == 'som':
            left = self._part_to_node(parts[0], node)
            target_type = parts[2]  # 'tal' or 'text'
            return CastNode(left, target_type=target_type, token=node)
        
        # Check for function call with multiple arguments using "med" separator
        # Pattern: "fn_name med arg1, arg2" or "fn_name med arg1 med arg2"
        # This handles cases like "index på första matchande med namn_lista, matchar_hiuh"
        if 'med' in parts:
            med_index = parts.index('med')
            fn_name = ' '.join(parts[:med_index])
            args_parts = parts[med_index + 1:]
            
            # Split args by comma
            args = []
            current_arg = []
            for part in args_parts:
                if part == ',':
                    if current_arg:
                        arg_str = ' '.join(current_arg)
                        args.append(self._part_to_node(arg_str, node))
                        current_arg = []
                else:
                    current_arg.append(part)
            if current_arg:
                arg_str = ' '.join(current_arg)
                args.append(self._part_to_node(arg_str, node))
            
            # Check if function name is defined
            if self._is_defined(fn_name, self._current_module):
                return FunctionCallNode(fn_name, args, token=node)
        
        # Default: parse with operator precedence
        return self._parse_expression_with_precedence(parts, node)
    
    def _part_to_node(self, part, token):
        """Convert a single part to the appropriate node."""
        if part.lower() == 'sant':
            return BoolNode(True, token=token)
        elif part.lower() == 'falskt':
            return BoolNode(False, token=token)
        elif part.isdigit():
            return IntNode(part, token=token)
        elif self._is_float(part):
            return FloatNode(part, token=token)
        elif part.startswith('"') or part.startswith("'"):
            return StringNode(part[1:-1], token=token)
        else:
            return VarAccessNode(part, target=None, token=token)
    
    def _is_float(self, s):
        """Check if string is a float."""
        try:
            float(s.replace(',', '.'))
            return '.' in s
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
    
    def _parse_expression_with_precedence(self, parts, node):
        """Parse expression parts with proper operator precedence.
        
        Precedence (lowest to highest):
        1. Boolean: " eller ", " och "
        2. Comparison: " är ", " större än ", " mindre än ", " lika med ", etc.
        3. Addition: "plus", "minus"
        4. Multiplication: "gånger", "delat med"
        """
        if not parts:
            return None
        
        if len(parts) == 1:
            return self._part_to_node(parts[0], node)
        
        # Check for built-in function calls first
        # "längd från X" -> längd(X)
        # "element X från Y" -> element(X, Y)
        # "kopia av X" -> kopia_av(X)
        if parts[0] == 'längd' and len(parts) >= 3 and parts[1] == 'från':
            # "längd från X" pattern
            target = ' '.join(parts[2:])
            return FunctionCallNode('längd', [VarAccessNode(target, target=None, token=node)], token=node)
        
        if parts[0] == 'längd' and len(parts) >= 2:
            # "längd X" pattern (alternative syntax)
            target = ' '.join(parts[1:])
            return FunctionCallNode('längd', [VarAccessNode(target, target=None, token=node)], token=node)
        
        if parts[0] in ['element', 'index'] and len(parts) >= 4 and 'från' in parts:
            # "element X från Y" or "index X från Y" pattern
            from_idx = parts.index('från')
            idx_name = ' '.join(parts[1:from_idx])
            target = ' '.join(parts[from_idx + 1:])
            return FunctionCallNode('element', [
                self._part_to_node(idx_name, node),
                VarAccessNode(target, target=None, token=node)
            ], token=node)
        
        if parts[0] == 'kopia' and len(parts) >= 3 and parts[1] == 'av':
            # "kopia av X" pattern
            target = ' '.join(parts[2:])
            return FunctionCallNode('kopia_av', [VarAccessNode(target, target=None, token=node)], token=node)
        
        # Define operator precedence levels
        # Each level is a list of operators to check (in order of precedence within the level)
        precedence_levels = [
            # Level 1: Boolean operators (lowest precedence)
            [' eller ', ' och '],
            # Level 2: Comparison operators
            [' är ', ' större än ', ' mindre än ', ' lika med ', ' inte ',
             ' större ', ' mindre ', ' är inte ', ' och ', ' eller ', ' i '],
            # Level 3: Addition/subtraction
            [' plus ', ' minus '],
            # Level 4: Multiplication/division (highest precedence)
            [' gånger ', ' delat med '],
        ]
        
        def split_by_operator(parts, operator):
            """Split parts by a specific operator, returning (left, op, right) tuples."""
            result = []
            current = []
            op_str = operator.strip()
            
            for i, part in enumerate(parts):
                # Check if this part starts an operator
                found_op = None
                for op in precedence_levels[-1]:  # Check highest precedence first
                    if part == op.strip():
                        found_op = op
                        break
                
                if found_op and len(current) > 0:
                    result.append((' '.join(current), found_op, parts[i+1:] if i+1 < len(parts) else []))
                    current = []
                else:
                    current.append(part)
            
            if current:
                result.append((' '.join(current), None, []))
            
            return result
        
        # Simplified approach: find the lowest precedence operator first
        # Then recursively parse left and right sides
        
        def find_operator(parts, level_index):
            """Find the rightmost operator at the given precedence level."""
            if level_index >= len(precedence_levels):
                return None, None
            
            operators = precedence_levels[level_index]
            found_op = None
            found_pos = -1
            
            # Build a combined string to search for operators
            combined = ' '.join(parts)
            
            for op in operators:
                pos = combined.find(op)
                if pos >= 0 and (found_pos < 0 or pos < found_pos):
                    found_op = op
                    found_pos = pos
            
            if found_op:
                # Split parts around this operator
                left_parts = []
                right_parts = []
                in_right = False
                op_len = len(found_op.strip().split())
                
                # Count tokens to skip for the operator
                op_tokens = found_op.strip().split()
                skip_count = 0
                
                for part in parts:
                    if skip_count > 0:
                        skip_count -= 1
                        continue
                    if in_right:
                        right_parts.append(part)
                    else:
                        # Check if this part starts the operator
                        if part == op_tokens[0]:
                            # Check if rest of operator matches
                            match = True
                            for j in range(1, len(op_tokens)):
                                if parts[parts.index(part) + j] != op_tokens[j]:
                                    match = False
                                    break
                            if match:
                                skip_count = len(op_tokens) - 1
                                in_right = True
                                continue
                        left_parts.append(part)
                
                return left_parts, found_op
            
            return None, None
        
        def parse_recursive(parts):
            if not parts:
                return None
            if len(parts) == 1:
                return self._part_to_node(parts[0], node)
            
            # Try each precedence level from lowest to highest
            for level_index in range(len(precedence_levels)):
                left_parts, found_op = find_operator(parts, level_index)
                
                if found_op and left_parts:
                    # Calculate right parts
                    combined = ' '.join(parts)
                    op_pos = combined.find(found_op)
                    right_combined = combined[op_pos + len(found_op):].strip()
                    right_parts = right_combined.split(' ') if right_combined else []
                    
                    left = parse_recursive(left_parts)
                    right = parse_recursive(right_parts)
                    
                    op_stripped = found_op.strip()
                    
                    # Create the appropriate node based on operator
                    if op_stripped == '+' or op_stripped == 'plus':
                        return AddNode(left, right, token=node)
                    elif op_stripped == '-' or op_stripped == 'minus':
                        return SubNode(left, right, token=node)
                    elif op_stripped == '*' or op_stripped == 'gånger':
                        return MulNode(left, right, token=node)
                    elif op_stripped == '/' or op_stripped == 'delat med':
                        return DivNode(left, right, token=node)
                    elif op_stripped == 'och':
                        return AndNode(left, right, token=node)
                    elif op_stripped == 'eller':
                        return OrNode(left, right, token=node)
                    else:
                        # Comparison operator
                        return ComparisonNode(left, op_stripped, right, token=node)
            
            # No operator found - treat as single value or string
            combined = ' '.join(parts)
            return self._part_to_node(combined, node)
        
        return parse_recursive(parts)
    
    # === ComparisonNode - special handling for stringification ===

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

        if left_unresolved:
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

        # Normal case - transform children
        new_left = self.visit(left)
        new_right = self.visit(right)

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
        
        return None
        
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
        value = self.visit(node.value)
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