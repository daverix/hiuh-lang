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
    def __init__(self, stdlib_path: str = None, target_dir: str = None):
        self.stdlib_path = stdlib_path
        self.target_dir = target_dir
        self.errors = []
        self.main_module = None
        
        # Module registry: stores AST and symbol table for each module
        self.module_registry = ModuleRegistry(target_dir=target_dir)
        
        # Internal module storage for raw AST parsing
        self.modules = {}  # name -> ModuleInfo (parsed AST)
        
        # Local variables tracked per module (for scope resolution)
        self.local_vars = {}  # module_name -> set of variable names
        
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
    
    def discover_modules_from_ast(self, module_name: str, ast: list, script_dir: str = None):
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
        return self._transform_nodes(ast, module_name)
    
    def resolve_all(self):
        # Pass 1: Mark all ImportNodes as resolved AND collect local variables
        for module_name, module in list(self.modules.items()):
            self._mark_imports_resolved(module.ast, module_name)
        
        # Pass 2: Update ModuleRegistry with ASTs
        for module_name, module in list(self.modules.items()):
            if module_name in self.module_registry.modules:
                self.module_registry.modules[module_name].ast = module.ast
            else:
                self.module_registry.add_module(module_name, module.path or "", module.ast)
        
        # Pass 3: Transform AST for symbol resolution (VarAccessNode, etc.)
        for module_name, module in list(self.modules.items()):
            module.ast = self._transform_module_ast(module_name, module.ast)
        
        # Pass 4: Update ModuleRegistry with transformed ASTs
        for module_name, module in list(self.modules.items()):
            self.module_registry.modules[module_name].ast = module.ast
        
        # Save symbol tables to target directory
        if self.target_dir:
            self.module_registry.save()
        
        return len(self.errors) == 0
    
    def _mark_imports_resolved(self, ast: list, module_name: str = None):
        """Mark all ImportNodes as resolved and collect local vars (Pass 1+2)."""
        for node in ast:
            if isinstance(node, ImportNode):
                if module_name:
                    node.resolved = True
            elif isinstance(node, AssignNode):
                if isinstance(node.value, FunctionDefNode):
                    # Collect params and recurse into body
                    if module_name:
                        for p in node.value.params:
                            self._add_local_var(module_name, p)
                    self._mark_imports_resolved(node.value.body or [], module_name)
                elif module_name:
                    # Non-function assignment - this is a local variable
                    self._add_local_var(module_name, node.name)
            elif isinstance(node, FunctionDefNode):
                # Collect params
                if module_name:
                    for p in node.params:
                        self._add_local_var(module_name, p)
                self._mark_imports_resolved(node.body or [], module_name)
            elif isinstance(node, IfNode):
                self._mark_imports_resolved(node.true_block or [], module_name)
                self._mark_imports_resolved(node.false_block or [], module_name)
            elif isinstance(node, WhileNode):
                self._mark_imports_resolved(node.body or [], module_name)
            elif isinstance(node, TryCatchNode):
                if module_name and node.error_var:
                    self._add_local_var(module_name, node.error_var)
                self._mark_imports_resolved(node.try_block or [], module_name)
                self._mark_imports_resolved(node.catch_block or [], module_name)
                if node.finally_block:
                    self._mark_imports_resolved(node.finally_block, module_name)
    
    def _transform_nodes(self, nodes: list, module_name: str) -> list:
        """Recursively transform a list of nodes."""
        result = []
        for node in nodes:
            transformed = self._transform_node(node, module_name)
            result.append(transformed)
        return result
    
    def _transform_node(self, node: ASTNode, module_name: str) -> ASTNode:
        """Transform a single node, recursively transforming children."""
        if node is None:
            return None
        
        # Mark ImportNode as resolved (points to ModuleRegistry)
        if isinstance(node, ImportNode):
            node.resolved = True
            return node
        
        # Special handling for TryCatchNode
        if isinstance(node, TryCatchNode):
            # Add error_var to scope for entire try-catch structure
            if node.error_var:
                self._add_local_var(module_name, node.error_var)
            
            # Transform try_block (error_var is in scope for consistency)
            transformed_try = self._transform_nodes(node.try_block, module_name)
            
            transformed_catch = self._transform_nodes(node.catch_block, module_name) if node.catch_block else []
            transformed_finally = self._transform_nodes(node.finally_block, module_name) if node.finally_block else None
            
            return TryCatchNode(
                try_block=transformed_try,
                error_var=node.error_var,
                catch_block=transformed_catch,
                finally_block=transformed_finally,
                token=node
            )
        
        # Special handling for ComparisonNode
        if isinstance(node, ComparisonNode):
            left = node.left
            right = node.right
            op = node.op if hasattr(node, 'op') and node.op else ''
            
            # Membership check (i) should NOT be stringified
            if op.strip() == 'i':
                return self._copy_and_transform(node, module_name)
            
            # Other comparisons: stringify if any operand is unresolved
            left_unresolved = isinstance(left, VarAccessNode) and self._is_unresolved(left, module_name)
            right_unresolved = isinstance(right, VarAccessNode) and self._is_unresolved(right, module_name)
            
            if left_unresolved or right_unresolved:
                left_str = self._get_string_value(left)
                right_str = self._get_string_value(right)
                return StringNode(f"{left_str} {op} {right_str}".strip(), token=node)
        
        # VarAccessNode: resolve or stringify
        if isinstance(node, VarAccessNode):
            return self._resolve_var_access(node, module_name)
        
        # FunctionCallNode with string name - check if it's a local callback
        if isinstance(node, FunctionCallNode) and isinstance(node.name, str):
            func_name = node.name
            if func_name:
                # Check if it's a known function - if so, keep as string
                sym = self.module_registry.resolve_symbol(func_name, module_name)
                if sym and sym.type == 'func':
                    pass
                elif self._is_local_var(func_name, module_name):
                    # It's a local variable (callback parameter) - convert to VarAccessNode
                    return FunctionCallNode(name=VarAccessNode(func_name, target=None), args=node.args, token=node)
        
        # FunctionCallNode with StringNode name - check if it's a known type
        if isinstance(node, FunctionCallNode) and isinstance(node.name, StringNode):
            func_name = node.name.value
            if func_name:
                sym = self.module_registry.resolve_symbol(func_name, module_name)
                if sym and sym.type == 'type' and node.args:
                    return FunctionCallNode(name=VarAccessNode(func_name, target=None), args=node.args, token=node)
        
        # Create a copy of the node with transformed children
        new_node = self._copy_and_transform(node, module_name)
        return new_node
    
    def _is_unresolved(self, node: VarAccessNode, module_name: str) -> bool:
        """Check if a VarAccessNode cannot be resolved in the current scope."""
        if node.target:
            return not self.module_registry.resolve_symbol(node.target, module_name)
        return not self.module_registry.resolve_symbol(node.name, module_name) and not self._is_local_var(node.name, module_name)
    
    def _is_local_var(self, name: str, module_name: str) -> bool:
        """Check if a name is a local variable in the module."""
        return name in self.local_vars.get(module_name, set())
    
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
    
    def _copy_and_transform(self, node: ASTNode, module_name: str) -> ASTNode:
        """Create a copy of node with transformed children."""
        cls = type(node)
        kwargs = {}
        
        for key, value in node.__dict__.items():
            if key in ['line', 'column']:
                continue
            elif key == 'name' and isinstance(value, VarAccessNode):
                transformed = self._transform_node(value, module_name)
                if isinstance(transformed, StringNode) and value.target:
                    kwargs[key] = VarAccessNode(value.name, value.target)
                else:
                    kwargs[key] = transformed
            elif key == 'params' and isinstance(node, FunctionDefNode):
                for p in value:
                    self._add_local_var(module_name, p)
                kwargs[key] = value
            elif key == 'body' and isinstance(node, FunctionDefNode):
                kwargs[key] = self._transform_nodes(value, module_name)
            elif key == 'body' and isinstance(node, WhileNode):
                kwargs[key] = self._transform_nodes(value or [], module_name)
            elif key == 'true_block':
                kwargs[key] = self._transform_nodes(value or [], module_name)
            elif key == 'false_block':
                kwargs[key] = self._transform_nodes(value or [], module_name) if value else None
            elif key == 'condition':
                kwargs[key] = self._transform_node(value, module_name) if value else None
            elif key in ['params', 'fields', 'alias', 'error_var', 'target_type', 'target_var', 'target_list', 'op', 'args']:
                if key == 'args':
                    kwargs[key] = self._transform_nodes(value, module_name)
                else:
                    kwargs[key] = value
            elif key == 'module_name':
                # Preserve module_name as-is (it's a string, not an AST to transform)
                kwargs[key] = value
            elif isinstance(value, ASTNode):
                kwargs[key] = self._transform_node(value, module_name)
            elif isinstance(value, list):
                if value and isinstance(value[0], str):
                    kwargs[key] = value
                else:
                    kwargs[key] = self._transform_nodes(value, module_name)
            else:
                kwargs[key] = value
        
        return cls(**kwargs)
    
    def _resolve_var_access(self, node: VarAccessNode, module_name: str) -> ASTNode:
        """Resolve a variable/field access - return StringNode if unknown."""
        if node.target:
            symbol = self.module_registry.resolve_symbol(node.target, module_name)
            is_local = self._is_local_var(node.target, module_name)
            if symbol or is_local:
                return node
            return StringNode(f"{node.target}.{node.name}", token=node)
        
        symbol = self.module_registry.resolve_symbol(node.name, module_name)
        if symbol:
            return node
        
        if self._is_local_var(node.name, module_name):
            return node
        
        # Try individual parts
        name_parts = node.name.split()
        for part in name_parts:
            if self._is_local_var(part, module_name):
                return node
            if self.module_registry.resolve_symbol(part, module_name):
                return node
        
        # Unknown symbol - transform to string literal
        return StringNode(node.name, token=node)
    
    def get_module_registry(self) -> ModuleRegistry:
        """Get the module registry (for use by backends)."""
        return self.module_registry
    
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