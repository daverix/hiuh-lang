# -*- coding: utf-8 -*-

class ASTNode:
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
    def __init__(self, value):
        self.value = int(value)

class FloatNode(ASTNode):
    def __init__(self, value):
        # Converts Swedish '3,4' to Python '3.4'
        self.value = float(str(value).replace(',', '.'))

class StringNode(ASTNode):
    def __init__(self, value):
        self.value = str(value)

class BoolNode(ASTNode):
    def __init__(self, value):
        self.value = bool(value)

# --- Variables & Access ---
class VarAccessNode(ASTNode):
    def __init__(self, name, target=None):
        self.name = name
        self.target = target

# --- Mathematical Operations ---
class AddNode(ASTNode):
    def __init__(self, left, right):
        self.left, self.right = left, right

class SubNode(ASTNode):
    def __init__(self, left, right):
        self.left, self.right = left, right

class MulNode(ASTNode):
    def __init__(self, left, right):
        self.left, self.right = left, right

class DivNode(ASTNode):
    def __init__(self, left, right):
        self.left, self.right = left, right

# --- Comparisons and Logic ---
class NotNode(ASTNode):
    def __init__(self, condition):
        self.condition = condition

class ComparisonNode(ASTNode):
    def __init__(self, left, op, right):
        self.left, self.op, self.right = left, op, right

class UnaryOpNode(ASTNode):
    def __init__(self, op, operand):
        self.op, self.operand = op, operand

# --- Statements ---
class AssignNode(ASTNode):
    def __init__(self, name, value, target_type=None):
        self.name = name
        self.value = value
        self.target_type = target_type  # Used for 'sätt x i person'

class PrintNode(ASTNode):
    def __init__(self, value):
        self.value = value

class IfNode(ASTNode):
    def __init__(self, condition, true_block, false_block=None):
        self.condition = condition
        self.true_block = true_block
        self.false_block = false_block

class WhileNode(ASTNode):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

# --- Functions and Types ---
class FunctionDefNode(ASTNode):
    def __init__(self, params, body):
        self.params = params
        self.body = body

class FunctionCallNode(ASTNode):
    def __init__(self, name, args):
        self.name = name
        self.args = args

class TypeDefNode(ASTNode):
    def __init__(self, name, fields):
        self.name = name
        self.fields = fields

class ReturnNode(ASTNode):
    def __init__(self, value):
        self.value = value

# --- Error Handling & Packages ---
class TryCatchNode(ASTNode):
    def __init__(self, try_block, error_var, catch_block=None, finally_block=None):
        self.try_block = try_block
        self.error_var = error_var
        self.catch_block = catch_block
        self.finally_block = finally_block # NEW

class ImportNode(ASTNode):
    def __init__(self, module_name, alias=None):
        self.module_name = module_name
        self.alias = alias

class CastNode(ASTNode):
    def __init__(self, value, target_type):
        self.value = value
        self.target_type = target_type # 'heltal', 'text', 'flyttal'

class AppendNode(ASTNode):
    def __init__(self, value, target_list):
        self.value = value
        self.target_list = target_list

class RemoveIndexNode(ASTNode):
    def __init__(self, index, target_list):
        self.index = index
        self.target_list = target_list

class RemoveValueNode(ASTNode):
    def __init__(self, value, target_list):
        self.value = value
        self.target_list = target_list

class FileWriteNode(ASTNode):
    def __init__(self, value, target_var):
        self.value = value        # What to write (Expression)
        self.target_var = target_var # Variable holding the file object

class CloseFileNode(ASTNode):
    def __init__(self, target_var):
        self.target_var = target_var # Variable holding the file object
