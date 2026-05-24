# -*- coding: utf-8 -*-
from hiuh.frontend.tokenizer import Token


class ASTNode:
    def __init__(self, token: Token|None):
        self.line = token.line if token else None
        self.column = token.column if token else None

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
        super().__init__(token)
        self.value = int(value)

class FloatNode(ASTNode):
    def __init__(self, value, token=None):
        super().__init__(token)
        # Converts Swedish '3,4' to Python '3.4'
        self.value = float(str(value).replace(',', '.'))

class StringNode(ASTNode):
    def __init__(self, value, token=None):
        super().__init__(token)
        self.value = str(value)

class BoolNode(ASTNode):
    def __init__(self, value, token=None):
        super().__init__(token)
        self.value = bool(value)

# --- Variables & Access ---
class VarAccessNode(ASTNode):
    def __init__(self, name, target=None, token=None):
        super().__init__(token)
        self.name = name
        self.target = target

# --- Mathematical Operations ---
class AddNode(ASTNode):
    def __init__(self, left, right, token=None):
        super().__init__(token)
        self.left, self.right = left, right

class SubNode(ASTNode):
    def __init__(self, left, right, token=None):
        super().__init__(token)
        self.left, self.right = left, right

class MulNode(ASTNode):
    def __init__(self, left, right, token=None):
        super().__init__(token)
        self.left, self.right = left, right

class DivNode(ASTNode):
    def __init__(self, left, right, token=None):
        super().__init__(token)
        self.left, self.right = left, right

# --- Comparisons and Logic ---
class NotNode(ASTNode):
    def __init__(self, condition, token=None):
        super().__init__(token)
        self.condition = condition

class ComparisonNode(ASTNode):
    def __init__(self, left, op, right, token=None):
        super().__init__(token)
        self.left, self.op, self.right = left, op, right

class UnaryOpNode(ASTNode):
    def __init__(self, op: str, operand, token=None):
        super().__init__(token)
        self.op, self.operand = op, operand

# --- Statements ---
class AssignNode(ASTNode):
    def __init__(self, name, value, target_type=None, token=None):
        super().__init__(token)
        self.name = name
        self.value = value
        self.target_type = target_type  # Used for 'sätt x i person'

class PrintNode(ASTNode):
    def __init__(self, value, token=None):
        super().__init__(token)
        self.value = value

class IfNode(ASTNode):
    def __init__(self, condition, true_block, false_block=None, token=None):
        super().__init__(token)
        self.condition = condition
        self.true_block = true_block
        self.false_block = false_block

class WhileNode(ASTNode):
    def __init__(self, condition, body, token=None):
        super().__init__(token)
        self.condition = condition
        self.body = body

# --- Functions and Types ---
class FunctionDefNode(ASTNode):
    def __init__(self, params, body, token=None):
        super().__init__(token)
        self.params = params
        self.body = body

class FunctionCallNode(ASTNode):
    def __init__(self, name, args, token=None):
        super().__init__(token)
        self.name = name
        self.args = args

class TypeDefNode(ASTNode):
    def __init__(self, name, fields, token=None):
        super().__init__(token)
        self.name = name
        self.fields = fields

class ReturnNode(ASTNode):
    def __init__(self, value, token=None):
        super().__init__(token)
        self.value = value

# --- Error Handling & Packages ---
class TryCatchNode(ASTNode):
    def __init__(self, try_block, error_var, catch_block=None, finally_block=None, token=None):
        super().__init__(token)
        self.try_block = try_block
        self.error_var = error_var
        self.catch_block = catch_block
        self.finally_block = finally_block # NEW

class ImportNode(ASTNode):
    def __init__(self, module_name, alias=None, token=None):
        super().__init__(token)
        self.module_name = module_name
        self.alias = alias

class CastNode(ASTNode):
    def __init__(self, value, target_type, token=None):
        super().__init__(token)
        self.value = value
        self.target_type = target_type # 'heltal', 'text', 'flyttal'

class AppendNode(ASTNode):
    def __init__(self, value, target_list, token=None):
        super().__init__(token)
        self.value = value
        self.target_list = target_list

class RemoveIndexNode(ASTNode):
    def __init__(self, index, target_list, token=None):
        super().__init__(token)
        self.index = index
        self.target_list = target_list

class RemoveValueNode(ASTNode):
    def __init__(self, value, target_list, token=None):
        super().__init__(token)
        self.value = value
        self.target_list = target_list

class FileWriteNode(ASTNode):
    def __init__(self, value, target_var, token=None):
        super().__init__(token)
        self.value = value        # What to write (Expression)
        self.target_var = target_var # Variable holding the file object

class CloseFileNode(ASTNode):
    def __init__(self, target_var, token=None):
        super().__init__(token)
        self.target_var = target_var # Variable holding the file object
