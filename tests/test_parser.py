"""Parser tests - tests raw parser output without resolver transformation.

TestPythonParser: uses Python Tokenizer+Parser
TestHiuhParser: uses hiuh tokeniserare+parser via interpreter
"""
import os
import unittest

from hiuh.frontend.ast import *
from hiuh.frontend.parser import Parser
from hiuh.frontend.tokenizer import Tokenizer
from tests.ast_format import ast_to_string


class _StringWrapper:
    """Wraps a string so it can be compared with AST nodes via _ast_to_string."""
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return self.value

class _BaseParserTests:
    """Mixin with parser tests. Subclasses provide parse(source)."""

    def parse(self, source):
        raise NotImplementedError

    def assertParseEqual(self, source, expected_ast_nodes):
        """Assert parse(source) matches expected AST nodes.

        expected_ast_nodes can be a list of AST nodes (Python backend)
        or a list of _StringWrapper (Hiuh backend).
        """
        actual = self.parse(source)
        if isinstance(actual, list) and actual and isinstance(actual[0], _StringWrapper):
            # Hiuh backend: compare strings
            actual_strs = [w.value for w in actual]
            expected_strs = [ast_to_string(n) for n in expected_ast_nodes]
            self.assertEqual(actual_strs, expected_strs)
        else:
            # Python backend: compare AST objects (strip locations)
            actual_stripped = self._strip_locations(actual)
            expected_stripped = self._strip_locations(expected_ast_nodes)
            self.assertEqual(actual_stripped, expected_stripped)

    def _strip_locations(self, node):
        if isinstance(node, list):
            return [self._strip_locations(child) for child in node]
        if isinstance(node, ExpressionPart):
            return str(node)
        if not hasattr(node, '__dict__'):
            return node
        result = {}
        for key, value in node.__dict__.items():
            if key in ('line', 'column', 'token', 'kind'):
                continue
            result[key] = self._strip_locations(value)
        return result

    def assertEqual(self, a, b, msg=None):
        # Make assertEqual available (from TestCase via mixin)
        raise NotImplementedError("subclass must provide assertEqual")

    # === Test cases ===

    def test_simple_print(self):
        source = "skriv hej"
        expected = [PrintNode(value=ExpressionPartsNode(parts=["hej"]))]
        self.assertParseEqual(source, expected)

    def test_return_statement(self):
        source = "ge 42"
        expected = [ReturnNode(value=ExpressionPartsNode(parts=["42"]))]
        self.assertParseEqual(source, expected)

    def test_variable_assignment(self):
        source = "sätt x till 5"
        expected = [AssignNode(name="x", value=ExpressionPartsNode(parts=["5"]))]
        self.assertParseEqual(source, expected)

    def test_string_assignment(self):
        source = "sätt meddelande till hej världen"
        expected = [AssignNode(name="meddelande", value=ExpressionPartsNode(parts=["hej", "världen"]))]
        self.assertParseEqual(source, expected)

    def test_indentation_dedent(self):
        source = "sätt x till 1\nsätt y till 2"
        expected = [
            AssignNode(name="x", value=ExpressionPartsNode(parts=["1"])),
            AssignNode(name="y", value=ExpressionPartsNode(parts=["2"])),
        ]
        self.assertParseEqual(source, expected)

    def test_import_statement(self):
        source = "använd listor"
        expected = [ImportNode(module_name="listor", import_all=True, resolved=False)]
        self.assertParseEqual(source, expected)

    def test_while_loop(self):
        source = "medan x är mindre än 10\n    sätt x till x plus 1"
        expected = [
            WhileNode(
                condition=ExpressionPartsNode(parts=["x", "är", "mindre", "än", "10"]),
                body=[AssignNode(name="x", value=ExpressionPartsNode(parts=["x", "plus", "1"]))],
            )
        ]
        self.assertParseEqual(source, expected)

    def test_nested_expressions(self):
        source = "sätt resultat till a plus b gånger c"
        expected = [AssignNode(name="resultat", value=ExpressionPartsNode(parts=["a", "plus", "b", "gånger", "c"]))]
        self.assertParseEqual(source, expected)

    def test_comparison_operators(self):
        source = "om x är större än y\n    skriv större"
        expected = [
            IfNode(
                conditions=[
                    IfCondition(
                        test=ExpressionPartsNode(parts=["x", "är", "större", "än", "y"]),
                        block=[PrintNode(value=ExpressionPartsNode(parts=["större"]))],
                    )
                ]
            )
        ]
        self.assertParseEqual(source, expected)

    def test_boolean_literals(self):
        source = "om sant\n    skriv det stämmer"
        expected = [
            IfNode(
                conditions=[
                    IfCondition(
                        test=ExpressionPartsNode(parts=["sant"]),
                        block=[PrintNode(value=ExpressionPartsNode(parts=["det", "stämmer"]))],
                    )
                ]
            )
        ]
        self.assertParseEqual(source, expected)

    def test_bool_literal_sant(self):
        source = "skriv SANT"
        expected = [PrintNode(value=ExpressionPartsNode(parts=["SANT"]))]
        self.assertParseEqual(source, expected)

    def test_bool_literal_falskt(self):
        source = "skriv FALSKT"
        expected = [PrintNode(value=ExpressionPartsNode(parts=["FALSKT"]))]
        self.assertParseEqual(source, expected)

    def test_negation(self):
        source = "om inte x\n    skriv falskt"
        expected = [
            IfNode(
                conditions=[
                    IfCondition(
                        test=ExpressionPartsNode(parts=["inte", "x"]),
                        block=[PrintNode(value=ExpressionPartsNode(parts=["falskt"]))],
                    )
                ]
            )
        ]
        self.assertParseEqual(source, expected)

    def test_type_cast_som(self):
        source = "sätt x till 5 som text"
        expected = [AssignNode(name="x", value=ExpressionPartsNode(parts=["5", "som", "text"]))]
        self.assertParseEqual(source, expected)

    def test_property_access_från(self):
        source = "skriv längd från lista"
        expected = [PrintNode(value=ExpressionPartsNode(parts=["längd", "från", "lista"]))]
        self.assertParseEqual(source, expected)

    def test_element_access(self):
        source = "skriv element 0 från lista"
        expected = [PrintNode(value=ExpressionPartsNode(parts=["element", "0", "från", "lista"]))]
        self.assertParseEqual(source, expected)

    def test_file_operations(self):
        source = "stäng fil"
        expected = [CloseFileNode(target_var="fil")]
        self.assertParseEqual(source, expected)

    def test_named_arguments(self):
        source = "sätt resultat till foo med a 5, b 3"
        expected = [AssignNode(name="resultat", value=ExpressionPartsNode(parts=["foo", "med", "a", "5", ",", "b", "3"]))]
        self.assertParseEqual(source, expected)

    def test_increment_statement(self):
        source = "öka x med 5"
        expected = [AddAssignNode(target="x", value=ExpressionPartsNode(parts=["5"]))]
        self.assertParseEqual(source, expected)

    def test_decrement_statement(self):
        source = "minska x med 10"
        expected = [SubAssignNode(target="x", value=ExpressionPartsNode(parts=["10"]))]
        self.assertParseEqual(source, expected)

    def test_multiply_assign_statements(self):
        source = "gångra x med 3"
        expected = [MultiplyAssignNode(target="x", value=ExpressionPartsNode(parts=["3"]))]
        self.assertParseEqual(source, expected)

    def test_divide_assign_statements(self):
        source = "dela x med 2"
        expected = [DivideAssignNode(target="x", value=ExpressionPartsNode(parts=["2"]))]
        self.assertParseEqual(source, expected)

    def test_bryt_statement(self):
        source = "medan sant\n    bryt"
        expected = [WhileNode(condition=ExpressionPartsNode(parts=["sant"]), body=[BreakNode()])]
        self.assertParseEqual(source, expected)

    def test_fortsätt_statement(self):
        source = "medan sant\n    fortsätt"
        expected = [WhileNode(condition=ExpressionPartsNode(parts=["sant"]), body=[ContinueNode()])]
        self.assertParseEqual(source, expected)

    def test_list_creation(self):
        source = "sätt nums till lista med 1, 2, 3"
        expected = [AssignNode(name="nums", value=ExpressionPartsNode(parts=["lista", "med", "1", ",", "2", ",", "3"]))]
        self.assertParseEqual(source, expected)

    def test_function_definition(self):
        source = "sätt foo till grej med a som heltal, b som heltal ger heltal\n    ge a plus b"
        expected = [
            AssignNode(
                name="foo",
                value=FunctionDefNode(
                    params=[("a", "heltal"), ("b", "heltal")],
                    body=[ReturnNode(value=ExpressionPartsNode(parts=["a", "plus", "b"]))],
                    return_type='heltal',
                ),
            )
        ]
        self.assertParseEqual(source, expected)

    def test_if_statement(self):
        source = "om x är 5\n    skriv japp"
        expected = [
            IfNode(
                conditions=[
                    IfCondition(
                        test=ExpressionPartsNode(parts=["x", "är", "5"]),
                        block=[PrintNode(value=ExpressionPartsNode(parts=["japp"]))],
                    )
                ]
            )
        ]
        self.assertParseEqual(source, expected)

    def test_if_else_statement(self):
        source = "om x är 5\n    skriv japp\nannars\n    skriv nej"
        expected = [
            IfNode(
                conditions=[
                    IfCondition(
                        test=ExpressionPartsNode(parts=["x", "är", "5"]),
                        block=[PrintNode(value=ExpressionPartsNode(parts=["japp"]))],
                    )
                ],
                else_block=[PrintNode(value=ExpressionPartsNode(parts=["nej"]))],
            )
        ]
        self.assertParseEqual(source, expected)

    def test_grejtyp_declaration(self):
        """grejtyp declares a function type signature."""
        source = "grejtyp mingrej med x som heltal ger heltal"
        from hiuh.frontend.ast import FunctionTypeNode
        expected = [FunctionTypeNode(name="mingrej", params=[("x", "heltal")], return_type="heltal")]
        self.assertParseEqual(source, expected)


