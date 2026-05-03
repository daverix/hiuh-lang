class ASTNode:
    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return self.__dict__ == other.__dict__

    def __repr__(self):
        # Format: NodeName(attr1=val1, attr2=val2)
        attrs = ", ".join([f"{k}={v!r}" for k, v in self.__dict__.items()])
        return f"{self.__class__.__name__}({attrs})"

# --- Literals and Variables ---
class LiteralNode(ASTNode):
    def __init__(self, value, type):
        self.value = value
        self.type = type  # 'INT', 'FLOAT', 'BOOL', 'STRING'

class VarAccessNode(ASTNode):
    def __init__(self, name, source=None):
        self.name = name
        self.source = source  # Used for 'namn från p'

# --- Operations ---
class BinOpNode(ASTNode):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

class UnaryOpNode(ASTNode):
    def __init__(self, op, operand):
        self.op = op
        self.operand = operand

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
    def __init__(self, try_block, error_var, catch_block):
        self.try_block = try_block
        self.error_var = error_var
        self.catch_block = catch_block

class ImportNode(ASTNode):
    def __init__(self, module, alias=None):
        self.module = module
        self.alias = alias
