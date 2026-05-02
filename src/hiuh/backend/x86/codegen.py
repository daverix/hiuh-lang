from typing import Any, Dict, List

class CodeGenerator:
    """
    Generates machine code or optimized intermediate representation (IR) 
    from an Abstract Syntax Tree (AST) representation.
    """
    def __init__(self, ast: Dict[str, Any]):
        self.ast = ast
        self.code_output: List[str] = []
        self.current_scope_vars: Dict[str, int] = {}
        self.line_number = 1

    def generate(self) -> List[str]:
        """
        Starts the generation process by traversing the root of the AST.
        """
        self.code_output = []
        self.generate_statement(self.ast)
        return self.code_output

    def _emit(self, instruction: str):
        """Helper function to write a line of assembled code."""
        self.code_output.append(f"{instruction.ljust(20)};")

    def generate_statement(self, statement: Dict[str, Any]):
        """
        Dispatches generation logic based on the type of statement.
        """
        stmt_type = statement.get("type")

        if stmt_type == "ASSIGNMENT":
            # Logic for variable assignment: var = expression
            var_name = statement["target"]
            expr = statement["value"]
            
            # 1. Allocate space for 'var_name'
            # 2. Recursively generate code for the expression
            # 3. Emit the STORE instruction
            self._emit(f"LOAD_VAL {var_name}")
            self.generate_statement(expr)

        elif stmt_type == "FUNCTION_CALL":
            # Logic for calling a function: func(args)
            func_name = statement["function"]
            args = statement["arguments"]
            
            self._emit(f"PUSH_ARGS")
            for arg in args:
                self.generate_statement(arg)
            
            self._emit(f"CALL {func_name}")

        elif stmt_type == "BLOCK":
            # Logic for blocks of statements (scope handling)
            for statement in statement["statements"]:
                self.generate_statement(statement)
        
        elif stmt_type == "RETURN":
            # Handle return statement
            return_value = statement["value"]
            self._emit(f"LOAD_VAL RETURN_VAL")
            self.generate_statement(return_value)

        else:
            self._emit(f"UNKNOWN_STATEMENT_TYPE({stmt_type})")

    def generate_expression(self, expression: Dict[str, Any]):
        """
        Generates code for an expression (e.g., arithmetic operations, variable lookups).
        """
        expr_type = expression.get("type")

        if expr_type == "BINARY_OP":
            # Logic: Left OP Right (Left must be evaluated first)
            left: Any = expression["left"]
            op: str = expression["operator"]
            right: Any = expression["right"]
            
            self.generate_expression(left)
            self._emit(f"OP_CODE {op}")
            self.generate_expression(right)

        elif expr_type == "VARIABLE_LOOKUP":
            # Placeholder: Simulates loading a variable value
            var_name = expression["variable"]
            self._emit(f"LOAD_VAL {var_name}")

        elif expr_type == "LITERAL":
            # Placeholder: Simulates loading a constant value
            value = expression["value"]
            self._emit(f"PUSH_CONST {value}")

# --- Sample Usage ---

def build_example_ast() -> Dict[str, Any]:
    """
    Builds a simplified AST representing:
    result = (a * 5) + constant_b
    """
    return {
        "type": "ASSIGNMENT",
        "target": "result",
        "value": {
            "type": "BINARY_OP",
            "left": {
                "type": "BINARY_OP",
                "left": {"type": "VARIABLE_LOOKUP", "variable": "a"},
                "operator": "*",
                "right": {"type": "LITERAL", "value": 5},
            },
            "operator": "+",
            "right": {"type": "LITERAL", "value": "constant_b"}
        }
    }

def generate_code_example():
    """
    Demonstrates the code generation process.
    """
    print("=======================================================")
    print("--- Code Generation Example ---")
    print("Original AST structure represents: result = (a * 5) + 'constant_b'")
    print("=======================================================")

    # 1. Build the AST
    test_ast = build_example_ast()
    
    # 2. Initialize and run the generator
    generator = CodeGenerator(test_ast)
    generated_code = generator.generate()

    # 3. Output the results
    print("\\n".join(generated_code))
    print("=======================================================")
    print("Code generation successful.")


if __name__ == "__main__":
    generate_code_example()