class TestPythonParser(_BaseParserTests, unittest.TestCase):
    """Parser tests using the Python Tokenizer+Parser."""

    def setUp(self):
        self.tokenizer = Tokenizer()

    def parse(self, source):
        tokens = self.tokenizer.tokenize(source)
        parser = Parser(tokens)
        return parser.parse()

    def assertEqual(self, a, b, msg=None):
        unittest.TestCase.assertEqual(self, a, b, msg)


class TestHiuhParser(_BaseParserTests, unittest.TestCase):
    """Parser tests using the hiuh tokeniserare+parser."""

    def setUp(self):
        self.tokenizer = Tokenizer()
        self._repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def parse(self, source):
        """Run source through hiuh tokeniserare then parser, return _StringWrapper list."""
        from hiuh.backend.interpreter.interpreter import Interpreter, ReturnException
        from hiuh.frontend.module_registry import ModuleRegistry
        from hiuh.frontend.resolver import Resolver

        lines = source.split("\n")
        line_strings = ", ".join(f'"{line}"' for line in lines)

        hiuh_source = (
            "använd parser\n"
            "använd tokeniserare\n"
            "använd testinterop\n"
            "\n"
            f"sätt källkod till lista med {line_strings}\n"
            "\n"
            "sätt tokens till tokenisera med källkod\n"
            "sätt ast till parsa med tokens\n"
            "ge formatera med ast\n"
        )

        mr = ModuleRegistry("/tmp/parser_hiuh_test")
        resolver = Resolver(mr, os.path.join(self._repo_root, "hiuh_i_hiuh"))

        tokens_py = self.tokenizer.tokenize(hiuh_source)
        parser = Parser(tokens_py)
        ast = parser.parse()

        resolver.discover_modules_from_ast("main", ast, self._repo_root)
        resolver.discover_imports("main")
        resolver.resolve_all()
        ast = resolver.get_ast("main")

        interp = Interpreter(mr)
        interp.modules = resolver.modules
        try:
            interp.execute(ast)
        except ReturnException as e:
            result = e.value
            if isinstance(result, list):
                return [_StringWrapper(s) for s in result]
        return []

    def assertEqual(self, a, b, msg=None):
        unittest.TestCase.assertEqual(self, a, b, msg)


if __name__ == "__main__":
    unittest.main()
