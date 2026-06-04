# -*- coding: utf-8 -*-
"""
Resolver: Resolves imports and symbol references across modules.
Two-pass: 
  1. Collect all declarations into registry
  2. Resolve all symbol references and transform AST
"""

import os
from hiuh.frontend.ast import *
from hiuh.frontend.registry import SymbolRegistry, SymbolInfo


class Resolver:
    def __init__(self, stdlib_path: str = None):
        self.registry = SymbolRegistry()
        self.stdlib_path = stdlib_path
        self.modules = {}
        self.errors = []
        self.main_module = None
        self._register_builtins()
    
    def _register_builtins(self):
        """Register built-in symbols."""
        # Ensure modules exist for both 'main' and '__main__' module names
        for mod in ['__main__', 'main']:
            self.registry.add_module(mod, "")
        # Built-in variables
        for mod in ['__main__', 'main']:
            self.registry.add_var(mod, "SANT")
            self.registry.add_var(mod, "FALSKT")
            self.registry.add_var(mod, "mellanrum")
            self.registry.add_var(mod, "ny")
            self.registry.add_var(mod, "rad")
            self.registry.add_var(mod, "lista")
            self.registry.add_var(mod, "inmatning")
            self.registry.add_var(mod, "heltal")
            self.registry.add_var(mod, "text")
            self.registry.add_var(mod, "flyttal")
        # Built-in functions
        for mod in ['__main__', 'main']:
            self.registry.add_func(mod, "lista", [], None)
            self.registry.add_func(mod, "inmatning", [], None)
            self.registry.add_func(mod, "heltal", [], None)
            self.registry.add_func(mod, "text", [], None)
            self.registry.add_func(mod, "flyttal", [], None)
    
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
        self.registry.add_module(module_name, script_dir or "")
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
        self.registry.add_module(module_name, file_path)
        
        # Load and flatten all nested imports recursively
        self._load_all_imports(module_name, base_dir)
    
    def _load_all_imports(self, module_name: str, base_dir: str):
        """Recursively load all imports for a module and flatten them."""
        module = self.modules.get(module_name)
        if not module or not module.ast:
            return
        
        # First, find and load any imports this module has
        imports_to_load = []
        for node in module.ast:
            if isinstance(node, ImportNode):
                if node.module_name not in self.modules:
                    file_path = self._find_module_file(node.module_name, module_name)
                    if file_path:
                        self._load_module(node.module_name, file_path, base_dir)
                        imports_to_load.append(node.module_name)
        
        # Recursively load imports of imported modules
        for imported_name in imports_to_load:
            self._load_all_imports(imported_name, base_dir)
        
        # Flatten this module's imports (replace ImportNode with exports)
        module.ast = self._flatten_imports(module.ast, module_name)
        
        # Also flatten imports inside nested structures
        self._flatten_nested_imports(module.ast, module_name)
    
    def _flatten_nested_imports(self, ast: list, module_name: str):
        """Flatten imports inside nested structures (functions, if, while)."""
        for node in ast:
            if isinstance(node, FunctionDefNode) and node.body:
                node.body = self._flatten_imports(node.body, module_name)
                self._flatten_nested_imports(node.body, module_name)
            elif isinstance(node, IfNode):
                if node.true_block:
                    node.true_block = self._flatten_imports(node.true_block, module_name)
                    self._flatten_nested_imports(node.true_block, module_name)
                if node.false_block:
                    node.false_block = self._flatten_imports(node.false_block, module_name)
                    self._flatten_nested_imports(node.false_block, module_name)
            elif isinstance(node, WhileNode) and node.body:
                node.body = self._flatten_imports(node.body, module_name)
                self._flatten_nested_imports(node.body, module_name)
    
    def _find_module_file(self, module_name: str, from_module: str) -> str:
        from_module_info = self.modules.get(from_module)
        if from_module_info and from_module_info.path:
            # Determine the search directory
            if os.path.isdir(from_module_info.path):
                search_dir = from_module_info.path
            else:
                search_dir = os.path.dirname(from_module_info.path)
            
            if search_dir and os.path.exists(search_dir):
                path_parts = module_name.split('.')
                local_path = os.path.join(search_dir, *path_parts) + '.hiuh'
                if os.path.exists(local_path):
                    return local_path
        
        # Fallback: check stdlib_path
        if self.stdlib_path and os.path.isdir(self.stdlib_path):
            path_parts = module_name.split('.')
            stdlib_path = os.path.join(self.stdlib_path, *path_parts) + '.hiuh'
            if os.path.exists(stdlib_path):
                return stdlib_path
        
        # Fallback: check the current working directory (for modules in project root)
        cwd = os.getcwd()
        if os.path.exists(cwd) and os.path.isdir(cwd):
            path_parts = module_name.split('.')
            cwd_path = os.path.join(cwd, *path_parts) + '.hiuh'
            if os.path.exists(cwd_path):
                return cwd_path
        
        return None
    
    def resolve_all(self):
        # Pass 1: Collect all declarations
        for module_name, module in list(self.modules.items()):
            self._collect_declarations(module_name, module.ast)
        
        # Pass 2: Flatten imports - replace ImportNode with module exports
        for module_name, module in list(self.modules.items()):
            module.ast = self._flatten_imports(module.ast, module_name)
        
        # Pass 3: Transform AST
        for module_name, module in list(self.modules.items()):
            module.ast = self._transform_ast(module.ast, module_name)
        
        return len(self.errors) == 0
    
    def _flatten_imports(self, ast: list, module_name: str) -> list:
        """Replace ImportNode with imports from modules."""
        result = []
        for node in ast:
            if isinstance(node, ImportNode):
                # ImportNode - inject the module's exports
                imported = self.modules.get(node.module_name)
                if imported and imported.ast:
                    # Recursively flatten the imported module's imports too
                    flattened_imported = self._flatten_imports(imported.ast, node.module_name)
                    for export in flattened_imported:
                        result.append(export)
            elif isinstance(node, TypeDefNode):
                # TypeDefNode: flatten nested imports in the type definition
                result.append(TypeDefNode(
                    node.name,
                    node.fields,
                    token=node
                ))
            elif isinstance(node, AssignNode) and isinstance(node.value, FunctionDefNode):
                # Flatten imports inside function bodies
                new_value = FunctionDefNode(
                    node.value.params,
                    self._flatten_imports(node.value.body, module_name),
                    line=node.value.line,
                    column=node.value.column
                )
                result.append(AssignNode(
                    node.name, new_value,
                    target_type=node.target_type,
                    token=node
                ))
            elif isinstance(node, (FunctionDefNode, WhileNode, IfNode)):
                result.append(self._flatten_node(node, module_name))
            else:
                result.append(node)
        return result
    
    def _flatten_node(self, node, module_name):
        if isinstance(node, FunctionDefNode):
            body = self._flatten_imports(node.body or [], module_name)
            return FunctionDefNode(node.params, body, line=node.line, column=node.column)
        if isinstance(node, WhileNode):
            body = self._flatten_imports(node.body or [], module_name)
            return WhileNode(node.condition, body, line=node.line, column=node.column)
        if isinstance(node, IfNode):
            t = self._flatten_imports(node.true_block or [], module_name)
            f = self._flatten_imports(node.false_block or [], module_name) if node.false_block else None
            return IfNode(node.condition, t, f, line=node.line, column=node.column)
        return node
    
    def _collect_declarations(self, module_name: str, ast: list):
        """Pass 1: Walk AST and collect all declarations including nested scopes."""
        for node in ast:
            self._collect_node_declarations(node, module_name)
    
    def _collect_node_declarations(self, node: ASTNode, module_name: str):
        """Collect declarations from a single node and its children."""
        if node is None:
            return
        
        if isinstance(node, ImportNode):
            self.registry.add_import(module_name, node.module_name)
            if node.module_name not in self.modules:
                # Determine base directory for module resolution
                importing_module = self.modules.get(module_name)
                if importing_module and importing_module.path:
                    if os.path.isdir(importing_module.path):
                        # path is already a directory
                        base_dir = importing_module.path
                    elif os.path.isfile(importing_module.path):
                        # path is a file, use its directory
                        base_dir = os.path.dirname(importing_module.path)
                    else:
                        # path might be a string like "/some/path" without actual file existence
                        base_dir = importing_module.path
                else:
                    base_dir = os.getcwd()
                
                file_path = self._find_module_file(node.module_name, module_name)
                if file_path:
                    self._load_module(node.module_name, file_path, base_dir)
                    imported_module = self.modules.get(node.module_name)
                    if imported_module:
                        self._collect_declarations(node.module_name, imported_module.ast)
        
        elif isinstance(node, TypeDefNode):
            self.registry.add_type(module_name, node.name, node.fields)
        
        elif isinstance(node, TryCatchNode):
            # error_var is in scope only for catch_block and finally_block
            pass
        
        elif isinstance(node, AssignNode):
            if isinstance(node.value, FunctionDefNode):
                self.registry.add_func(module_name, node.name, node.value.params, None)
                # Collect params as local vars
                self.registry.add_local_vars(module_name, node.value.params)
                # NOTE: Do NOT iterate over function body here.
                # Function bodies should be processed with their own module context,
                # not the importing module's context. Skip to avoid polluting local_vars.
            else:
                self.registry.add_var(module_name, node.name)
                self.registry.add_local_vars(module_name, [node.name])
        
        elif isinstance(node, FunctionDefNode):
            # Params are registered by the parent AssignNode, skip processing body
            # to avoid adding params to wrong module's local_vars when functions
            # are flattened from imported modules
            pass
        
        elif isinstance(node, IfNode):
            # Collect from condition (might have assignments)
            # Transform true_block and collect declarations
            for n in node.true_block or []:
                self._collect_node_declarations(n, module_name)
            for n in node.false_block or []:
                self._collect_node_declarations(n, module_name)
        
        elif isinstance(node, WhileNode):
            for n in node.body or []:
                self._collect_node_declarations(n, module_name)
    
    def _transform_ast(self, ast: list, module_name: str) -> list:
        """Pass 2: Transform AST - resolve VarAccessNode to StringNode when unknown."""
        return self._transform_nodes(ast, module_name)
    
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
        
        # Skip ImportNode - imports should have been flattened already
        if isinstance(node, ImportNode):
            return node
        
        # Special handling for TryCatchNode - handle error_var scope correctly
        if isinstance(node, TryCatchNode):
            # Transform try_block FIRST (error_var not in scope yet)
            transformed_try = self._transform_nodes(node.try_block, module_name)
            
            # Add error_var to scope for catch_block
            if node.error_var:
                self.registry.add_local_vars(module_name, [node.error_var])
            
            # Transform catch_block and finally_block
            transformed_catch = self._transform_nodes(node.catch_block, module_name) if node.catch_block else []
            transformed_finally = self._transform_nodes(node.finally_block, module_name) if node.finally_block else None
            
            # Build the transformed TryCatchNode
            return TryCatchNode(
                try_block=transformed_try,
                error_var=node.error_var,
                catch_block=transformed_catch,
                finally_block=transformed_finally,
                token=node
            )
        
        # Special handling for ComparisonNode - if any operand is an unresolved VarAccessNode,
        # transform the entire comparison to a string EXCEPT for membership checks
        if isinstance(node, ComparisonNode):
            left = node.left
            right = node.right
            
            # Get the operator
            op = node.op if hasattr(node, 'op') and node.op else ''
            
            # Membership check (i) should NOT be stringified - needs runtime evaluation
            # Keep the comparison as-is, let interpreter handle variable resolution at runtime
            if op.strip() == 'i':
                return self._copy_and_transform(node, module_name)
            
            # Other comparisons: stringify if any operand is unresolved
            left_unresolved = isinstance(left, VarAccessNode) and self._is_unresolved(left, module_name)
            right_unresolved = isinstance(right, VarAccessNode) and self._is_unresolved(right, module_name)
            
            if left_unresolved or right_unresolved:
                # At least one side is unresolved - stringify entire comparison
                left_str = self._get_string_value(left)
                right_str = self._get_string_value(right)
                return StringNode(f"{left_str} {op} {right_str}".strip(), token=node)
        
        # Check if this is a VarAccessNode that should become StringNode
        if isinstance(node, VarAccessNode):
            return self._resolve_var_access(node, module_name)
        
        # Special handling for FunctionCallNode - convert stringified type names back to VarAccessNode
        # This applies when name is a StringNode (was stringified during transformation)
        # AND the call has arguments (indicating it might be a constructor call with args)
        if isinstance(node, FunctionCallNode) and isinstance(node.name, StringNode):
            func_name = node.name.value
            if func_name:
                # Check if function name is a known type - if so, convert to VarAccessNode
                # Only convert if there are args (type constructors often have args)
                sym = self.registry.resolve(func_name, module_name)
                if sym and sym.type == 'type' and node.args:
                    # Name is a known type with args - convert to VarAccessNode
                    return FunctionCallNode(name=VarAccessNode(func_name, target=None), args=node.args, token=node)
        
        # Create a copy of the node with transformed children
        new_node = self._copy_and_transform(node, module_name)
        return new_node
    
    def _is_unresolved(self, node: VarAccessNode, module_name: str) -> bool:
        """Check if a VarAccessNode cannot be resolved in the current scope."""
        if node.target:
            return not self.registry.resolve(node.target, module_name)
        return not self.registry.resolve(node.name, module_name) and node.name not in self.registry.local_vars.get(module_name, set())
    
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
    
    def _collect_local_vars_from_body(self, module_name: str, body: list):
        """Recursively collect local variable names from a function body."""
        for stmt in body:
            if isinstance(stmt, AssignNode):
                # Only add simple assignments (not function definitions)
                # Function params are already added in _copy_and_transform
                if stmt.value is not None and not isinstance(stmt.value, FunctionDefNode):
                    self.registry.add_local_vars(module_name, [stmt.name])
            elif isinstance(stmt, WhileNode):
                self._collect_local_vars_from_body(module_name, stmt.body or [])
            elif isinstance(stmt, IfNode):
                self._collect_local_vars_from_body(module_name, stmt.true_block or [])
                if stmt.false_block:
                    self._collect_local_vars_from_body(module_name, stmt.false_block)
            elif isinstance(stmt, TryCatchNode):
                self._collect_local_vars_from_body(module_name, stmt.try_block or [])
                if stmt.catch_block:
                    self._collect_local_vars_from_body(module_name, stmt.catch_block)
                if stmt.finally_block:
                    self._collect_local_vars_from_body(module_name, stmt.finally_block)
    
    def _copy_and_transform(self, node: ASTNode, module_name: str) -> ASTNode:
        """Create a copy of node with transformed children."""
        cls = type(node)
        kwargs = {}
        
        for key, value in node.__dict__.items():
            if key in ['line', 'column']:
                # Skip these - they come from token
                continue
            elif key == 'name' and isinstance(value, VarAccessNode):
                # FunctionCallNode.name can be a VarAccessNode - transform it
                # But preserve VarAccessNode if it has a target (module call)
                # to allow runtime resolution of function name
                transformed = self._transform_node(value, module_name)
                # Keep as VarAccessNode for interpreter to handle module.function pattern
                if isinstance(transformed, StringNode) and value.target:
                    kwargs[key] = VarAccessNode(value.name, value.target)
                else:
                    kwargs[key] = transformed
            elif key == 'params' and isinstance(node, FunctionDefNode):
                # FunctionDefNode: Register params as local vars so body references resolve correctly
                self.registry.add_local_vars(module_name, value)
                kwargs[key] = value  # params are strings, don't transform
            elif key in ['params', 'fields', 'alias', 'module_name', 'error_var', 'target_type', 'target_var', 'target_list', 'op', 'args']:
                # These are simple values, not AST nodes - skip transformation
                # BUT args should still be transformed to resolve VarAccessNode -> StringNode
                if key == 'args':
                    kwargs[key] = self._transform_nodes(value, module_name)
                else:
                    kwargs[key] = value
            elif key == 'body' and isinstance(node, FunctionDefNode):
                # FunctionDefNode: Transform body with params already in scope
                # First pass: collect local variables from AssignNodes so they're in scope
                self._collect_local_vars_from_body(module_name, value)
                # Second pass: transform the body
                kwargs[key] = self._transform_nodes(value, module_name)
            elif isinstance(value, ASTNode):
                kwargs[key] = self._transform_node(value, module_name)
            elif isinstance(value, list):
                # Check if this is a list of strings (params, fields) or ASTNodes
                if value and isinstance(value[0], str):
                    kwargs[key] = value  # Don't transform string lists
                else:
                    kwargs[key] = self._transform_nodes(value, module_name)
            else:
                kwargs[key] = value
        
        return cls(**kwargs)
    
    def _resolve_var_access(self, node: VarAccessNode, module_name: str) -> ASTNode:
        """Resolve a variable/field access - return StringNode if unknown."""
        # Check if symbol exists
        if node.target:
            # Target-based access (e.g., 'x from list')
            symbol = self.registry.resolve(node.target, module_name)
            # Also check local vars for the target
            is_local = node.target in self.registry.local_vars.get(module_name, set())
            if symbol or is_local:
                return node
            return StringNode(f"{node.target}.{node.name}", token=node)
        
        # Check full name
        symbol = self.registry.resolve(node.name, module_name)
        if symbol:
            return node
        
        # Check local vars with full name
        is_local = node.name in self.registry.local_vars.get(module_name, set())
        if is_local:
            return node
        
        # Try individual parts
        name_parts = node.name.split()
        for part in name_parts:
            if part in self.registry.local_vars.get(module_name, set()):
                return node
            if self.registry.resolve(part, module_name):
                return node
        
        # Unknown symbol - transform to string literal
        return StringNode(node.name, token=node)
    
    def get_ast(self, module_name: str = None) -> list:
        """Get the AST for a module (transformed if resolve_all was called)."""
        if module_name is None:
            module_name = self.main_module
        return self.modules.get(module_name, ModuleInfo("", "")).ast


class ModuleInfo:
    def __init__(self, name: str, path: str):
        self.name = name
        self.path = path
        self.source = None
        self.tokens = None
        self.ast = None
        self.imports = []