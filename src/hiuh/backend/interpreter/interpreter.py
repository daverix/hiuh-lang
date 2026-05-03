# -*- coding: utf-8 -*-
import sys
from hiuh.frontend.ast import *
from hiuh.backend.interpreter.environment import Environment

class Interpreter:
    def __init__(self):
        self.globals = Environment()
        self.globals.define("SANT", True)
        self.globals.define("FALSKT", False)
        # Built-in: lista
        self.globals.define("lista", lambda *args: list(args))
        self.env = self.globals

    def execute(self, nodes):
        last_result = None
        for node in nodes:
            last_result = self.visit(node)
        return last_result

    def visit(self, node):
        if node is None: return None
        method_name = f"visit_{type(node).__name__}"
        visitor = getattr(self, method_name, self.no_visit_method)
        return visitor(node)

    def no_visit_method(self, node):
        raise Exception(f"Interpreter: visit_{type(node).__name__} is not implemented")

    # --- Literals ---
    def visit_IntNode(self, node): return int(node.value)
    def visit_FloatNode(self, node): return float(node.value.replace(',', '.'))
    def visit_BoolNode(self, node): return node.value
    def visit_StringNode(self, node): return node.value

    # --- Variables ---
    def visit_VarAccessNode(self, node):
        return self.env.get(node.name)

    def visit_AssignNode(self, node):
        value = self.visit(node.value)

        # Scenario: sätt märke i min bil till Volvo
        if node.target_type:
            obj = self.env.get(node.target_type)
            if isinstance(obj, dict):
                obj[node.name] = value
                return value
            raise Exception(f"'{node.target_type}' är inte ett objekt (det är {type(obj).__name__}).")

        if callable(value) and isinstance(node.value, VarAccessNode):
            value = value()

        self.env.define(node.name, value)
        return value

    # --- Stdout ---
    def visit_PrintNode(self, node):
        value = self.visit(node.value)
        # If the value is already a newline (from 'ny rad'),
        # just print it without adding an extra one.
        if value == "\n":
            sys.stdout.write(value)
        else:
            sys.stdout.write(str(value) + "\n")
        return value

    # --- Math & Swedish String Concatenation ---
    def visit_AddNode(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)

        # Swedish Natural Language logic:
        # If we are joining text, assume a space is needed
        # (e.g., 'hej' pluss 'namn' -> 'hej namn')
        if isinstance(left, str) and isinstance(right, str):
            # Only add space if left doesn't already end with one
            # and right doesn't start with one
            sep = " " if not left.endswith(" ") and not right.startswith(" ") else ""
            return f"{left}{sep}{right}"

        # Fallback for numbers or mixed types
        try:
            return left + right
        except TypeError:
            # If addition fails (e.g. string + int), coerce to string with space
            return f"{left} {right}"

    def visit_SubNode(self, node): return self.visit(node.left) - self.visit(node.right)
    def visit_MulNode(self, node): return self.visit(node.left) * self.visit(node.right)
    def visit_DivNode(self, node): return self.visit(node.left) / self.visit(node.right)

    # --- Control Flow ---
    def visit_IfNode(self, node):
        condition = self.visit(node.condition)
        if condition:
            for stmt in node.true_block:
                self.visit(stmt)
        elif node.false_block:
            # Handle if false_block is the list directly or the list inside the list
            stmts = node.false_block[1] if isinstance(node.false_block, list) and len(node.false_block) > 1 else node.false_block
            if isinstance(stmts, list):
                for stmt in stmts:
                    self.visit(stmt)
        return None

    # --- Functions ---
    def visit_FunctionDefNode(self, node):
        # Capture the environment where the function was defined (Closure)
        closure_env = self.env

        def hiuh_function(*args):
            # Create a new local scope for the function call
            call_env = Environment(closure_env)

            # Map the arguments to parameter names
            for name, val in zip(node.params, args):
                call_env.define(name, val)

            # Execute the function body in the new environment
            previous_env = self.env
            self.env = call_env
            try:
                for stmt in node.body:
                    result = self.visit(stmt)
                    # If we hit a ReturnNode, stop and return that value
                    if isinstance(stmt, ReturnNode):
                        return result
            finally:
                self.env = previous_env
            return None

        return hiuh_function

    def visit_FunctionCallNode(self, node):
        # 1. Get the function object from the environment
        func = self.env.get(node.name)

        # 2. Evaluate all arguments
        args = [self.visit(arg) for arg in node.args]

        # 3. If it's a real function (callable), run it
        if callable(func):
            return func(*args)

        # If it's not a function and not a known variable,
        # only then do we do the Swedish greedy string fallback
        arg_str = " ".join(str(a) for a in args)
        return f"{node.name} med {arg_str}"

    def visit_ReturnNode(self, node):
        return self.visit(node.value)

    # --- Error Handling ---
    def visit_TryCatchNode(self, node):
        prev_env = self.env
        try:
            for stmt in node.try_block:
                self.visit(stmt)
        except HiuhRuntimeError as e:
            # Catch scope
            self.env = Environment(prev_env)
            self.env.define(node.error_var, e.value)
            for stmt in node.catch_block:
                self.visit(stmt)
        finally:
            self.env = prev_env

    def visit_UnaryOpNode(self, node):
        if node.op == "kasta":
            val = self.visit(node.operand)
            raise HiuhRuntimeError(val)
        return None

    def visit_ComparisonNode(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = node.op.strip()

        # Handle Swedish Comparison Operators
        if op == "större än":
            return left > right
        if op == "mindre än":
            return left < right
        if op == "lika med":
            return left == right
        if op == "större än eller lika med":
            return left >= right
        if op == "mindre än eller lika med":
            return left <= right

        # Handle Logical Operators
        if op == "och":
            return bool(left) and bool(right)
        if op == "eller":
            return bool(left) or bool(right)

        raise Exception(f"Interpreter: Okänd jämförelseoperator '{op}'")

    # --- Types and Objects ---
    def visit_TypeDefNode(self, node):
        # The constructor returns a NEW dictionary every time it is called
        def constructor():
            return {field.strip(): None for field in node.fields}

        self.env.define(node.name, constructor)
        return None

    def visit_AssignNode(self, node):
        value = self.visit(node.value)

        if node.target_type:
            # Setting a field: sätt märke i min bil till Volvo
            obj = self.env.get(node.target_type)
            if isinstance(obj, dict):
                obj[node.name] = value
                return value
            raise Exception(f"'{node.target_type}' är inte ett objekt (typ: {type(obj).__name__}).")

        # Instantiation logic: sätt min bil till bil
        # If 'value' is a blueprint/constructor and we are assigning it
        # to a variable (not a property), run it to create the dictionary.
        if callable(value) and not isinstance(node.value, FunctionDefNode):
            value = value()

        self.env.define(node.name, value)
        return value

    def visit_VarAccessNode(self, node):
        # Handle 'märke i min bil'
        if hasattr(node, 'target') and node.target:
            obj = self.env.get(node.target)
            if isinstance(obj, dict):
                # Return the field value, or the field name as string if empty (Swedish fallback)
                val = obj.get(node.name)
                return val if val is not None else node.name
            raise Exception(f"Kan inte läsa '{node.name}' från '{node.target}' (inte ett objekt).")

        return self.env.get(node.name)

class HiuhRuntimeError(Exception):
    def __init__(self, value):
        self.value = value
