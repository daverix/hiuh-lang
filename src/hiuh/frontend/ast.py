# -*- coding: utf-8 -*-


class ASTNode:
    def __init__(self, line: int|None = None, column: int|None = None):
        self.line = line
        self.column = column

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return self.__dict__ == other.__dict__

    def __repr__(self):
        # Format: NodeName(attr1=val1, ...)
        attrs = ", ".join([f"{k}={v!r}" for k, v in self.__dict__.items()])
        return f"{self.__class__.__name__}({attrs})"

# --- Literals ---
class IntNode(ASTNode):
    def __init__(self, value, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.value = int(value)

class FloatNode(ASTNode):
    def __init__(self, value, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.value = float(str(value).replace(',', '.'))

class StringNode(ASTNode):
    def __init__(self, value, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.value = str(value)

class BoolNode(ASTNode):
    def __init__(self, value, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.value = bool(value)

# --- Variables & Access ---
class VarAccessNode(ASTNode):
    def __init__(self, name, target=None, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.name = name
        self.target = target

class ElementAccessNode(ASTNode):
    def __init__(self, index, target, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.index = index  # Can be IntNode or VarAccessNode
        self.target = target  # The list being accessed

class ElementAssignNode(ASTNode):
    def __init__(self, index, target, value, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.index = index  # Can be IntNode or VarAccessNode
        self.target = target  # The list being modified
        self.value = value  # The value to set

class PropertyAccessNode(ASTNode):
    def __init__(self, property_name, target, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.property_name = property_name  # e.g., "längd"
        self.target = target  # The object being accessed

# --- Mathematical Operations ---
class AddNode(ASTNode):
    def __init__(self, left, right, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.left, self.right = left, right

class SubNode(ASTNode):
    def __init__(self, left, right, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.left, self.right = left, right

class MulNode(ASTNode):
    def __init__(self, left, right, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.left, self.right = left, right

class DivNode(ASTNode):
    def __init__(self, left, right, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.left, self.right = left, right

class ModNode(ASTNode):
    def __init__(self, left, right, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.left, self.right = left, right

# --- Comparisons and Logic ---
class NotNode(ASTNode):
    def __init__(self, condition, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.condition = condition

class EqualNode(ASTNode):
    def __init__(self, left, right, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.left, self.right = left, right

class NotEqualNode(ASTNode):
    def __init__(self, left, right, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.left, self.right = left, right

class GreaterThanNode(ASTNode):
    def __init__(self, left, right, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.left, self.right = left, right

class LessThanNode(ASTNode):
    def __init__(self, left, right, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.left, self.right = left, right

class GreaterThanOrEqualNode(ASTNode):
    def __init__(self, left, right, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.left, self.right = left, right

class LessThanOrEqualNode(ASTNode):
    def __init__(self, left, right, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.left, self.right = left, right

class AndNode(ASTNode):
    def __init__(self, left, right, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.left, self.right = left, right

class OrNode(ASTNode):
    def __init__(self, left, right, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.left, self.right = left, right

ComparisonNodes = (EqualNode, NotEqualNode, GreaterThanNode, LessThanNode, GreaterThanOrEqualNode, LessThanOrEqualNode, AndNode, OrNode)

class UnaryOpNode(ASTNode):
    def __init__(self, op: str, operand, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.op, self.operand = op, operand

# --- Statements ---
class AssignNode(ASTNode):
    def __init__(self, name, value, target_type=None, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.name = name
        self.value = value
        self.target_type = target_type  # Used for 'sätt x i person'

class AddAssignNode(ASTNode):
    def __init__(self, target, value, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.target = target
        self.value = value

class SubAssignNode(ASTNode):
    def __init__(self, target, value, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.target = target
        self.value = value

class MultiplyAssignNode(ASTNode):
    def __init__(self, target, value, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.target = target
        self.value = value

class DivideAssignNode(ASTNode):
    def __init__(self, target, value, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.target = target
        self.value = value

class PrintNode(ASTNode):
    def __init__(self, value, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.value = value

class IfCondition(ASTNode):
    def __init__(self, test, block, line=None, column=None):
        super().__init__(line, column)
        self.test = test
        self.block = block

class IfNode(ASTNode):
    def __init__(self, conditions, else_block=None, line=None, column=None):
        super().__init__(line, column)
        self.conditions = conditions  # List of IfCondition nodes
        self.else_block = else_block

class WhileNode(ASTNode):
    def __init__(self, condition, body, line=None, column=None):
        super().__init__(line, column)
        self.condition = condition
        self.body = body

class BreakNode(ASTNode):
    def __init__(self, token=None):
        super().__init__(token.line if token else None, token.column if token else None)

class ContinueNode(ASTNode):
    def __init__(self, token=None):
        super().__init__(token.line if token else None, token.column if token else None)

# --- Functions and Types ---
class FunctionDefNode(ASTNode):
    def __init__(self, params, body, return_type, line=None, column=None, is_infix=False, type_params=None, kind=None):
        super().__init__(line, column)
        self.params = params
        self.body = body
        self.is_infix = is_infix
        self.type_params = type_params or []
        self.kind = kind if kind is not None else ('infix' if is_infix else 'grej')
        self.return_type = return_type  # str or None

    def get_param_types(self):
        """Return a dict mapping param name -> type name (only for typed params)."""
        result = {}
        for p in self.params:
            if isinstance(p, tuple):
                name, type_name = p
                result[name] = type_name
        return result

    def get_param_names(self):
        """Return a list of just the parameter names."""
        return [p if isinstance(p, str) else p[0] for p in self.params]

class FunctionCallNode(ASTNode):
    def __init__(self, name, args, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.name = name
        self.args = args

class NamedArgNode(ASTNode):
    """Represents a named argument in a function call: name=value"""
    def __init__(self, name, value, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.name = name
        self.value = value

class InfixCallNode(ASTNode):
    def __init__(self, left, operator, right, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.left = left
        self.operator = operator
        self.right = right

class TypeDefNode(ASTNode):
    def __init__(self, name, fields, token=None, type_params=None,
                 parent_types=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.name = name
        # fields is a list of either:
        # - strings (legacy untyped syntax)
        # - (name, type) tuples (new typed syntax)
        self.fields = fields
        # type_params is a list of type parameter names (e.g. ['T', 'U'] for generics)
        self.type_params = type_params or []
        # parent_types: list of (name, type_params) tuples for inherited types
        # e.g. [("fordon", []), ("lista av par", ["K", "V"])]
        self.parent_types = parent_types or []

    def get_field_types(self):
        """Return a dict mapping field name -> type name (only for typed fields)."""
        result = {}
        for f in self.fields:
            if isinstance(f, tuple):
                name, type_name = f
                result[name] = type_name
        return result

    def get_field_names(self):
        """Return a list of just the field names."""
        return [f if isinstance(f, str) else f[0] for f in self.fields]

class ReturnNode(ASTNode):
    def __init__(self, value, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.value = value

# --- Error Handling & Packages ---
class TryCatchNode(ASTNode):
    def __init__(self, try_block, error_var, catch_block=None, finally_block=None, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.try_block = try_block
        self.error_var = error_var
        self.catch_block = catch_block
        self.finally_block = finally_block

class ForEachNode(ASTNode):
    def __init__(self, variable, iterable, body, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.variable = variable  # string: loop variable name
        self.iterable = iterable  # ASTNode: expression returning a list
        self.body = body  # list[ASTNode]: block to execute

class ImportNode(ASTNode):
    def __init__(self, module_name, alias=None, import_all=False, resolved=False, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.module_name = module_name
        self.alias = alias
        self.import_all = import_all
        self.resolved = resolved  # False by default, set True by resolver

class CastNode(ASTNode):
    def __init__(self, value, target_type, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.value = value
        self.target_type = target_type

class TypeOfNode(ASTNode):
    """typ av expression: returns the type name of a value as a string."""
    def __init__(self, value, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.value = value

class AppendNode(ASTNode):
    def __init__(self, value, target_list, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.value = value
        self.target_list = target_list

class RemoveIndexNode(ASTNode):
    def __init__(self, index, target_list, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.index = index
        self.target_list = target_list

class RemoveValueNode(ASTNode):
    def __init__(self, value, target_list, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.value = value
        self.target_list = target_list

class FileWriteNode(ASTNode):
    def __init__(self, value, target_var, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.value = value
        self.target_var = target_var

class CloseFileNode(ASTNode):
    def __init__(self, target_var, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.target_var = target_var

class CopyWithPropNode(ASTNode):
    """Node for 'sätt X till kopia av Y med P V, P V, P V' pattern.
    
    Creates a copy of an object with multiple properties updated.
    """
    def __init__(self, name, source, updates, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.name = name          # The new variable name (X)
        self.source = source     # The source object (Y)
        self.updates = updates    # List of (prop_name, value) tuples

class ExpressionPartsNode(ASTNode):
    """Generic expression node that stores a list of parts to be resolved later.
    
    Parser creates this for any sequence like 'frukt innehåller banan'.
    Resolver transforms it to the correct node type based on context.
    """
    def __init__(self, parts, token=None):
        super().__init__(token.line if token else None, token.column if token else None)
        self.parts = parts