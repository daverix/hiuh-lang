# -*- coding: utf-8 -*-
import os
import sys
from hiuh.frontend.ast import *
from hiuh.backend.interpreter.environment import Environment
from hiuh.frontend.module_registry import ModuleRegistry


class ReturnException(Exception):
    """Internal interpreter exception used to bubble return values out of nested scopes."""
    def __init__(self, value):
        self.value = value

class Char:
    """Internal interpreter representation of a single character token byte."""
    def __init__(self, value: str):
        self.value = value  # Guaranteed to be a 1-character string

    def __eq__(self, other):
        if isinstance(other, Char):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other
        return False

    def __str__(self):
        return self.value

    def __repr__(self):
        return f"Char({self.value!r})"

class Interpreter:
    def __init__(self, module_registry: ModuleRegistry):
        self.module_registry = module_registry  # ModuleRegistry for cross-module resolution
        self.globals = Environment()
        self.globals.define("SANT", True)
        self.globals.define("FALSKT", False)
        # Built-in: lista creates a Python list
        self.globals.define("lista", lambda *args: list(args))
        # Built-in: inmatning reads from stdin
        self.globals.define("inmatning", lambda: sys.stdin.readline().strip())
        self.globals.define("längd", lambda x: len(x) if hasattr(x, '__len__') else 0)
        # Built-in: element gets element at index from list
        self.globals.define("element", lambda idx, lst: lst[idx] if isinstance(lst, list) and 0 <= idx < len(lst) else None)
        self.globals.define("mellanrum", " ")
        self.globals.define("öppna", self.builtin_open)

        self.open_files = []
        self.call_stack = []
        self.script_dir_stack = [os.getcwd()]
        self.env = self.globals
        self.modules = {}  # Populated by resolver
        self._module_exports = {}  # Cache for module export values

    def execute(self, nodes):
        res = None
        for node in nodes:
            res = self.visit(node)
        return res

    def visit(self, node):
        if node is None: return None

        if hasattr(node, 'line') and node.line is not None:
            if self.call_stack:
                self.call_stack[-1]["line"] = node.line
                self.call_stack[-1]["column"] = getattr(node, 'column', 1)

        method = f"visit_{type(node).__name__}"
        visitor = getattr(self, method, self.no_visit_method)

        try:
            return visitor(node)
        except Exception as e:
            # Catch errors anywhere in the execution tree and print the trace once
            if not hasattr(e, '_hiuh_traceback_printed'):
                self.print_hiuh_traceback()
                e._hiuh_traceback_printed = True
            raise e

    def print_hiuh_traceback(self):
        """Prints a human-readable trace of the execution path when a crash happens."""
        import sys
        print("\n--- Spårningshistorik (Call Stack) ---", file=sys.stderr)

        # Traverse frames from the first caller down to the execution crash line
        for frame in self.call_stack:
            # Skip the dummy internal Python runner seed layer if it doesn't represent real code
            if frame["function"] == "<huvudprogram>" and frame["file"] == "run.py":
                continue

            col_info = f", Kolumn {frame['column']}" if "column" in frame else ""
            print(f"  Fil: '{frame['file']}', Rad {frame['line']}{col_info}, i funktion: {frame['function']}", file=sys.stderr)

        print("--------------------------------------\n", file=sys.stderr)

    def no_visit_method(self, node):
        raise Exception(f"Interpreter: visit_{type(node).__name__} is not implemented")
    
    def visit_ImportNode(self, node):
        """Handle resolved ImportNode by loading module from ModuleRegistry."""
        if not getattr(node, 'resolved', False):
            raise Exception(f"ImportNode for '{node.module_name}' is not resolved")
        
        # Look up the module in the module registry
        if self.module_registry and node.module_name in self.module_registry.modules:
            module = self.module_registry.modules[node.module_name]
            
            # Execute the module's AST to populate the environment
            if module.ast:
                prev_env = self.env
                module_env = Environment(prev_env)
                self.env = module_env
                try:
                    for stmt in module.ast:
                        if isinstance(stmt, ImportNode) and not getattr(stmt, 'resolved', False):
                            continue  # Skip unresolved nested imports
                        self.visit(stmt)
                    
                    # For wildcard imports (import_all=True): copy all to parent
                    # For alias imports (import_all=False): symbols are scoped to alias only
                    if node.import_all:
                        # Wildcard import: copy all module-level definitions to parent
                        for name, value in module_env.vars.items():
                            prev_env.define(name, value)
                    elif node.alias:
                        # Alias import: store module env under alias for qualified access (h.hälsa)
                        prev_env.define(node.alias, module_env)
                    # Non-wildcard, no alias: only execute for side effects, no symbol export
                finally:
                    self.env = prev_env
        # If not in registry, the import resolved to nothing (module has no exports)
        return None

    # --- Literals ---
    def visit_IntNode(self, node): return int(node.value)
    def visit_FloatNode(self, node): return float(node.value)
    def visit_BoolNode(self, node): return node.value
    def visit_StringNode(self, node): return node.value

    def _resolve_index(self, name):
        try:
            return int(name)
        except ValueError:
            index_value = self.env.get(name)
            if index_value is None:
                raise Exception(f"Variabeln '{name}' finns inte i aktuell kontext")
            try:
                return int(index_value)
            except (ValueError, TypeError):
                raise Exception(f"Variabeln '{name}' är inte ett giltigt index: {index_value}")

    # --- Variables & List/Dict Access ---
    def visit_VarAccessNode(self, node):
        if node.target:
            obj = self.env.get(node.target)

            if hasattr(obj, 'value'):
                obj = obj.value

            # Handle Environment objects (from aliased imports like `använd x som h`)
            if hasattr(obj, 'vars'):
                # It's an Environment - look up in its vars
                return obj.vars.get(node.name, node.name)

            if isinstance(obj, str):
                index = self._resolve_index(node.name)
                try:
                    return Char(obj[index])
                except IndexError:
                    raise Exception(f"Index {index} finns inte i texten {node.target}")

            if isinstance(obj, list):
                index = self._resolve_index(node.name)
                try:
                    return obj[index]
                except IndexError:
                    raise Exception(f"Index {index} finns inte i listan {node.target}")

            if isinstance(obj, dict):
                val = obj.get(node.name)

                if callable(val):
                    return val()

                return val if val is not None else node.name
        return self.env.get(node.name)

    def visit_AssignNode(self, node):
        value = self.visit(node.value)

        # List index assignment: sätt element 0 i lista till x
        if node.target_type:
            obj = self.env.get(node.target_type)
            if isinstance(obj, list):
                try:
                    obj[int(node.name)] = value
                    return value
                except (ValueError, IndexError):
                    raise Exception(f"Index {node.name} saknas i listan {node.target_type}")
            # Typ objects are now immutable - use 'kopia av' instead
            raise Exception(f"Typ {node.target_type} är oföränderlig. Använd 'kopia av' för att skapa en ny instans.")

        # Instantiate types (e.g. sätt p till person)
        try:
            if callable(value) and isinstance(node.value, VarAccessNode):
                value = value()
        except ReturnException as e:
            # Catch the return payload thrown by 'ge' and pass it back
            value = e.value

        self.env.define(node.name, value)
        return value

    # --- Stdout ---
    def visit_PrintNode(self, node):
        val = self.visit(node.value)
        # If val is a callable function (not a FunctionCallNode), convert to string
        if callable(val) and not isinstance(node.value, FunctionCallNode):
            val = str(val)
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
        for cond_block in node.conditions:
            if self.visit(cond_block.test):
                for s in cond_block.block: self.visit(s)
                return
        if node.else_block:
            for s in node.else_block: self.visit(s)

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

        func_name = str(node.name)
        current_file = os.path.basename(self.script_dir_stack[-1])

        # Resolve function reference...
        func = None
        if isinstance(node.name, VarAccessNode) and node.name.target:
            func_name = f"{node.name.target}.{node.name.name}"
            module_obj = self.env.get(node.name.target)
            
            # Support both dict and Environment for module access
            if isinstance(module_obj, dict):
                func = module_obj.get(node.name.name)
            elif hasattr(module_obj, 'vars'):
                # It's an Environment object - get from its vars
                func = module_obj.vars.get(node.name.name)
            else:
                func = None
        elif isinstance(node.name, VarAccessNode):
            # VarAccessNode without target - look up the name directly
            func_name = node.name.name
            raw_func = self.env.get(func_name)
            if isinstance(raw_func, str):
                func = self.env.get(raw_func)
            else:
                func = raw_func
        else:
            # Try to get the function directly from env
            raw_func = self.env.get(node.name)
            
            # If we got a string back, it means the function wasn't found directly
            # and env returned the name as a string - look up by that name
            if isinstance(raw_func, str):
                func = self.env.get(raw_func)
            else:
                func = raw_func

        if func and (callable(func) or hasattr(func, 'body')):
            # --- PUSH FUNCTION FRAME ---
            self.call_stack.append({
                "function": func_name,
                "file": current_file,
                "line": getattr(node, 'line', self.call_stack[-1]["line"] if self.call_stack else 1),
                "column": getattr(node, 'column', self.call_stack[-1]["column"] if self.call_stack else 1)
            })

            try:
                if callable(func):
                    return func(*args)
                return self.execute_hiuh_function(func, args)
            except ReturnException as e:
                # Catch the return payload thrown by 'ge' and pass it back
                return e.value
            finally:
                # --- POP FUNCTION FRAME ---
                # This try/finally strictly matches the execution life of the function call!
                self.call_stack.pop()
        
        # Function not found - stringify the call (e.g., "hälsa med David")
        args_str = ' '.join(str(a) for a in args)
        return f"{func_name} med {args_str}".strip()

    def execute_hiuh_function(self, func_node, args):
        """Executes a user-defined Hiuh-lang function in an isolated local environment."""
        # 1. Lexical Scope Isolation
        definition_env = getattr(func_node, 'closure_env', self.globals)
        local_env = Environment(definition_env)

        # 2. Bind parameter names to the evaluated runtime arguments
        if len(args) != len(func_node.params):
            raise Exception(
                f"Fel antal argument: Förväntade {len(func_node.params)}, "
                f"men fick {len(args)}."
            )

        for param_name, arg_value in zip(func_node.params, args):
            local_env.define(param_name, arg_value)

        # 3. Swap the active environment pointer to our new local scope
        old_env = self.env
        self.env = local_env

        try:
            # 4. Loop through and execute every statement in the function body
            for statement_node in func_node.body:
                # If your ReturnNode logic throws a custom Python exception to bubble up the value:
                self.visit(statement_node)

            return None # Default return value if 'ge' is omitted
        except ReturnException as e:
            return e.value # Extract value thrown via 'ge'
        finally:
            # 5. ALWAYS restore the parent execution environment pointer!
            self.env = old_env

    def visit_ExpressionPartsNode(self, node):
        """ExpressionPartsNode should always be transformed by resolver before interpreter runs."""
        raise Exception(f"Interpreter: ExpressionPartsNode was not transformed by resolver. Parts: {node.parts}")

    def visit_ReturnNode(self, node):
        return_value = self.visit(node.value)
        # Raise the exception to instantly halt the current execution frame loop
        raise ReturnException(return_value)

    def visit_ComparisonNode(self, node):
        l = self.visit(node.left)
        r = self.visit(node.right)
        op = node.op.strip()
        
        # Strip leading "är " if present (är is syntactic sugar)
        if op.startswith('är '):
            op = op[3:]

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

    def visit_InfixCallNode(self, node):
        # Evaluate left and right operands
        left_val = self.visit(node.left)
        right_val = self.visit(node.right)
        
        # Look up the infix function by name
        func = self.env.get(node.operator)
        
        # If func is a string, look it up
        if isinstance(func, str):
            func = self.env.get(func)
        
        if func is None:
            raise Exception(f"Infix function '{node.operator}' is not defined")
        
        # Call the function with left as first arg, right as second arg
        if hasattr(func, 'body'):
            # It's a hiuh function (FunctionDefNode stored in env)
            return self._call_hiuh_function(func, left_val, right_val)
        elif callable(func):
            # It's a Python function
            return func(left_val, right_val)
        else:
            raise Exception(f"'{node.operator}' is not callable")
    
    def _call_hiuh_function(self, func_node, arg1, arg2):
        """Call a hiuh function with two arguments."""
        if not hasattr(func_node, 'body'):
            raise Exception("Not a hiuh function")
        
        # Save current environment
        old_env = self.env
        
        # Create local environment with function scope
        local_env = Environment(old_env)
        
        # Bind parameters to arguments (first param = arg1, second param = arg2)
        params = func_node.params
        if len(params) >= 1:
            local_env.define(params[0], arg1)
        if len(params) >= 2:
            local_env.define(params[1], arg2)
        
        # Swap environment
        self.env = local_env
        
        try:
            for statement_node in func_node.body:
                self.visit(statement_node)
            return None
        except ReturnException as e:
            return e.value
        finally:
            self.env = old_env

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
        # Store constructor: takes field values and returns a dict with field names as keys
        def make_constructor(*args):
            result = {}
            for i, field in enumerate(node.fields):
                field_name = field.strip()
                result[field_name] = args[i] if i < len(args) else None
            return result
        self.env.define(node.name, make_constructor)

    def visit_CopyWithPropNode(self, node):
        """Handle 'sätt X till kopia av Y med P V, P V, P V' pattern.
        
        Creates a copy of source object Y with multiple properties updated.
        """
        source = self.env.get(node.source)
        
        # Make a shallow copy of the source
        if isinstance(source, dict):
            result = dict(source)
            for prop, val in node.updates:
                result[prop] = self.visit(val)
        elif isinstance(source, list):
            result = list(source)
            for prop, val in node.updates:
                # For lists, prop should be an index
                try:
                    idx = int(prop)
                    result[idx] = self.visit(val)
                except (ValueError, IndexError):
                    raise Exception(f"Kan inte uppdatera index {prop} i lista")
        else:
            raise Exception(f"Kan inte skapa kopia av '{node.source}' - okänt typ")
        
        self.env.define(node.name, result)
        return result

    def visit_CastNode(self, node):
        val = self.visit(node.value)
        target = node.target_type

        try:
            if target == "tecken":
                if isinstance(val, Char):
                    return val

                if 0 <= val <= 255:
                    return Char(chr(val))
                raise ValueError(f"ASCII-kod {val} är utanför giltigt intervall (0-255).")
            if target == "tal":
                if isinstance(val, Char):
                    return ord(val.value) if val.value else 0

                return int(float(str(val).replace(',', '.'))) # Handles "10" or "10,5"
            if target == "flyttal":
                return float(str(val).replace(',', '.'))
            if target == "text":
                return str(val)
            if target == "boolesk":
                return bool(val)
        except (ValueError, TypeError):
            raise Exception(f"Kunde inte omvandla '{val}' till {target}")

        raise Exception(f"Kunde inte omvandla '{val}' till {target}")

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
