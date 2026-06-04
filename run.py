#!/usr/bin/env python3

import os
import sys

# Ensure the 'src' directory is in the python path - BEFORE any hiuh imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from hiuh.frontend.module_registry import ModuleRegistry

from hiuh.frontend.resolver import Resolver
from hiuh.backend.interpreter.interpreter import Interpreter


def get_stdlib_path():
    """Get the standard library path, with fallbacks."""
    # 1. Explicit env var
    if os.environ.get("HIUE_LIB"):
        return os.environ["HIUE_LIB"]
    
    # 2. Fallback: relative to this file (for development)
    compiler_dir = os.path.dirname(os.path.abspath(__file__))
    stdlib = os.path.join(compiler_dir, "hiuh_i_hiuh")
    if os.path.exists(stdlib):
        return stdlib
    
    return None  # No stdlib available


def compile_and_run(file_path: str, cli_args: list):
    """Compile and run a hiuh file with multi-module support."""
    
    abs_path = os.path.abspath(file_path)
    base_dir = os.path.dirname(abs_path)
    
    if not os.path.exists(abs_path):
        print(f"Fel: Filen '{abs_path}' hittades inte.")
        return

    working_dir = os.path.dirname(os.path.abspath(__file__))

    # Get stdlib path (if available)
    stdlib_path = get_stdlib_path()
    symbols_dir = os.path.join(working_dir, "build", "symbols")

    module_registry = ModuleRegistry(symbols_dir)

    # Discover and parse all modules
    resolver = Resolver(module_registry, stdlib_path=stdlib_path)
    
    try:
        main_module = resolver.discover_modules(abs_path)
    except Exception as e:
        print(f"Upptäcktfel: {e}")
        return
    
    # Resolve all cross-module references
    success = resolver.resolve_all()
    if not success:
        print("Upplösningsfel:")
        for error in resolver.errors:
            print(f"  {error}")
        return
    
    # Get the main module's AST
    main_module_info = resolver.modules.get(main_module)
    if not main_module_info:
        print(f"Kunde inte hitta huvudmodul: {main_module}")
        return
    
    nodes = main_module_info.ast
    
    # Execute with interpreter
    interpreter = Interpreter(module_registry)
    interpreter.globals.define("argument", cli_args)
    interpreter.script_dir_stack = [base_dir]
    interpreter.modules = resolver.modules  # Pass module info for future use
    
    try:
        interpreter.execute(nodes)
    except Exception as e:
        print(f"Körningsfel: {e}")


def main():
    if len(sys.argv) < 2:
        print("Användning: python run.py [filnamn.hiuh] [argument...]")
        print("")
        print("Miljövariabler:")
        print("  HIUE_LIB    Sökväg till hiuh's standardbibliotek")
        return

    file_path = sys.argv[1]
    cli_args = sys.argv[1:]
    
    compile_and_run(file_path, cli_args)


if __name__ == "__main__":
    main()