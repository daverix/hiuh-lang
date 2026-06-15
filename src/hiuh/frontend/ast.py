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
        attrs = ", ".join([f"{k}={v!r}" for k, v in self.__dict__.items()])
        return f"{self.__class__.__name__}({attrs})"

# --- Literals ---
class IntNode(ASTNode):
    def __init__(self, line, column, value):
        super().__init__(line, column)
        self.value = int(value)

class FloatNode(ASTNode):
    def __init__(self, line, column, value):
        super().__init__(line, column)
        self.value = float(str(value).replace(',', '.'))

class StringNode(ASTNode):
    def __init__(self, line, column, value):
        super().__init__(line, column)
        self.value = str(value)

class BoolNode(ASTNode):
    def __init__(self, line, column, value):
        super().__init__(line, column)
        self.value = bool(value)

# --- Variables & Access ---
class VarAccessNode(ASTNode):
    def __init__(self, line, column, name, target=None):
        super().__init__(line, column)
        self.name = name
        self.target = target

class ElementAccessNode(ASTNode):
    def __init__(self, line, column, index, target):
        super().__init__(line, column)
        self.index = index
        self.target = target

class ElementAssignNode(ASTNode):
    def __init__(self, line, column, index, target, value):
        super().__init__(line, column)
        self.index = index
        self.target = target
        self.value = value

class PropertyAccessNode(ASTNode):
    def __init__(self, line, column, property_name, target):
        super().__init__(line, column)
        self.property_name = property_name
        self.target = target

# --- Mathematical Operations ---
class AddNode(ASTNode):
    def __init__(self, line, column, left, right):
        super().__init__(line, column)
        self.left, self.right = left, right

class SubNode(ASTNode):
    def __init__(self, line, column, left, right):
        super().__init__(line, column)
        self.left, self.right = left, right

class MulNode(ASTNode):
    def __init__(self, line, column, left, right):
        super().__init__(line, column)
        self.left, self.right = left, right

class DivNode(ASTNode):
    def __init__(self, line, column, left, right):
        super().__init__(line, column)
        self.left, self.right = left, right

class ModNode(ASTNode):
    def __init__(self, line, column, left, right):
        super().__init__(line, column)
        self.left, self.right = left, right

# --- Comparisons and Logic ---
class NotNode(ASTNode):
    def __init__(self, line, column, condition):
        super().__init__(line, column)
        self.condition = condition

class EqualNode(ASTNode):
    def __init__(self, line, column, left, right):
        super().__init__(line, column)
        self.left, self.right = left, right

class NotEqualNode(ASTNode):
    def __init__(self, line, column, left, right):
        super().__init__(line, column)
        self.left, self.right = left, right

class GreaterThanNode(ASTNode):
    def __init__(self, line, column, left, right):
        super().__init__(line, column)
        self.left, self.right = left, right

class LessThanNode(ASTNode):
    def __init__(self, line, column, left, right):
        super().__init__(line, column)
        self.left, self.right = left, right

class GreaterThanOrEqualNode(ASTNode):
    def __init__(self, line, column, left, right):
        super().__init__(line, column)
        self.left, self.right = left, right

class LessThanOrEqualNode(ASTNode):
    def __init__(self, line, column, left, right):
        super().__init__(line, column)
        self.left, self.right = left, right

class AndNode(ASTNode):
    def __init__(self, line, column, left, right):
        super().__init__(line, column)
        self.left, self.right = left, right

class OrNode(ASTNode):
    def __init__(self, line, column, left, right):
        super().__init__(line, column)
        self.left, self.right = left, right

ComparisonNodes = (EqualNode, NotEqualNode, GreaterThanNode, LessThanNode, GreaterThanOrEqualNode, LessThanOrEqualNode, AndNode, OrNode)

class UnaryOpNode(ASTNode):
    def __init__(self, line, column, op: str, operand):
        super().__init__(line, column)
        self.op, self.operand = op, operand

# --- Statements ---
class AssignNode(ASTNode):
    def __init__(self, line, column, name, value, target_type=None):
        super().__init__(line, column)
        self.name = name
        self.value = value
        self.target_type = target_type

class AddAssignNode(ASTNode):
    def __init__(self, line, column, target, value):
        super().__init__(line, column)
        self.target = target
        self.value = value

class SubAssignNode(ASTNode):
    def __init__(self, line, column, target, value):
        super().__init__(line, column)
        self.target = target
        self.value = value

class MultiplyAssignNode(ASTNode):
    def __init__(self, line, column, target, value):
        super().__init__(line, column)
        self.target = target
        self.value = value

class DivideAssignNode(ASTNode):
    def __init__(self, line, column, target, value):
        super().__init__(line, column)
        self.target = target
        self.value = value

class PrintNode(ASTNode):
    def __init__(self, line, column, value):
        super().__init__(line, column)
        self.value = value

class IfCondition(ASTNode):
    def __init__(self, line, column, test, block):
        super().__init__(line, column)
        self.test = test
        self.block = block

class IfNode(ASTNode):
    def __init__(self, line, column, conditions, else_block=None):
        super().__init__(line, column)
        self.conditions = conditions
        self.else_block = else_block

