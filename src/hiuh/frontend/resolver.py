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
    
    def discover_modules_from_ast(self, module_name: str, ast: list):
        module = ModuleInfo(module_name, "")
        module.ast = ast
        self.modules[module_name] = module
        self.main_module = module_name
        self.registry.add_module(module_name, "")
    
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
    
    def _find_module_file(self, module_name: str, from_module: str) -> str:
        from_module_info = self.modules.get(from_module)
        if from_module_info:
            from_dir = os.path.dirname(from_module_info.path)
        else:
            from_dir = os.getcwd()
        
        path_parts = module_name.split('.')
        local_path = os.path.join(from_dir, *path_parts) + '.hiuh'
        if os.path.exists(local_path):
            return local_path
        
        if self.stdlib_path:
            stdlib_path = os.path.join(self.stdlib_path, *path_parts) + '.hiuh'
            if os.path.exists(stdlib_path):
                return stdlib_path
        
        return None
    
    def resolve_all(self):
        """Run both passes to resolve all modules."""
        for module_name, module in self.modules.items():
            self._collect_declarations(module_name, module.ast)
        
        for module_name, module in self.modules.items():
            module.ast = self._transform_ast(module.ast, module_name)
        
        return len(self.errors) == 0
    
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
                file_path = self._find_module_file(node.module_name, module_name)
                if file_path:
                    base_dir = os.path.dirname(self.modules.get(module_name).path) if self.modules.get(module_name) else os.getcwd()
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
                # Collect declarations from function body
                for body_node in node.value.body:
                    self._collect_node_declarations(body_node, module_name)
            else:
                self.registry.add_var(module_name, node.name)
                self.registry.add_local_vars(module_name, [node.name])
        
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
        
        elif isinstance(node, FunctionDefNode):
            self.registry.add_local_vars(module_name, node.params)
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
        
        # Special handling for ImportNode - transform unresolved module names
        if isinstance(node, ImportNode):
            # Transform the module name - if it's a VarAccessNode, stringify it
            module_name_val = node.module_name
            if isinstance(node.module_name, VarAccessNode):
                module_name_val = node.module_name.name if hasattr(node.module_name, 'name') else str(node.module_name)
            
            return ImportNode(
                module_name=module_name_val,
                alias=node.alias,
                token=node
            )
        
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
            elif key in ['params', 'fields', 'alias', 'module_name', 'error_var', 'target_type', 'target_var', 'target_list', 'op']:
                # These are simple values, not AST nodes - skip transformation
                kwargs[key] = value
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
        else:
            symbol = self.registry.resolve(node.name, module_name)
            is_local = node.name in self.registry.local_vars.get(module_name, set())
        
        if not symbol and not is_local:
            # Unknown symbol - transform to string literal
            return StringNode(node.name, token=node)
        
        return node
    
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