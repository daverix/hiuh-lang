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

            if hasattr(obj, 'value'):
                obj = obj.value

            if isinstance(obj, str):
                try:
                    idx = int(node.name)
                    if 0 <= idx < len(obj):
                        return obj[idx]
                    return "" # Return empty string for out-of-bounds indices safely
                except ValueError:
                    # If it's not a digit index, it might be a property lookup like 'längd från text'
                    if node.name == "längd":
                        return len(obj)

            if isinstance(obj, list):
                try:
                    return obj[int(node.name)]
                except (ValueError, IndexError):
                    raise Exception(f"Index {node.name} saknas i listan {node.target}")

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
        left = self.visit(node.left)
        right = self.visit(node.right)

        # Runtime Type Check: If both are numbers, do mathematical addition
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            return left + right

        # Fallback: If either side is text, cast both to strings for concatenation
        # This converts: integer (1) plus string (".s") -> "1.s"
        return str(left) + str(right)

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
        args = [self.visit(arg) for arg in node.args]

        if isinstance(node.name, VarAccessNode) and node.name.target:
            module_dict = self.env.get(node.name.target)
            if isinstance(module_dict, dict):
                func = module_dict.get(node.name.name)
                if func and callable(func):
                    return func(*args)
            raise Exception(f"Hittade inte funktionen '{node.name.name}' i modulen '{node.name.target}'.")

        f = self.env.get(node.name)

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

    def visit_NotNode(self, node):
        val = self.visit(node.condition)
        return not bool(val)

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
            if node.finally_block:
                for s in node.finally_block:
                    self.visit(s)
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
            raise ValueError(f"Okänt läge {mode_str}")

        try:
            f = open(str(path), py_mode, encoding='utf-8')
            self.open_files.append(f)

            # We use a mutable state container to track if we peeked/read an empty line
            state = {"last_line": None, "reached_end": False}

            def read_next_line():
                line = f.readline()
                if line == "": # Python returns completely empty string ONLY at EOF
                    state["reached_end"] = True
                    return ""
                return line.rstrip('\n')

            def check_is_end():
                # If we already flagged EOF during a read action
                if state["reached_end"]:
                    return True

                # Peek ahead: can we read anything?
                pos = f.tell()
                next_check = f.readline()
                f.seek(pos)

                if next_check == "":
                    state["reached_end"] = True
                    return True
                return False

            return {
                "_file_handle": f,
                "läge": mode_str,
                "nästa rad": read_next_line,
                "gå till början": lambda: (f.seek(0), state.update({"reached_end": False})),
                "gå till slutet": lambda: f.tell() >= os.fstat(f.fileno()).st_size,
                "i slutet": check_is_end
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

    def visit_ImportNode(self, node):
        path_parts = node.module_name.split('.')
        relative_path = os.path.sep.join(path_parts)
        module_file = f"{relative_path}.hiuh"
        if not os.path.exists(module_file):
            raise Exception(f"Modulen '{node.module_name}' hittades inte ({module_file}).")

        with open(module_file, 'r', encoding='utf-8') as f:
            module_source = f.read()

        from hiuh.frontend.tokenizer import Tokenizer
        from hiuh.frontend.parser import Parser

        tokenizer = Tokenizer()
        tokens = tokenizer.tokenize(module_source)
        parser = Parser(tokens)
        module_nodes = parser.parse()

        module_env = Environment(self.globals)

        old_env = self.env
        self.env = module_env
        try:
            for m_node in module_nodes:
                self.visit(m_node)
        finally:
            self.env = old_env # Always swap back

        if hasattr(module_env, 'values'):
            module_exports = dict(module_env.values)
        elif hasattr(module_env, 'vars'):
            module_exports = dict(module_env.vars)
        else:
            module_exports = module_env.get_local_bindings()

        namespace_name = node.alias if node.alias else path_parts[-1]
        self.env.define(namespace_name, module_exports)

        return module_exports