# -*- coding: utf-8 -*-
"""
SymbolRegistry: Stores all symbols across all modules.
Used by the resolver to resolve cross-module references.
"""

from typing import Optional


class FuncSignature:
    """Function signature information."""
    def __init__(self, params: list[str], return_type: Optional[str] = None):
        self.params = params
        self.return_type = return_type
    
    def __repr__(self):
        return f"Func({self.params}) -> {self.return_type}"


class TypeSignature:
    """Type (struct) signature information."""
    def __init__(self, name: str, fields: list[str]):
        self.name = name
        self.fields = fields
    
    def __repr__(self):
        return f"Type({self.name}: {self.fields})"


class SymbolInfo:
    """Complete symbol information."""
    def __init__(self, name: str, symbol_type: str, module: str, signature):
        self.name = name
        self.type = symbol_type  # "func", "type", "var"
        self.module = module
        self.signature = signature  # FuncSignature, TypeSignature, or None


class SymbolRegistry:
    """Global registry of all symbols across all modules."""
    
    def __init__(self):
        self.modules = {}      # module_name → file_path
        self.symbols = {}      # module_name → { name → SymbolInfo }
        self.deps = {}         # module_name → [imported_module_names]
        self.source_cache = {} # module_name → source_code
        self.local_vars = {}   # module_name → set of local variable names (for resolver)
    
    def add_module(self, name: str, path: str):
        """Register a module."""
        self.modules[name] = path
        if name not in self.symbols:
            self.symbols[name] = {}
        if name not in self.deps:
            self.deps[name] = []
        if name not in self.local_vars:
            self.local_vars[name] = set()
    
    def add_func(self, module: str, name: str, params: list[str], return_type: Optional[str] = None):
        """Register a function symbol."""
        sig = FuncSignature(params, return_type)
        self.symbols[module][name] = SymbolInfo(name, "func", module, sig)
        # Add params as local variables so they resolve correctly
        if module in self.local_vars:
            for p in params:
                self.local_vars[module].add(p)
    
    def add_type(self, module: str, name: str, fields: list[str]):
        """Register a type (struct) symbol."""
        sig = TypeSignature(name, fields)
        self.symbols[module][name] = SymbolInfo(name, "type", module, sig)
    
    def add_var(self, module: str, name: str):
        """Register a variable symbol (simple value)."""
        self.symbols[module][name] = SymbolInfo(name, "var", module, None)
        if module in self.local_vars:
            self.local_vars[module].add(name)
    
    def add_local_vars(self, module: str, names: list[str]):
        """Add local variable names (e.g., function parameters)."""
        if module not in self.local_vars:
            self.local_vars[module] = set()
        for name in names:
            self.local_vars[module].add(name)
    
    def add_import(self, module: str, imported: str):
        """Record that a module imports another module."""
        if imported not in self.deps[module]:
            self.deps[module].append(imported)
    
    def get_module(self, name: str) -> Optional[str]:
        """Get the file path for a module."""
        return self.modules.get(name)
    
    def resolve(self, name: str, from_module: str) -> Optional[SymbolInfo]:
        """
        Resolve a symbol name from a given module.
        Checks: local symbols → imported modules → builtins.
        """
        # 1. Check local module
        if name in self.symbols.get(from_module, {}):
            return self.symbols[from_module][name]
        
        # 2. Check imported modules (in order)
        for imported in self.deps.get(from_module, []):
            if name in self.symbols.get(imported, {}):
                return self.symbols[imported][name]
        
        # 3. Built-in symbols (handled separately)
        return None
    
    def get_imports(self, module: str) -> list[str]:
        """Get all modules imported by a given module."""
        return self.deps.get(module, [])