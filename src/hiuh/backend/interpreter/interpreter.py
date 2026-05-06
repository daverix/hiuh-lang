# -*- coding: utf-8 -*-
import os
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
        self.globals.define("längd", lambda x: len(x) if hasattr(x, '__len__') else 0)
        self.globals.define("mellanrum", " ")
        self.open_files = []
        self.globals.define("öppna", self.builtin_open)
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

                if callable(val):
                    return val()

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
        return self.visit(node.left) + self.visit(node.right)

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

        if op == "i":
            try:
                return l in r
            except TypeError:
                return False
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

    def visit_CastNode(self, node):
        val = self.visit(node.value)
        target = node.target_type

        try:
            if target == "tal":
                return int(float(str(val).replace(',', '.'))) # Handles "10" or "10,5"
            if target == "flyttal":
                return float(str(val).replace(',', '.'))
            if target == "text":
                return str(val)
            if target == "boolesk":
                return bool(val)
        except (ValueError, TypeError):
            raise Exception(f"Kunde inte omvandla '{val}' till {target}")

        return val

    def visit_AppendNode(self, node):
        val = self.visit(node.value)
        lst = self.env.get(node.target_list)

        if isinstance(lst, list):
            lst.append(val)
            return val
        raise Exception(f"Kan inte lägga till i '{node.target_list}' för det är inte en lista.")

    def visit_RemoveIndexNode(self, node):
        idx = self.visit(node.index)
        lst = self.env.get(node.target_list)

        if isinstance(lst, list):
            try:
                # 0-based pop as requested
                return lst.pop(int(idx))
            except (IndexError, ValueError):
                raise Exception(f"Index {idx} finns inte i listan '{node.target_list}'")
        raise Exception(f"'{node.target_list}' är inte en lista.")

    def visit_RemoveValueNode(self, node):
        val = self.visit(node.value)
        lst = self.env.get(node.target_list)

        if isinstance(lst, list):
            if val in lst:
                lst.remove(val)
                return val
            # Return None or throw error if value doesn't exist
            return None
        raise Exception(f"Kan inte ta bort från '{node.target_list}' för det är inte en lista.")

    def builtin_open(self, path, mode_str="läsning"):
        # Map Swedish intent to Python modes
        # 'r'  = read
        # 'w'  = write (overwrite/new)
        # 'a' = append
        if mode_str == "skrivning":
            py_mode = 'w'
        elif mode_str == "läsning":
            py_mode = 'r'
        elif mode_str == "tillägg":
            py_mode = 'a'
        else:
            raise ValueError(f"Unknown mode {mode_str}")

        try:
            f = open(str(path), py_mode, encoding='utf-8')
            self.open_files.append(f)

            def at_eof():
                cur = f.tell()
                f.seek(0, os.SEEK_END)
                end = f.tell()
                f.seek(cur)
                return cur >= end

            return {
                "_file_handle": f,
                "läge": mode_str,
                "nästa rad": lambda: f.readline().rstrip('\n'),
                "gå till början": lambda: f.seek(0),
                "gå till slutet": lambda: f.tell() >= os.fstat(f.fileno()).st_size,
                "i slutet": at_eof
            }
        except Exception as e:
            raise Exception(f"Kunde inte öppna {path} för {mode_str}: {e}")

    def visit_FileWriteNode(self, node):
        content = self.visit(node.value)
        file_obj = self.env.get(node.target_var)

        if isinstance(file_obj, dict) and "_file_handle" in file_obj:
            f = file_obj["_file_handle"]
            f.write(str(content) + "\n") # Natural: write adds a newline
            f.flush() # Ensure it's written immediately
            return content
        raise Exception(f"'{node.target_var}' är inte en öppen fil.")

    def visit_CloseFileNode(self, node):
        file_obj = self.env.get(node.target_var)

        if isinstance(file_obj, dict) and "_file_handle" in file_obj:
            f = file_obj["_file_handle"]
            f.close()
            # Remove from tracking list if you implemented the auto-cleanup earlier
            if hasattr(self, 'open_files') and f in self.open_files:
                self.open_files.remove(f)
            return True
        raise Exception(f"'{node.target_var}' är inte en öppen fil.")