class WhileNode(ASTNode):
    def __init__(self, line, column, condition, body):
        super().__init__(line, column)
        self.condition = condition
        self.body = body

class BreakNode(ASTNode):
    def __init__(self, line, column):
        super().__init__(line, column)

class ContinueNode(ASTNode):
    def __init__(self, line, column):
        super().__init__(line, column)

# --- Functions and Types ---
class FunctionDefNode(ASTNode):
    def __init__(self, line, column, params, body, return_type, type_params=None, kind='grej'):
        super().__init__(line, column)
        self.params = params
        self.body = body
        self.type_params = type_params or []
        self.kind = kind
        self.return_type = return_type

    @property
    def is_infix(self):
        return self.kind == 'infix'

    def get_param_types(self):
        result = {}
        for p in self.params:
            if isinstance(p, tuple):
                name, type_name = p
                result[name] = type_name
        return result

    def get_param_names(self):
        return [p if isinstance(p, str) else p[0] for p in self.params]

class FunctionCallNode(ASTNode):
    def __init__(self, line, column, name, args):
        super().__init__(line, column)
        self.name = name
        self.args = args

class NamedArgNode(ASTNode):
    def __init__(self, line, column, name, value):
        super().__init__(line, column)
        self.name = name
        self.value = value

class InfixCallNode(ASTNode):
    def __init__(self, line, column, left, operator, right):
        super().__init__(line, column)
        self.left = left
        self.operator = operator
        self.right = right

class TypeDefNode(ASTNode):
    def __init__(self, line, column, name, fields, type_params=None, parent_types=None):
        super().__init__(line, column)
        self.name = name
        self.fields = fields
        self.type_params = type_params or []
        self.parent_types = parent_types or []

    def get_field_types(self):
        result = {}
        for f in self.fields:
            if isinstance(f, tuple):
                name, type_name = f
                result[name] = type_name
        return result

    def get_field_names(self):
        return [f if isinstance(f, str) else f[0] for f in self.fields]

class ReturnNode(ASTNode):
    def __init__(self, line, column, value):
        super().__init__(line, column)
        self.value = value

# --- Error Handling & Packages ---
class TryCatchNode(ASTNode):
    def __init__(self, line, column, try_block, error_var, catch_block=None, finally_block=None):
        super().__init__(line, column)
        self.try_block = try_block
        self.error_var = error_var
        self.catch_block = catch_block
        self.finally_block = finally_block

class ForEachNode(ASTNode):
    def __init__(self, line, column, variable, iterable, body):
        super().__init__(line, column)
        self.variable = variable
        self.iterable = iterable
        self.body = body

class ImportNode(ASTNode):
    def __init__(self, line, column, module_name, alias=None, import_all=False, resolved=False):
        super().__init__(line, column)
        self.module_name = module_name
        self.alias = alias
        self.import_all = import_all
        self.resolved = resolved

class CastNode(ASTNode):
    def __init__(self, line, column, value, target_type):
        super().__init__(line, column)
        self.value = value
        self.target_type = target_type

class TypeOfNode(ASTNode):
    def __init__(self, line, column, value):
        super().__init__(line, column)
        self.value = value

class AppendNode(ASTNode):
    def __init__(self, line, column, value, target_list):
        super().__init__(line, column)
        self.value = value
        self.target_list = target_list

class RemoveIndexNode(ASTNode):
    def __init__(self, line, column, index, target_list):
        super().__init__(line, column)
        self.index = index
        self.target_list = target_list

class RemoveValueNode(ASTNode):
    def __init__(self, line, column, value, target_list):
        super().__init__(line, column)
        self.value = value
        self.target_list = target_list

class FileWriteNode(ASTNode):
    def __init__(self, line, column, value, target_var):
        super().__init__(line, column)
        self.value = value
        self.target_var = target_var

class CloseFileNode(ASTNode):
    def __init__(self, line, column, target_var):
        super().__init__(line, column)
        self.target_var = target_var

class CopyWithPropNode(ASTNode):
    def __init__(self, line, column, name, source, updates):
        super().__init__(line, column)
        self.name = name
        self.source = source
        self.updates = updates

class ExpressionPart:
    """A single part in an expression, with original token type for disambiguation."""
    def __init__(self, value, token_type, line=None, column=None):
        self.value = value
        self.token_type = token_type
        self.line = line
        self.column = column

    def __repr__(self):
        return f"ExpressionPart({self.value!r}, type={self.token_type})"


class ExpressionPartsNode(ASTNode):
    """Generic expression node that stores a list of parts to be resolved later."""
    def __init__(self, line, column, parts):
        super().__init__(line, column)
        for p in parts:
            if not isinstance(p, ExpressionPart):
                raise TypeError(f"ExpressionPartsNode parts must be ExpressionPart, got {type(p).__name__}: {p!r}")
        self.parts = parts


class FunctionTypeNode(ASTNode):
    """Function type declaration: grejtyp namn med params ger returtyp"""
    def __init__(self, line, column, name, params, return_type):
        super().__init__(line, column)
        self.name = name
        self.params = params
        self.return_type = return_type
