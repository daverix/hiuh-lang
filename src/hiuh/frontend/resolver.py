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
        
        # Register all top-level declarations from this module
        for node in ast:
            self._register_node_declarations(node, name)
    
    def _register_node_declarations(self, node: ASTNode, module_name: str):
        """Register declarations from a node into the module registry."""
        if node is None:
            return
        
        if isinstance(node, ImportNode):
            # Record the import
            self.module_registry.add_import(module_name, node.module_name)
            return
        
        if isinstance(node, TypeDefNode):
            self.module_registry.modules[module_name].add_symbol(node.name, "type")
            return
        
        if isinstance(node, AssignNode):
            if isinstance(node.value, FunctionDefNode):
                self.module_registry.modules[module_name].add_symbol(
                    node.name, "func", FunctionSignature(params=node.value.params)
                )
            else:
                self.module_registry.modules[module_name].add_symbol(node.name, "var")
            return
        
        # Recursively handle nested structures
        if isinstance(node, FunctionDefNode):
            # Register params
            for param in node.params:
                self._add_local_var(module_name, param)
            # Register body declarations
            for stmt in node.body or []:
                self._register_node_declarations(stmt, module_name)
            return
        
        if isinstance(node, IfNode):
            for stmt in (node.true_block or []):
                self._register_node_declarations(stmt, module_name)
            for stmt in (node.false_block or []):
                self._register_node_declarations(stmt, module_name)
            return
        
        if isinstance(node, WhileNode):
            for stmt in (node.body or []):
                self._register_node_declarations(stmt, module_name)
            return
        
        if isinstance(node, TryCatchNode):
            if node.error_var:
                self._add_local_var(module_name, node.error_var)
            for stmt in (node.try_block or []):
                self._register_node_declarations(stmt, module_name)
            for stmt in (node.catch_block or []):
                self._register_node_declarations(stmt, module_name)
            if node.finally_block:
                for stmt in node.finally_block:
                    self._register_node_declarations(stmt, module_name)
    
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
        
        # Register all declarations
        for node in ast:
            self._register_node_declarations(node, module_name)
        
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
        
        # Register all declarations
        for node in ast:
            self._register_node_declarations(node, module_name)
    
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
    
    def _transform_module_ast(self, module_name: str, ast: list) -> list:
        """Transform all AST nodes in a module."""
        self._current_module = module_name
        return self._visit_nodes(ast)
    
    def resolve_all(self):
        # Single pass: collect local vars AND transform AST (imports resolved via visitor)
        self._pass = 1
        for module_name, module in list(self.modules.items()):
            self._current_module = module_name
            module.ast = self._visit_nodes(module.ast)
        
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
        """Visit an import node - load module if not already loaded."""
        # Check if module is already loaded
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
        return FunctionDefNode(params=node.params, body=body, line=node.line, column=node.column)
    
    def visit_FunctionCallNode(self, node):
        args = self._visit_nodes(node.args)
        if args is node.args:
            return node
        return FunctionCallNode(name=node.name, args=args, token=node)
    
    def visit_ReturnNode(self, node):
        value = self.visit(node.value)
        if value is node.value:
            return node
        return ReturnNode(value=value, token=node)
    
    # === Statement nodes - transform children ===
    
    def visit_AssignNode(self, node):
        # Collect the variable name as a local var
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
        condition = self.visit(node.condition)
        true_block = self._visit_nodes(node.true_block or [])
        false_block = self._visit_nodes(node.false_block) if node.false_block else None
        
        if condition is node.condition and true_block is node.true_block and false_block is node.false_block:
            return node
        
        return IfNode(
            condition=condition,
            true_block=true_block,
            false_block=false_block,
            line=node.line,
            column=node.column
        )
    
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
        return node  # No transformation needed
    
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