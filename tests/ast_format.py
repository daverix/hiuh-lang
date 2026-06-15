"""Shared AST formatting for cross-backend test comparison."""
from hiuh.frontend.ast import *

def ast_to_string(node):
    """Convert an AST node to a canonical string for cross-backend comparison."""
    if isinstance(node, list):
        items = ', '.join((ast_to_string(n) for n in node))
        return "[" + items + "]"
    if isinstance(node, ExpressionPartsNode):
        if len(node.parts) == 1 and node.parts[0].value.isdigit():
            return f"IntNode({node.parts[0].value})"
        return "Expr(" + " ".join(p.value for p in node.parts) + ")"
    classname = type(node).__name__
    if isinstance(node, (IntNode, FloatNode)):
        return f"{classname}({node.value})"
    if isinstance(node, StringNode):
        return f"{classname}({repr(node.value)})"
    if isinstance(node, BoolNode):
        return f"{classname}({node.value})"
    if isinstance(node, VarAccessNode):
        return f"{classname}({node.name})"
    if isinstance(node, (BreakNode, ContinueNode)):
        return f"{classname}()"
    if isinstance(node, PrintNode):
        return f"{classname}({ast_to_string(node.value)})"
    if isinstance(node, ReturnNode):
        return f"{classname}({ast_to_string(node.value)})"
    if isinstance(node, AssignNode):
        return f"{classname}({node.name}, {ast_to_string(node.value)})"
    if isinstance(node, AddAssignNode):
        return f"{classname}({node.target}, {ast_to_string(node.value)})"
    if isinstance(node, SubAssignNode):
        return f"{classname}({node.target}, {ast_to_string(node.value)})"
    if isinstance(node, MultiplyAssignNode):
        return f"{classname}({node.target}, {ast_to_string(node.value)})"
    if isinstance(node, DivideAssignNode):
        return f"{classname}({node.target}, {ast_to_string(node.value)})"
    if isinstance(node, ImportNode):
        return f"{classname}({node.module_name})"
    if isinstance(node, CloseFileNode):
        return f"{classname}({node.target_var})"
    if isinstance(node, WhileNode):
        cond = ast_to_string(node.condition)
        body = ast_to_string(node.body)
        return f"{classname}({cond}, {body})"
    if isinstance(node, ForEachNode):
        return f"{classname}({node.variable}, {ast_to_string(node.iterable)}, {ast_to_string(node.body)})"
    if isinstance(node, IfNode):
        conds = ', '.join((f'IfCond({ast_to_string(c.test)}, {ast_to_string(c.block)})' for c in node.conditions))
        if node.else_block:
            conds += ", Else(" + ast_to_string(node.else_block) + ")"
        return f"IfNode({conds})"
    if isinstance(node, TryCatchNode):
        parts = [f"Try({ast_to_string(node.try_block)})"]
        if node.catch_block:
            parts.append(f"Catch({node.error_var!r}, {ast_to_string(node.catch_block)})")
        if node.finally_block:
            parts.append(f"Finally({ast_to_string(node.finally_block)})")
        return "TryCatchNode(" + ", ".join(parts) + ")"
    if isinstance(node, UnaryOpNode):
        return f"UnaryOpNode({node.op!r}, {ast_to_string(node.operand)})"
    if isinstance(node, FunctionDefNode):
        params = str(node.params)
        body = ast_to_string(node.body)
        kind = getattr(node, 'kind', 'grej')
        kind_str = f", kind={kind!r}" if kind and kind != 'grej' else ""
        ret = f", return_type={node.return_type!r}" if getattr(node, 'return_type', None) else ""
        return f"{classname}({params}, {body}{kind_str}{ret})"
    if isinstance(node, ElementAssignNode):
        return f"{classname}({ast_to_string(node.index)}, {ast_to_string(node.target)}, {ast_to_string(node.value)})"
    if isinstance(node, CopyWithPropNode):
        updates = ', '.join(f"('{k}', {ast_to_string(v)})" for k, v in node.updates)
        return f"{classname}({node.name!r}, {node.source!r}, [{updates}])"
    if isinstance(node, (AddNode, SubNode, MulNode, DivNode, ModNode, EqualNode, NotEqualNode, LessThanNode, GreaterThanNode, LessThanOrEqualNode, GreaterThanOrEqualNode)):
        return f"{classname}({ast_to_string(node.left)}, {ast_to_string(node.right)})"
    if isinstance(node, AndNode):
        return f"AndNode({ast_to_string(node.left)}, {ast_to_string(node.right)})"
    if isinstance(node, OrNode):
        return f"OrNode({ast_to_string(node.left)}, {ast_to_string(node.right)})"
    if isinstance(node, NotNode):
        return f"NotNode({ast_to_string(node.condition)})"
    if isinstance(node, CastNode):
        return f"CastNode({ast_to_string(node.value)}, {node.target_type!r})"
    if isinstance(node, TypeOfNode):
        return f"TypeOfNode({ast_to_string(node.value)})"
    if isinstance(node, PropertyAccessNode):
        return f"PropertyAccessNode({node.property_name!r}, {ast_to_string(node.target)})"
    if isinstance(node, ElementAccessNode):
        return f"ElementAccessNode({ast_to_string(node.index)}, {ast_to_string(node.target)})"
    if isinstance(node, InfixCallNode):
        return f"InfixCallNode({ast_to_string(node.left)}, {node.operator!r}, {ast_to_string(node.right)})"
    if isinstance(node, FunctionCallNode):
        args = ', '.join((ast_to_string(a) for a in node.args))
        return f"FunctionCallNode({node.name!r}, [{args}])"
    if isinstance(node, NamedArgNode):
        return f"NamedArgNode({node.name!r}, {ast_to_string(node.value)})"
    if isinstance(node, AppendNode):
        return f"AppendNode({ast_to_string(node.value)}, {node.target_list!r})"
    if isinstance(node, RemoveValueNode):
        return f"RemoveValueNode({ast_to_string(node.value)}, {node.target_list!r})"
    if isinstance(node, RemoveIndexNode):
        return f"RemoveIndexNode({ast_to_string(node.index)}, {node.target_list!r})"
    if isinstance(node, FunctionTypeNode):
        params = str(node.params)
        return f"FunctionTypeNode(name={node.name!r}, params={params}, return_type={node.return_type!r})"
    if isinstance(node, TypeDefNode):
        fields = ', '.join(repr(f) for f in node.fields)
        return f"TypeDefNode({node.name!r}, [{fields}])"
    return f"{classname}(...)"