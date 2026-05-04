# -*- coding: utf-8 -*-
import sys
from hiuh.frontend.ast import *
from hiuh.backend.interpreter.environment import Environment

class Interpreter:
    def __init__(self):
        self.globals = Environment()
        self.globals.define("SANT", True)
        self.globals.define("FALSKT", False)
        # Built-in: lista creates a Python list
        self.globals.define("lista", lambda *args: list(args))
        # Built-in: inmatning reads from stdin
        self.globals.define("inmatning", lambda: sys.stdin.readline().strip())
        self.env = self.globals

    def execute(self, nodes):
        res = None
        for node in nodes:
            res = self.visit(node)
        return res

    def visit(self, node):
        if node is None: return None
        method = f"visit_{type(node).__name__}"
        visitor = getattr(self, method, self.no_visit_method)
        return visitor(node)

    def no_visit_method(self, node):
        raise Exception(f"Interpreter: visit_{type(node).__name__} is not implemented")

    # --- Literals ---
    def visit_IntNode(self, node): return int(node.value)
    def visit_FloatNode(self, node): return float(node.value)
    def visit_BoolNode(self, node): return node.value
    def visit_StringNode(self, node): return node.value

    # --- Variables & List/Dict Access ---
    def visit_VarAccessNode(self, node):
        if node.target:
            obj = self.env.get(node.target)
            # List Access: element 0 från lista
            if isinstance(obj, list):
                try:
                    return obj[int(node.name)]
                except (ValueError, IndexError):
                    raise Exception(f"Index {node.name} saknas i listan {node.target}")
            # Object Access: fält från objekt
            if isinstance(obj, dict):
                val = obj.get(node.name)
                return val if val is not None else node.name
        return self.env.get(node.name)

    def visit_AssignNode(self, node):
        value = self.visit(node.value)

        if node.target_type:
            obj = self.env.get(node.target_type)
            # List Set: sätt element 0 i lista till x
            if isinstance(obj, list):
                try:
                    obj[int(node.name)] = value
                    return value
                except (ValueError, IndexError):
                    raise Exception(f"Index {node.name} saknas i listan {node.target_type}")
            # Object Set: sätt fält i objekt till x
            if isinstance(obj, dict):
                obj[node.name] = value
                return value

        # Instantiate types (e.g. sätt p till person)
        if callable(value) and isinstance(node.value, VarAccessNode):
            value = value()

        self.env.define(node.name, value)
        return value

    # --- Stdout ---
    def visit_PrintNode(self, node):
        val = self.visit(node.value)
        sys.stdout.write(str(val))
        return val

    # --- Math & Swedish String Concatenation ---
    def visit_AddNode(self, node):
        l = self.visit(node.left)
        r = self.visit(node.right)
        if isinstance(l, str) and isinstance(r, str):
            sep = " " if not l.endswith(" ") and not r.startswith(" ") else ""
            return f"{l}{sep}{r}"
        try:
            return l + r
        except TypeError:
            return f"{l} {r}"

    def visit_SubNode(self, node): return self.visit(node.left) - self.visit(node.right)
    def visit_MulNode(self, node): return self.visit(node.left) * self.visit(node.right)
    def visit_DivNode(self, node): return self.visit(node.left) / self.visit(node.right)

    # --- Control Flow ---
    def visit_IfNode(self, node):
        if self.visit(node.condition):
            for s in node.true_block: self.visit(s)
        elif node.false_block:
            # Handle if false_block is a list of nodes or a single statement
            stmts = node.false_block if isinstance(node.false_block, list) else [node.false_block]
            for s in stmts: self.visit(s)

    def visit_WhileNode(self, node):
        while self.visit(node.condition):
            for s in node.body: self.visit(s)

    # --- Functions ---
    def visit_FunctionDefNode(self, node):
        closure = self.env
        def hiuh_func(*args):
            call_env = Environment(closure)
            for n, v in zip(node.params, args):
                call_env.define(n, v)

            prev_env = self.env
            self.env = call_env
            try:
                for s in node.body:
                    res = self.visit(s)
                    if isinstance(s, ReturnNode):
                        return res
            finally:
                self.env = prev_env
        return hiuh_func

    def visit_FunctionCallNode(self, node):
        f = self.env.get(node.name)
        # Visited arguments
        args = [self.visit(arg) for arg in node.args]

        if callable(f):
            return f(*args)

        # Swedish Fallback Rule
        arg_str = " ".join(map(str, args))
        return f"{node.name} med {arg_str}"

    def visit_ReturnNode(self, node):
        return self.visit(node.value)

    def visit_ComparisonNode(self, node):
        l = self.visit(node.left)
        r = self.visit(node.right)
        op = node.op.strip()
        if op == "större än": return l > r
        if op == "mindre än": return l < r
        if op == "lika med": return l == r
        if op == "större än eller lika med": return l >= r
        if op == "mindre än eller lika med": return l <= r
        if op == "och": return bool(l) and bool(r)
        if op == "eller": return bool(l) or bool(r)
        return False

    # --- Error Handling ---
    def visit_TryCatchNode(self, node):
        old_env = self.env
        try:
            for s in node.try_block: self.visit(s)
        except Exception as e:
            # Create catch scope
            self.env = Environment(old_env)
            # Use custom value if HiuhRuntimeError, else standard Python message
            val = getattr(e, 'value', str(e))
            self.env.define(node.error_var, val)
            for s in node.catch_block: self.visit(s)
        finally:
            self.env = old_env

    def visit_UnaryOpNode(self, node):
        if node.op == "kasta":
            val = self.visit(node.operand)
            err = Exception(val)
            err.value = val # Attach for catch block
            raise err

    def visit_TypeDefNode(self, node):
        # Store constructor: returns a new dict with defined fields
        self.env.define(node.name, lambda: {f.strip(): None for f in node.fields})
