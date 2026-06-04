# -*- coding: utf-8 -*-
"""
Module registry - stores each module with its AST and symbol table.
Makes it easy to switch between AST and symbol-based representations for different backends.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FunctionSignature:
    """Signature for a function."""
    params: list[str] = field(default_factory=list)
    return_type: Optional[str] = None


@dataclass
class SymbolEntry:
    """An entry in the symbol table."""
    name: str
    type: str  # 'var', 'func', 'type', 'module'
    module: str
    signature: Optional[FunctionSignature] = None
    target: Optional[str] = None  # For field access or module prefix


@dataclass
class ModuleEntry:
    """
    A single module entry containing AST and symbol table.
    
    Used by the compiler to switch between AST and symbol-based representations
    for different backends (e.g., interpreter vs x86).
    """
    name: str
    path: str = ""
    ast: list = field(default_factory=list)  # Raw AST nodes
    symbols: dict[str, SymbolEntry] = field(default_factory=dict)  # Symbol name -> SymbolEntry
    imports: list[str] = field(default_factory=list)  # Modules this module imports
    exports: list[str] = field(default_factory=list)  # Symbol names exported
    
    def get_symbol(self, name: str) -> Optional[SymbolEntry]:
        """Get a symbol by name."""
        return self.symbols.get(name)
    
    def has_symbol(self, name: str) -> bool:
        """Check if a symbol exists."""
        return name in self.symbols
    
    def add_symbol(self, name: str, symbol_type: str, 
                   signature: FunctionSignature = None, target: str = None):
        """Add a symbol to this module."""
        entry = SymbolEntry(
            name=name,
            type=symbol_type,
            module=self.name,
            signature=signature,
            target=target
        )
        self.symbols[name] = entry
        if name not in self.exports:
            self.exports.append(name)
    
    def resolve_symbol(self, name: str) -> Optional[SymbolEntry]:
        """
        Resolve a symbol with import chain lookup.
        First check local, then imported modules.
        """
        # Check local first
        if name in self.symbols:
            return self.symbols[name]
        
        # Check imports
        for imported_name in self.imports:
            # Note: This requires access to the parent registry to get imported modules
            # The actual resolution is done by ModuleRegistry.resolve()
            pass
        
        return None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'path': self.path,
            'imports': self.imports,
            'exports': self.exports,
            'symbols': {
                s_name: {
                    'name': entry.name,
                    'type': entry.type,
                    'module': entry.module,
                    'signature': {
                        'params': entry.signature.params if entry.signature else [],
                        'return_type': entry.signature.return_type if entry.signature else None
                    } if entry.signature else None,
                    'target': entry.target
                }
                for s_name, entry in self.symbols.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ModuleEntry':
        """Create from dictionary (JSON deserialization)."""
        module = cls(
            name=data['name'],
            path=data.get('path', '')
        )
        module.imports = data.get('imports', [])
        module.exports = data.get('exports', [])
        
        for s_name, s_data in data.get('symbols', {}).items():
            sig_data = s_data.get('signature')
            sig = FunctionSignature(
                params=sig_data.get('params', []) if sig_data else [],
                return_type=sig_data.get('return_type') if sig_data else None
            ) if sig_data else None
            
            entry = SymbolEntry(
                name=s_data['name'],
                type=s_data['type'],
                module=s_data['module'],
                signature=sig,
                target=s_data.get('target')
            )
            module.symbols[s_name] = entry
        
        return module


class ModuleRegistry:
    """
    Registry of all modules with their ASTs and symbol tables.
    
    Makes it easy to switch between AST and symbol-based representations
    for different backends (e.g., interpreter vs x86).
    """
    
    def __init__(self, symbols_dir: str):
        self.symbols_dir = symbols_dir
        self.modules: dict[str, ModuleEntry] = {}
        self.errors: list[str] = []
    
    def add_module(self, name: str, path: str = "", ast: list = None) -> ModuleEntry:
        """Add or get a module entry."""
        if name not in self.modules:
            self.modules[name] = ModuleEntry(
                name=name,
                path=path,
                ast=ast or []
            )
        elif ast is not None:
            self.modules[name].ast = ast
        
        return self.modules[name]
    
    def get_module(self, name: str) -> Optional[ModuleEntry]:
        """Get a module entry by name."""
        return self.modules.get(name)
    
    def has_module(self, name: str) -> bool:
        """Check if a module exists."""
        return name in self.modules
    
    def add_import(self, module_name: str, imported_name: str):
        """Record that a module imports another module."""
        if module_name in self.modules:
            if imported_name not in self.modules[module_name].imports:
                self.modules[module_name].imports.append(imported_name)
    
    def resolve_symbol(self, name: str, from_module: str) -> Optional[SymbolEntry]:
        """
        Resolve a symbol name from a given module.
        
        Resolution order:
        1. Local symbols in the module
        2. Imported modules (in order)
        
        Args:
            name: Symbol name to resolve
            from_module: Module context for resolution
        
        Returns:
            SymbolEntry if found, None otherwise
        """
        # 1. Check local module
        if from_module in self.modules:
            if name in self.modules[from_module].symbols:
                return self.modules[from_module].symbols[name]
        
        # 2. Check imported modules (in order)
        if from_module in self.modules:
            for imported in self.modules[from_module].imports:
                if imported in self.modules:
                    if name in self.modules[imported].symbols:
                        return self.modules[imported].symbols[name]
        
        return None
    
    def is_local_var(self, name: str, module: str) -> bool:
        """Check if a name is a local variable in the module."""
        if module in self.modules:
            if name in self.modules[module].symbols:
                entry = self.modules[module].symbols[name]
                return entry.type == 'var'
        return False
    
    def is_known_function(self, name: str, module: str) -> bool:
        """Check if a name is a known function in the module scope."""
        if module in self.modules:
            if name in self.modules[module].symbols:
                entry = self.modules[module].symbols[name]
                return entry.type == 'func'
        return False
    
    def get_all_symbols(self, module: str) -> list[str]:
        """Get all symbol names for a module (including imports)."""
        if module not in self.modules:
            return []
        
        result = list(self.modules[module].symbols.keys())
        
        # Add imported symbols
        for imported in self.modules[module].imports:
            if imported in self.modules:
                for name, entry in self.modules[imported].symbols.items():
                    if name not in result:
                        result.append(name)
        
        return result
    
    def save(self, module_name: str = None):
        """
        Save symbol table(s) to JSON file(s).
        
        Args:
            module_name: If provided, save only that module's symbols.
                        Otherwise save all modules.
        """
        if not self.symbols_dir:
            return
        
        os.makedirs(self.symbols_dir, exist_ok=True)
        
        modules_to_save = []
        if module_name:
            if module_name in self.modules:
                modules_to_save = [module_name]
        else:
            modules_to_save = list(self.modules.keys())
        
        for name in modules_to_save:
            module = self.modules[name]
            
            # Create safe filename from module name
            safe_name = name.replace('.', '_').replace('/', '_')
            filepath = os.path.join(self.symbols_dir, f"{safe_name}.json")
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(module.to_dict(), f, indent=2, ensure_ascii=False)
    
    def load(self, module_name: str) -> Optional[ModuleEntry]:
        """
        Load symbol table for a specific module from JSON file.
        
        Args:
            module_name: Name of the module to load
        
        Returns:
            ModuleEntry if found, None otherwise
        """
        if not self.symbols_dir:
            return None
        
        safe_name = module_name.replace('.', '_').replace('/', '_')
        filepath = os.path.join(self.symbols_dir, f"{safe_name}.json")
        
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        module = ModuleEntry.from_dict(data)
        self.modules[module_name] = module
        return module
    
    def load_all(self):
        """Load all symbol tables from the target directory."""
        if not self.symbols_dir or not os.path.exists(self.symbols_dir):
            return
        
        for filename in os.listdir(self.symbols_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.symbols_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                module = ModuleEntry.from_dict(data)
                self.modules[module.name] = module
    
    def debug_print(self):
        """Print all modules for debugging."""
        for name in sorted(self.modules.keys()):
            module = self.modules[name]
            print(f"Module: {name}")
            print(f"  Path: {module.path}")
            print(f"  Imports: {module.imports}")
            print(f"  Exports: {module.exports}")
            print(f"  AST nodes: {len(module.ast)}")
            print(f"  Symbols:")
            for s_name, entry in sorted(module.symbols.items()):
                sig_str = ""
                if entry.signature:
                    sig_str = f"({', '.join(entry.signature.params)})"
                target_str = f" from {entry.target}" if entry.target else ""
                print(f"    {s_name}{sig_str}: {entry.type}{target_str}")
            print()