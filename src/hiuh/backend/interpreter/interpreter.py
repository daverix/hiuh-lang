import os
import sys
from hiuh.frontend.ast import *
from hiuh.backend.interpreter.environment import Environment
from hiuh.frontend.module_registry import ModuleRegistry


class ReturnException(Exception):
    """Internal interpreter exception used to bubble return values out of nested scopes."""

    def __init__(self, value):
        self.value = value


class BreakException(Exception):
    """Internal interpreter exception used to break out of loops."""
    pass


class ContinueException(Exception):
    """Internal interpreter exception used to continue to next loop iteration."""
    pass


class Char:
    """Internal interpreter representation of a single character token byte."""

    def __init__(self, value: str):
        self.value = value

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
        self.module_registry = module_registry
        self.globals = Environment()
        self.globals.define("SANT", True)
        self.globals.define("FALSKT", False)
        self.globals.define("lista", lambda *args: list(args))
        self.globals.define("inmatning", lambda: sys.stdin.readline().strip())
        self.globals.define("längd", lambda x: len(x) if hasattr(x, '__len__') else 0)
        self.globals.define('element',
                            lambda idx, lst: lst[idx] if isinstance(lst, list) and 0 <= idx < len(lst) else None)
        self.globals.define("mellanrum", " ")
        self.globals.define("öppna", self.builtin_open)
        self.globals.define("öka", lambda x, v: x + v if isinstance(x, (int, float)) else str(x) + str(v))
        self.globals.define("minska", lambda x, v: x - v)
        self.globals.define("gångra", lambda x, v: x * v)
        self.globals.define("dela", lambda x, v: x / v)
        self.globals.define("ordlista", lambda: {})
        self.globals.define("putta", self.builtin_putta)
        self.globals.define("hämta", self.builtin_hämta)
        self.globals.define("finns", self.builtin_finns)
        self.globals.define("rensa", self.builtin_rensa)
        self._hiuhtyp_heltal = {"namn": "heltal", "föräldrar": [], "_typ": "hiuhtyp"}
        self._hiuhtyp_sträng = {"namn": "sträng", "föräldrar": [], "_typ": "hiuhtyp"}
        self._hiuhtyp_flyttal = {"namn": "flyttal", "föräldrar": [], "_typ": "hiuhtyp"}
        self._hiuhtyp_boolesk = {"namn": "boolesk", "föräldrar": [], "_typ": "hiuhtyp"}
        self.globals.define("heltal", self._hiuhtyp_heltal)
        self.globals.define("sträng", self._hiuhtyp_sträng)
        self.globals.define("flyttal", self._hiuhtyp_flyttal)
        self.globals.define("boolesk", self._hiuhtyp_boolesk)
        self._hiuhtyp_registry = {'heltal': self._hiuhtyp_heltal, 'sträng': self._hiuhtyp_sträng,
                                  'flyttal': self._hiuhtyp_flyttal, 'boolesk': self._hiuhtyp_boolesk,
                                  'lista': {'namn': 'lista', 'föräldrar': [], '_typ': 'hiuhtyp'},
                                  'ordlista': {'namn': 'ordlista', 'föräldrar': [], '_typ': 'hiuhtyp'},
                                  'hiuhtyp': {'namn': 'hiuhtyp', 'föräldrar': [], '_typ': 'hiuhtyp'},
                                  'BasNod': {'namn': 'BasNod', 'föräldrar': [], '_typ': 'hiuhtyp'},
                                  'SkrivNod': {'namn': 'SkrivNod',
                                               'föräldrar': [{'namn': 'BasNod', 'föräldrar': [], '_typ': 'hiuhtyp'}],
                                               '_typ': 'hiuhtyp'}, 'TilldelaNod': {'namn': 'TilldelaNod', 'föräldrar': [
                {'namn': 'BasNod', 'föräldrar': [], '_typ': 'hiuhtyp'}], '_typ': 'hiuhtyp'},
                                  'ReturNod': {'namn': 'ReturNod',
                                               'föräldrar': [{'namn': 'BasNod', 'föräldrar': [], '_typ': 'hiuhtyp'}],
                                               '_typ': 'hiuhtyp'}, 'BrytNod': {'namn': 'BrytNod', 'föräldrar': [
                {'namn': 'BasNod', 'föräldrar': [], '_typ': 'hiuhtyp'}], '_typ': 'hiuhtyp'},
                                  'FortsättNod': {'namn': 'FortsättNod',
                                                  'föräldrar': [{'namn': 'BasNod', 'föräldrar': [], '_typ': 'hiuhtyp'}],
                                                  '_typ': 'hiuhtyp'}, 'OmNod': {'namn': 'OmNod', 'föräldrar': [
                {'namn': 'BasNod', 'föräldrar': [], '_typ': 'hiuhtyp'}], '_typ': 'hiuhtyp'},
                                  'MedanNod': {'namn': 'MedanNod',
                                               'föräldrar': [{'namn': 'BasNod', 'föräldrar': [], '_typ': 'hiuhtyp'}],
                                               '_typ': 'hiuhtyp'}, 'BinärNod': {'namn': 'BinärNod', 'föräldrar': [
                {'namn': 'BasNod', 'föräldrar': [], '_typ': 'hiuhtyp'}], '_typ': 'hiuhtyp'},
                                  'ImporteraNod': {'namn': 'ImporteraNod', 'föräldrar': [
                                      {'namn': 'BasNod', 'föräldrar': [], '_typ': 'hiuhtyp'}], '_typ': 'hiuhtyp'},
                                  'StängFilNod': {'namn': 'StängFilNod',
                                                  'föräldrar': [{'namn': 'BasNod', 'föräldrar': [], '_typ': 'hiuhtyp'}],
                                                  '_typ': 'hiuhtyp'}, 'FunktionsDefNod': {'namn': 'FunktionsDefNod',
                                                                                          'föräldrar': [
                                                                                              {'namn': 'BasNod',
                                                                                               'föräldrar': [],
                                                                                               '_typ': 'hiuhtyp'}],
                                                                                          '_typ': 'hiuhtyp'},
                                  'SträngNod': {'namn': 'SträngNod',
                                                'föräldrar': [{'namn': 'BasNod', 'föräldrar': [], '_typ': 'hiuhtyp'}],
                                                '_typ': 'hiuhtyp'}, 'ÖkaNod': {'namn': 'ÖkaNod', 'föräldrar': [
                {'namn': 'BasNod', 'föräldrar': [], '_typ': 'hiuhtyp'}], '_typ': 'hiuhtyp'},
                                  'MinskaNod': {'namn': 'MinskaNod',
                                                'föräldrar': [{'namn': 'BasNod', 'föräldrar': [], '_typ': 'hiuhtyp'}],
                                                '_typ': 'hiuhtyp'}, 'GångraNod': {'namn': 'GångraNod', 'föräldrar': [
                {'namn': 'BasNod', 'föräldrar': [], '_typ': 'hiuhtyp'}], '_typ': 'hiuhtyp'},
                                  'DelaNod': {'namn': 'DelaNod',
                                              'föräldrar': [{'namn': 'BasNod', 'föräldrar': [], '_typ': 'hiuhtyp'}],
                                              '_typ': 'hiuhtyp'}}
        self.open_files = []
        self.call_stack = []
        self.file_stack = ["main"]
        self.script_dir_stack = [os.getcwd()]
        self.env = self.globals
        self.modules = {}
        self._module_exports = {}

    def execute(self, nodes):
        self.call_stack.append({'function': '<huvudprogram>', 'file': self.file_stack[-1], 'line': 1, 'column': 1})
        try:
            res = None
            for node in nodes:
                res = self.visit(node)
            return res
        except Exception as e:
            if hasattr(e, '_hiuh_call_stack'):
                self.print_hiuh_traceback(e._hiuh_call_stack, exception=e)
            raise e
        finally:
            self.call_stack.pop()

    def visit(self, node):
        if node is None:
            return None
        if hasattr(node, 'line') and node.line is not None:
            if self.call_stack:
                self.call_stack[-1]["line"] = node.line
                self.call_stack[-1]["column"] = getattr(node, 'column', 1)
        method = f"visit_{type(node).__name__}"
        visitor = getattr(self, method, self.no_visit_method)
        try:
            return visitor(node)
        except Exception as e:
            if not isinstance(e, (ReturnException, BreakException, ContinueException)):
                if not hasattr(e, '_hiuh_call_stack'):
                    e._hiuh_call_stack = list(self.call_stack)
            raise e

    def print_hiuh_traceback(self, call_stack=None, exception=None):
        """Prints a human-readable trace of the execution path when a crash happens."""
        import sys
        if exception is not None:
            print(f"\nFel: {exception}", file=sys.stderr)
        print("\n--- Spårningshistorik (Call Stack) ---", file=sys.stderr)
        stack = call_stack if call_stack is not None else self.call_stack
        for frame in reversed(stack):
            if frame["function"] == "<huvudprogram>" and frame["file"] == "run.py":
                continue
            file_name = frame["file"]
            module_path = None
            if self.modules and file_name in self.modules:
                module_path = self.modules[file_name].path
            elif self.module_registry and file_name in self.module_registry.modules:
                module_path = self.module_registry.modules[file_name].path
            if module_path and module_path != "<in_memory>":
                try:
                    from pathlib import Path
                    p = Path(module_path).absolute()
                    if p.is_file():
                        file_name = p.as_uri()
                except (ValueError, ImportError):
                    file_name = module_path
            col_info = f":{frame['column']}" if "column" in frame else ""
            print(f"{file_name}:{frame['line']}{col_info}: i funktion: {frame['function']}", file=sys.stderr)
        print("--------------------------------------\n", file=sys.stderr)

    def no_visit_method(self, node):
        raise Exception(f"Interpreter: visit_{type(node).__name__} is not implemented")

    def visit_ImportNode(self, node):
        """Handle resolved ImportNode by loading module from ModuleRegistry."""
        if not getattr(node, 'resolved', False):
            raise Exception(f"ImportNode for '{node.module_name}' is not resolved")
        if self.module_registry and node.module_name in self.module_registry.modules:
            module = self.module_registry.modules[node.module_name]
            if module.ast:
                prev_env = self.env
                module_env = Environment(prev_env)
                self.env = module_env
                self.file_stack.append(module.name)
                self.call_stack.append(
                    {'function': f'<modul:{module.name}>', 'file': module.name, 'line': 1, 'column': 1})
                try:
                    for stmt in module.ast:
                        if isinstance(stmt, ImportNode) and (not getattr(stmt, 'resolved', False)):
                            continue
                        self.visit(stmt)
                    if node.import_all:
                        for name, value in module_env.vars.items():
                            prev_env.define(name, value)
                    elif node.alias:
                        prev_env.define(node.alias, module_env)
                finally:
                    self.env = prev_env
                    self.call_stack.pop()
                    self.file_stack.pop()
        return None

    def visit_IntNode(self, node):
        return int(node.value)

    def visit_FloatNode(self, node):
        return float(node.value)

    def visit_BoolNode(self, node):
        return node.value

    def visit_StringNode(self, node):
        return node.value

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

    def visit_VarAccessNode(self, node):
        if node.target:
            obj = self.env.get(node.target)
            if hasattr(obj, 'value'):
                obj = obj.value
            if hasattr(obj, 'vars'):
                return obj.vars.get(node.name, node.name)
            if isinstance(obj, str):
                index = self._resolve_index(node.name)
                try:
                    return Char(obj[index])
                except IndexError:
                    raise Exception(f"Index {index} finns inte i texten {node.target}")
            if isinstance(obj, list):
                if node.name == 'längd':
                    return len(obj)
                elif node.name == 'element':
                    return obj
                elif node.name == 'index':
                    return obj
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

    def visit_ElementAccessNode(self, node):
        """Handle element access: element X from list"""
        target = self.visit(node.target)
        index = self.visit(node.index)
        if hasattr(target, 'value'):
            target = target.value
        if isinstance(target, list):
            if isinstance(index, int):
                idx = index
            elif isinstance(index, str):
                idx = int(index)
            else:
                idx = int(str(index))
            try:
                return target[idx]
            except IndexError:
                raise Exception(f"Index {idx} finns inte i listan")
        if isinstance(target, str):
            if isinstance(index, int):
                idx = index
            elif isinstance(index, str):
                idx = int(index)
            else:
                idx = int(str(index))
            try:
                return Char(target[idx])
            except IndexError:
                raise Exception(f"Index {idx} finns inte i texten")
        raise Exception(f"Kan inte komma åt element från {type(target).__name__}")

    def visit_ElementAssignNode(self, node):
        """Handle element assignment: sätt element X i list till value"""
        target = self.visit(node.target)
        index = self.visit(node.index)
        value = self.visit(node.value)
        if hasattr(target, 'value'):
            target = target.value
        if not isinstance(target, list):
            raise Exception(f"Kan inte sätta element i {type(target).__name__}")
        if isinstance(index, int):
            idx = index
        elif isinstance(index, str):
            idx = int(index)
        else:
            idx = int(str(index))
        target_name = None
        if isinstance(node.target, VarAccessNode):
            target_name = node.target.name
        list_obj = self.env.get(target_name)
        if hasattr(list_obj, 'value'):
            list_obj = list_obj.value
        if not isinstance(list_obj, list):
            raise Exception(f"Kan inte sätta element i {type(list_obj).__name__}")
        list_obj[idx] = value
        return value

    def visit_PropertyAccessNode(self, node):
        """Handle property access: property from object"""
        target = self.visit(node.target)
        prop_name = node.property_name
        if hasattr(target, 'value'):
            target = target.value
        if isinstance(target, list):
            if prop_name == 'längd':
                return len(target)
            elif prop_name == 'element':
                return target
            elif prop_name == 'index':
                return target
            raise Exception(f"Egenskap '{prop_name}' finns inte i listan")
        if isinstance(target, dict):
            val = target.get(prop_name)
            if callable(val):
                return val()
            return val if val is not None else prop_name
        if hasattr(target, 'vars'):
            val = target.vars.get(prop_name, prop_name)
            if callable(val):
                return val()
            return val
        if isinstance(target, str):
            if prop_name == 'längd':
                return len(target)
            raise Exception(f"Egenskap '{prop_name}' finns inte i text")
        raise Exception(f"Kan inte komma åt egenskap '{prop_name}' från {type(target).__name__}")

    def _is_defined_in_env(self, env, name):
        if name in env.vars:
            return True
        if env.parent:
            return self._is_defined_in_env(env.parent, name)
        return False

    def visit_AddAssignNode(self, node):
        if not self._is_defined_in_env(self.env, node.target):
            raise Exception(f"Variabeln '{node.target}' är inte definierad")
        current_val = self.env.get(node.target)
        value_to_add = self.visit(node.value)
        if isinstance(current_val, (int, float)) and isinstance(value_to_add, (int, float)):
            new_val = current_val + value_to_add
        else:
            new_val = str(current_val) + str(value_to_add)
        self.env.define(node.target, new_val)
        return new_val

    def visit_SubAssignNode(self, node):
        if not self._is_defined_in_env(self.env, node.target):
            raise Exception(f"Variabeln '{node.target}' är inte definierad")
        current_val = self.env.get(node.target)
        value_to_sub = self.visit(node.value)
        if not isinstance(current_val, (int, float)) or not isinstance(value_to_sub, (int, float)):
            raise Exception(f"Kan inte minska icke-numeriska värden ({current_val} och {value_to_sub})")
        new_val = current_val - value_to_sub
        self.env.define(node.target, new_val)
        return new_val

    def visit_MultiplyAssignNode(self, node):
        if not self._is_defined_in_env(self.env, node.target):
            raise Exception(f"Variabeln '{node.target}' är inte definierad")
        current_val = self.env.get(node.target)
        value_to_mul = self.visit(node.value)
        if isinstance(current_val, (int, float)) and isinstance(value_to_mul, (int, float)):
            new_val = current_val * value_to_mul
        elif isinstance(current_val, str) and isinstance(value_to_mul, int):
            new_val = current_val * value_to_mul
        else:
            raise Exception(
                f'Kan inte multiplicera värden av typ {type(current_val).__name__} och {type(value_to_mul).__name__}')
        self.env.define(node.target, new_val)
        return new_val

    def visit_DivideAssignNode(self, node):
        if not self._is_defined_in_env(self.env, node.target):
            raise Exception(f"Variabeln '{node.target}' är inte definierad")
        current_val = self.env.get(node.target)
        value_to_div = self.visit(node.value)
        if not isinstance(current_val, (int, float)) or not isinstance(value_to_div, (int, float)):
            raise Exception(f"Kan inte dividera icke-numeriska värden ({current_val} och {value_to_div})")
        if value_to_div == 0:
            raise Exception("Division med nolla är inte tillåten")
        new_val = current_val / value_to_div
        self.env.define(node.target, new_val)
        return new_val

    def visit_AssignNode(self, node):
        value = self.visit(node.value)
        if node.target_type:
            obj = self.env.get(node.target_type)
            if isinstance(obj, list):
                try:
                    obj[int(node.name)] = value
                    return value
                except (ValueError, IndexError):
                    raise Exception(f"Index {node.name} saknas i listan {node.target_type}")
            raise Exception(f"Typ {node.target_type} är oföränderlig. Använd 'kopia av' för att skapa en ny instans.")
        try:
            if callable(value) and isinstance(node.value, VarAccessNode):
                value = value()
        except ReturnException as e:
            value = e.value
        self.env.define(node.name, value)
        return value

    def visit_PrintNode(self, node):
        val = self.visit(node.value)
        if callable(val) and (not isinstance(node.value, FunctionCallNode)):
            val = str(val)
        if isinstance(val, bool):
            val = "SANT" if val else "FALSKT"
        sys.stdout.write(str(val))
        return val

    def visit_AddNode(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            return left + right
        return str(left) + str(right)

    def visit_SubNode(self, node):
        return self.visit(node.left) - self.visit(node.right)

    def visit_MulNode(self, node):
        return self.visit(node.left) * self.visit(node.right)

    def visit_DivNode(self, node):
        return self.visit(node.left) / self.visit(node.right)

    def visit_ModNode(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
            raise Exception(f"Kan inte utföra modulo på icke-numeriska värden ({left} och {right})")
        if right == 0:
            raise Exception("Division med nolla är inte tillåten")
        return left % right

    def visit_IfNode(self, node):
        for cond_block in node.conditions:
            if self.visit(cond_block.test):
                for s in cond_block.block:
                    self.visit(s)
                return
        if node.else_block:
            for s in node.else_block:
                self.visit(s)

    def visit_WhileNode(self, node):
        while self.visit(node.condition):
            try:
                for s in node.body:
                    self.visit(s)
            except BreakException:
                break
            except ContinueException:
                continue

    def visit_ForEachNode(self, node):
        """Execute a for-each loop: 'för varje X i <iterable> ...'"""
        iterable_val = self.visit(node.iterable)
        if isinstance(iterable_val, str):
            iterable_val = list(iterable_val)
        elif not isinstance(iterable_val, list):
            raise Exception(f"För varje kräver en lista eller text, inte {type(iterable_val).__name__}")
        for item in iterable_val:
            self.env.define(node.variable, item)
            try:
                for s in node.body:
                    self.visit(s)
            except BreakException:
                break
            except ContinueException:
                continue

    def visit_BreakNode(self, node):
        raise BreakException()

    def visit_ContinueNode(self, node):
        raise ContinueException()

    def visit_FunctionDefNode(self, node):
        closure = self.env

        def hiuh_func(*args, **kwargs):
            call_env = Environment(closure)
            for p, v in zip(node.params, args):
                name = p if isinstance(p, str) else p[0]
                call_env.define(name, v)
            param_names = [p if isinstance(p, str) else p[0] for p in node.params]
            for name, value in kwargs.items():
                if name in param_names:
                    call_env.define(name, value)
            prev_env = self.env
            self.env = call_env
            self.file_stack.append(hiuh_func._file)
            try:
                for s in node.body:
                    res = self.visit(s)
                    if isinstance(s, ReturnNode):
                        return res
            except ReturnException as e:
                return e.value
            finally:
                self.env = prev_env
                self.file_stack.pop()

        hiuh_func._file = self.file_stack[-1]
        return hiuh_func

    def visit_NamedArgNode(self, node):
        """Named argument - visit the value but keep the name."""
        return node

    def visit_FunctionCallNode(self, node):
        args = []
        named_kwargs = {}
        for arg in node.args:
            if isinstance(arg, NamedArgNode):
                named_kwargs[arg.name] = self.visit(arg.value)
            else:
                args.append(self.visit(arg))
        func_name = str(node.name)
        func = None
        if isinstance(node.name, VarAccessNode) and node.name.target:
            func_name = f"{node.name.target}.{node.name.name}"
            module_obj = self.env.get(node.name.target)
            if isinstance(module_obj, dict):
                func = module_obj.get(node.name.name)
            elif hasattr(module_obj, 'vars'):
                func = module_obj.vars.get(node.name.name)
            else:
                func = None
        elif isinstance(node.name, VarAccessNode):
            func_name = node.name.name
            raw_func = self.env.get(func_name)
            if isinstance(raw_func, str):
                func = self.env.get(raw_func)
            else:
                func = raw_func
        else:
            raw_func = self.env.get(node.name)
            if isinstance(raw_func, str):
                func = self.env.get(raw_func)
            else:
                func = raw_func
        if func and (callable(func) or hasattr(func, 'body')):
            func_file = getattr(func, '_file', self.file_stack[-1])
            self.call_stack.append({'function': func_name, 'file': func_file, 'line': getattr(node, 'line',
                                                                                              self.call_stack[-1][
                                                                                                  'line'] if self.call_stack else 1),
                                    'column': getattr(node, 'column',
                                                      self.call_stack[-1]['column'] if self.call_stack else 1)})
            try:
                if callable(func):
                    return func(*args, **named_kwargs)
                return self.execute_hiuh_function(func, args, named_kwargs)
            except ReturnException as e:
                return e.value
            finally:
                self.call_stack.pop()
        args_str = ' '.join((str(a) for a in args))
        return f"{func_name} med {args_str}".strip()

    def execute_hiuh_function(self, func_node, args, named_kwargs=None):
        """Executes a user-defined Hiuh-lang function in an isolated local environment."""
        if named_kwargs is None:
            named_kwargs = {}
        definition_env = getattr(func_node, 'closure_env', self.globals)
        local_env = Environment(definition_env)
        func_params = func_node.params if hasattr(func_node, 'params') else []
        if hasattr(func_node, 'fields'):
            fields = func_node.fields
            instance = {}
            for i, arg_value in enumerate(args):
                if i < len(fields):
                    instance[fields[i]] = arg_value
            for name, value in named_kwargs.items():
                if name in fields:
                    instance[name] = value
            return instance
        if len(args) != len(func_params):
            raise Exception(f'Fel antal argument: Förväntade {len(func_params)}, men fick {len(args)}.')
        for param_name, arg_value in zip(func_params, args):
            local_env.define(param_name, arg_value)
        for name, value in named_kwargs.items():
            if name in func_params:
                local_env.define(name, value)
        old_env = self.env
        self.env = local_env
        func_file = getattr(func_node, '_file', self.file_stack[-1])
        self.file_stack.append(func_file)
        try:
            for statement_node in func_node.body:
                self.visit(statement_node)
            return None
        except ReturnException as e:
            return e.value
        finally:
            self.env = old_env
            self.file_stack.pop()

    def visit_ExpressionPartsNode(self, node):
        """ExpressionPartsNode should always be transformed by resolver before interpreter runs."""
        raise Exception(f"Interpreter: ExpressionPartsNode was not transformed by resolver. Parts: {node.parts}")

    def visit_ReturnNode(self, node):
        return_value = self.visit(node.value)
        raise ReturnException(return_value)

    def visit_EqualNode(self, node):
        return self.visit(node.left) == self.visit(node.right)

    def visit_NotEqualNode(self, node):
        return self.visit(node.left) != self.visit(node.right)

    def visit_GreaterThanNode(self, node):
        return self.visit(node.left) > self.visit(node.right)

    def visit_LessThanNode(self, node):
        return self.visit(node.left) < self.visit(node.right)

    def visit_GreaterThanOrEqualNode(self, node):
        return self.visit(node.left) >= self.visit(node.right)

    def visit_LessThanOrEqualNode(self, node):
        return self.visit(node.left) <= self.visit(node.right)

    def visit_AndNode(self, node):
        return bool(self.visit(node.left)) and bool(self.visit(node.right))

    def visit_OrNode(self, node):
        return bool(self.visit(node.left)) or bool(self.visit(node.right))

    def visit_NotNode(self, node):
        return not bool(self.visit(node.condition))

    def visit_InfixCallNode(self, node):
        left_val = self.visit(node.left)
        right_val = self.visit(node.right)
        func = self.env.get(node.operator)
        if isinstance(func, str):
            func = self.env.get(func)
        if func is None and self.module_registry:
            for mod_name, mod_info in self.module_registry.modules.items():
                if hasattr(mod_info, 'symbols') and node.operator in mod_info.symbols:
                    sym = mod_info.symbols[node.operator]
                    if hasattr(sym, 'node') and sym.node:
                        func = sym.node
                        break
        if func is None:
            raise Exception(f"Infix function '{node.operator}' is not defined")
        if hasattr(func, 'body'):
            return self._call_hiuh_function(func, left_val, right_val)
        elif callable(func):
            return func(left_val, right_val)
        else:
            raise Exception(f"'{node.operator}' is not callable")

    def _call_hiuh_function(self, func_node, arg1, arg2):
        """Call a hiuh function with two arguments."""
        if not hasattr(func_node, 'body'):
            raise Exception("Not a hiuh function")
        old_env = self.env
        local_env = Environment(old_env)
        params = func_node.params
        if len(params) >= 1:
            local_env.define(params[0], arg1)
        if len(params) >= 2:
            local_env.define(params[1], arg2)
        self.env = local_env
        try:
            for statement_node in func_node.body:
                self.visit(statement_node)
            return None
        except ReturnException as e:
            return e.value
        finally:
            self.env = old_env

    def visit_TryCatchNode(self, node):
        old_env = self.env
        try:
            for s in node.try_block:
                self.visit(s)
        except Exception as e:
            self.env = Environment(old_env)
            val = getattr(e, 'value', str(e))
            self.env.define(node.error_var, val)
            for s in node.catch_block:
                self.visit(s)
        finally:
            if node.finally_block:
                for s in node.finally_block:
                    self.visit(s)
            self.env = old_env

    def visit_UnaryOpNode(self, node):
        if node.op == "kasta":
            val = self.visit(node.operand)
            err = Exception(val)
            err.value = val
            raise err

    def visit_TypeDefNode(self, node):
        all_fields = list(node.fields)
        seen_fields = set()
        if node.parent_types:
            for parent_name, _parent_params in reversed(node.parent_types):
                parent_cons = self.env.get(parent_name)
                if parent_cons and hasattr(parent_cons, '_fields'):
                    for f in parent_cons._fields:
                        fname = f if isinstance(f, str) else f[0]
                        if fname in seen_fields:
                            raise Exception(f"Fältet '{fname}' finns i flera ärvda typer för '{node.name}'")
                        seen_fields.add(fname)
                        all_fields.insert(0, f)
        for f in node.fields:
            fname = f if isinstance(f, str) else f[0]
            if fname in seen_fields:
                raise Exception(f"Fältet '{fname}' i '{node.name}' krockar med ärvt fält")

        def make_constructor(*args, **kwargs):
            result = {}
            for i, field in enumerate(all_fields):
                field_name = field if isinstance(field, str) else field[0]
                result[field_name] = args[i] if i < len(args) else None
            field_names = [f if isinstance(f, str) else f[0] for f in all_fields]
            for name, value in kwargs.items():
                if name in field_names:
                    result[name] = value
            result['_typ'] = node.name
            if node.parent_types:
                result['_föräldrar'] = [p[0] for p in node.parent_types]
            else:
                result['_föräldrar'] = []
            return result

        make_constructor._fields = all_fields
        self.env.define(node.name, make_constructor)
        parent_hiuhtyps = []
        if node.parent_types:
            for pn in [p[0] for p in node.parent_types]:
                if pn in self._hiuhtyp_registry:
                    parent_hiuhtyps.append(self._hiuhtyp_registry[pn])
        h = {"namn": node.name, "föräldrar": parent_hiuhtyps, "_typ": "hiuhtyp"}
        make_constructor._hiuhtyp = h
        self._hiuhtyp_registry[node.name] = h

    def visit_FunctionTypeNode(self, node):
        """grejtyp declaration — no-op at runtime, type info for resolver."""
        return None

    def visit_TypeOfNode(self, node):
        """typ av X — returns a hiuhtyp object with namn and föräldrar."""
        val = self.visit(node.value)
        if isinstance(val, dict) and '_typ' in val:
            type_name = val['_typ']
            cons = self.env.get(type_name)
            if cons and hasattr(cons, '_hiuhtyp'):
                return cons._hiuhtyp
            if type_name in self._hiuhtyp_registry:
                return self._hiuhtyp_registry[type_name]
            parent_names = val.get('_föräldrar', [])
            parents = []
            for pn in parent_names:
                if pn in self._hiuhtyp_registry:
                    parents.append(self._hiuhtyp_registry[pn])
                else:
                    parents.append({"namn": pn, "föräldrar": [], "_typ": "hiuhtyp"})
            return {"namn": type_name, "föräldrar": parents, "_typ": "hiuhtyp"}
        if isinstance(val, bool):
            type_name = "boolesk"
        elif isinstance(val, str) and val in ("SANT", "FALSKT"):
            type_name = "boolesk"
        elif isinstance(val, int):
            type_name = "heltal"
        elif isinstance(val, float):
            type_name = "flyttal"
        elif isinstance(val, str):
            type_name = "sträng"
        elif isinstance(val, list):
            type_name = "lista"
        elif callable(val):
            if hasattr(val, '_hiuhtyp'):
                return val._hiuhtyp
            type_name = "grej"
        else:
            type_name = "okänd"
        if type_name in self._hiuhtyp_registry:
            return self._hiuhtyp_registry[type_name]
        return {"namn": type_name, "föräldrar": [], "_typ": "hiuhtyp"}

    def visit_CopyWithPropNode(self, node):
        """Handle 'sätt X till kopia av Y med P V, P V, P V' pattern.
        
        Creates a copy of source object Y with multiple properties updated.
        """
        source = self.env.get(node.source)
        if isinstance(source, dict):
            result = dict(source)
            for prop, val in node.updates:
                result[prop] = self.visit(val)
        elif isinstance(source, list):
            result = list(source)
            for prop, val in node.updates:
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
                return int(float(str(val).replace(',', '.')))
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
            return None
        raise Exception(f"Kan inte ta bort från '{node.target_list}' för det är inte en lista.")

    def builtin_putta(self, key, value, target):
        """putta key, value till target — add entry to dict."""
        if not isinstance(target, dict):
            raise Exception(f"Kan inte putta i '{type(target).__name__}' för det är inte en ordlista.")
        target[key] = value
        return target

    def builtin_hämta(self, key, source):
        """hämta key från source — get value from dict."""
        if not isinstance(source, dict):
            raise Exception(f"Kan inte hämta från '{type(source).__name__}' för det är inte en ordlista.")
        if key not in source:
            raise Exception(f"Nyckeln '{key}' finns inte i ordlistan.")
        return source[key]

    def builtin_finns(self, key, source):
        """finns key i source — check if key exists in dict."""
        if not isinstance(source, dict):
            return False
        return key in source

    def builtin_rensa(self, key, target):
        """rensa key från target — remove entry from dict."""
        if not isinstance(target, dict):
            raise Exception(f"Kan inte rensa från '{type(target).__name__}' för det är inte en ordlista.")
        if key in target:
            del target[key]
        return target

    def builtin_open(self, path, mode_str="läsning"):
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
            state = {"last_line": None, "reached_end": False}

            def read_next_line():
                line = f.readline()
                if line == '':
                    state["reached_end"] = True
                    return ""
                return line.rstrip('\n')

            def check_is_end():
                if state["reached_end"]:
                    return True
                pos = f.tell()
                next_check = f.readline()
                f.seek(pos)
                if next_check == "":
                    state["reached_end"] = True
                    return True
                return False

            return {'_file_handle': f, 'läge': mode_str, 'nästa rad': read_next_line,
                    'gå till början': lambda: (f.seek(0), state.update({'reached_end': False})),
                    'gå till slutet': lambda: f.tell() >= os.fstat(f.fileno()).st_size, 'i slutet': check_is_end}
        except Exception as e:
            raise Exception(f"Kunde inte öppna {path} för {mode_str}: {e}")

    def visit_FileWriteNode(self, node):
        content = self.visit(node.value)
        file_obj = self.env.get(node.target_var)
        if isinstance(file_obj, dict) and "_file_handle" in file_obj:
            f = file_obj["_file_handle"]
            f.write(str(content) + '\n')
            f.flush()
            return content
        raise Exception(f"'{node.target_var}' är inte en öppen fil.")

    def visit_CloseFileNode(self, node):
        file_obj = self.env.get(node.target_var)
        if isinstance(file_obj, dict) and "_file_handle" in file_obj:
            f = file_obj["_file_handle"]
            f.close()
            if hasattr(self, 'open_files') and f in self.open_files:
                self.open_files.remove(f)
            return True
        raise Exception(f"'{node.target_var}' är inte en öppen fil.")
