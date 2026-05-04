#!/usr/bin/env python3

import sys
import os

# Ensure the 'src' directory is in the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from hiuh.frontend.tokenizer import Tokenizer
from hiuh.frontend.parser import Parser
from hiuh.backend.interpreter.interpreter import Interpreter

def main():
    if len(sys.argv) < 2:
        print("Användning: python hiuh.py [filnamn.hiuh] [argument...]")
        return

    file_path = sys.argv[1]
    # 'argument' contains the script name and all following params
    cli_args = sys.argv[1:]

    if not os.path.exists(file_path):
        print(f"Fel: Filen '{file_path}' hittades inte.")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        source = f.read()

    # 1. Tokenize
    tokenizer = Tokenizer()
    tokens = tokenizer.tokenize(source)

    # 2. Parse
    parser = Parser(tokens)
    try:
        nodes = parser.parse()
    except SyntaxError as e:
        print(f"Syntaxfel: {e}")
        return

    # 3. Interpret
    interpreter = Interpreter()
    # Inject the 'argument' list into globals
    interpreter.globals.define("argument", cli_args)

    try:
        interpreter.execute(nodes)
    except Exception as e:
        print(f"Körningsfel: {e}")

if __name__ == "__main__":
    main()
