"""Parser tests - tests raw parser output without resolver transformation."""
import unittest

from hiuh.frontend.ast import *
from hiuh.frontend.parser import Parser
from hiuh.frontend.tokenizer import Tokenizer


class TestHiuhParserRaw(unittest.TestCase):
    """Test parser only - verifies raw AST output before resolver transformation."""
    
    def setUp(self):
        self.tokenizer = Tokenizer()

    def parse_source(self, source):
        """Parse source and return raw AST (no resolver)."""
        tokens = self.tokenizer.tokenize(source)
        parser = Parser(tokens)
        return parser.parse()

    def strip_locations(self, node):
        if isinstance(node, list):
            return [self.strip_locations(child) for child in node]

        if not hasattr(node, '__dict__'):
            return node

        result = {}
        for key, value in node.__dict__.items():
            if key in ('line', 'column', 'token'):
                continue
            result[key] = self.strip_locations(value)
        return result

    def assertNodesEqual(self, actual, expected):
        actual_stripped = self.strip_locations(actual)
        expected_stripped = self.strip_locations(expected)
        self.assertEqual(actual_stripped, expected_stripped)

    def test_simple_print(self):
        """Verify that 'skriv hej' creates a PrintNode."""
        source = "skriv hej"
        expected = [
            PrintNode(value=ExpressionPartsNode(parts=["hej"]))
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_variable_assignment(self):
        """Verify that 'sätt x till 5' creates an AssignNode."""
        source = "sätt x till 5"
        expected = [
            AssignNode(
                name="x",
                value=ExpressionPartsNode(parts=["5"])
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_string_assignment(self):
        """Verify that string assignments work."""
        source = "sätt meddelande till hej världen"
        expected = [
            AssignNode(
                name="meddelande",
                value=ExpressionPartsNode(parts=["hej", "världen"])
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_if_statement(self):
        """Verify that if statements are parsed correctly."""
        source = "om x är 5\n    skriv japp"
        expected = [
            IfNode(
                conditions=[
                    IfCondition(
                        test=ExpressionPartsNode(parts=["x", "är", "5"]),
                        block=[PrintNode(value=ExpressionPartsNode(parts=["japp"]))]
                    )
                ]
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_if_else_statement(self):
        """Verify that if-else statements are parsed correctly."""
        source = "om x är 5\n    skriv japp\nannars\n    skriv nej"
        expected = [
            IfNode(
                conditions=[
                    IfCondition(
                        test=ExpressionPartsNode(parts=["x", "är", "5"]),
                        block=[PrintNode(value=ExpressionPartsNode(parts=["japp"]))]
                    )
                ],
                else_block=[PrintNode(value=ExpressionPartsNode(parts=["nej"]))]
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_while_loop(self):
        """Verify that while loops are parsed correctly."""
        source = "medan x är mindre än 10\n    sätt x till x plus 1"
        expected = [
            WhileNode(
                condition=ExpressionPartsNode(parts=["x", "är", "mindre", "än", "10"]),
                body=[
                    AssignNode(
                        name="x",
                        value=ExpressionPartsNode(parts=["x", "plus", "1"])
                    )
                ]
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_for_each_loop(self):
        """Verify that for-each loops are parsed correctly with multi-word variable.
        
        The variable name is joined into a single string.
        Expression parts remain as separate tokens.
        """
        source = "sätt min lista till lista med a, b, c\nför varje mitt index i min lista\n    skriv mitt index"
        expected = [
            AssignNode(
                name="min lista",
                value=ExpressionPartsNode(parts=["lista", "med", "a", ",", "b", ",", "c"])
            ),
            ForEachNode(
                variable="mitt index",
                iterable=ExpressionPartsNode(parts=["min", "lista"]),
                body=[
                    PrintNode(value=ExpressionPartsNode(parts=["mitt", "index"]))
                ]
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_function_definition(self):
        """Verify that function definitions are parsed correctly."""
        source = "sätt foo till grej med a, b\n    ge a plus b"
        expected = [
            AssignNode(
                name="foo",
                value=FunctionDefNode(
                    params=["a", "b"],
                    body=[
                        ReturnNode(value=ExpressionPartsNode(parts=["a", "plus", "b"]))
                    ]
                )
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_function_call(self):
        """Verify that function calls are parsed correctly."""
        source = "sätt resultat till foo med5, 3"
        expected = [
            AssignNode(
                name="resultat",
                value=ExpressionPartsNode(parts=["foo", "med5", ",", "3"])
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_return_statement(self):
        """Verify that return statements are parsed correctly."""
        source = "ge 42"
        expected = [
            ReturnNode(value=ExpressionPartsNode(parts=["42"]))
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_boolean_literals(self):
        """Verify that boolean literals are recognized."""
        source = "om sant\n    skriv det stämmer"
        expected = [
            IfNode(
                conditions=[
                    IfCondition(
                        test=ExpressionPartsNode(parts=["sant"]),
                        block=[PrintNode(value=ExpressionPartsNode(parts=["det", "stämmer"]))]
                    )
                ]
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_nested_expressions(self):
        """Verify that nested expressions are preserved."""
        source = "sätt resultat till a plus b gånger c"
        expected = [
            AssignNode(
                name="resultat",
                value=ExpressionPartsNode(parts=["a", "plus", "b", "gånger", "c"])
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_list_creation(self):
        """Verify that list creation is parsed correctly."""
        source = "sätt nums till lista med 1, 2, 3"
        expected = [
            AssignNode(
                name="nums",
                value=ExpressionPartsNode(parts=["lista", "med", "1", ",", "2", ",", "3"])
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_comparison_operators(self):
        """Verify that comparison operators are preserved."""
        source = "om x är större än y\n    skriv större"
        expected = [
            IfNode(
                conditions=[
                    IfCondition(
                        test=ExpressionPartsNode(parts=["x", "är", "större", "än", "y"]),
                        block=[PrintNode(value=ExpressionPartsNode(parts=["större"]))]
                    )
                ]
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_negation(self):
        """Verify that negation 'inte' is preserved."""
        source = "om inte x\n    skriv falskt"
        expected = [
            IfNode(
                conditions=[
                    IfCondition(
                        test=ExpressionPartsNode(parts=["inte", "x"]),
                        block=[PrintNode(value=ExpressionPartsNode(parts=["falskt"]))]
                    )
                ]
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_type_cast_som(self):
        """Verify that type cast 'som' is preserved."""
        source = "sätt x till 5 som text"
        expected = [
            AssignNode(
                name="x",
                value=ExpressionPartsNode(parts=["5", "som", "text"])
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_property_access_från(self):
        """Verify that property access 'från' is preserved."""
        source = "skriv längd från lista"
        expected = [
            PrintNode(
                value=ExpressionPartsNode(parts=["längd", "från", "lista"])
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_element_access(self):
        """Verify that element access is preserved."""
        source = "skriv element0 från lista"
        expected = [
            PrintNode(
                value=ExpressionPartsNode(parts=["element0", "från", "lista"])
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_infix_function_definition(self):
        """Verify that infix function definition is parsed correctly."""
        source = "sätt är del av till infix grej med del, helhet\n    ge falskt"
        expected = [
            AssignNode(
                name="är del av",
                value=FunctionDefNode(
                    params=["del", "helhet"],
                    body=[ReturnNode(value=ExpressionPartsNode(parts=["falskt"]))],
                    is_infix=True
                )
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_infix_function_call(self):
        """Verify that infix function call is preserved as ExpressionPartsNode."""
        source = "om a är del av b\n    skriv ja"
        expected = [
            IfNode(
                conditions=[
                    IfCondition(
                        test=ExpressionPartsNode(parts=["a", "är", "del", "av", "b"]),
                        block=[PrintNode(value=ExpressionPartsNode(parts=["ja"]))]
                    )
                ]
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_try_catch(self):
        """Verify that try-catch is parsed correctly."""
        source = "försök\n    kasta fel\nfånga fel\n    skriv fel"
        expected = [
            TryCatchNode(
                try_block=[UnaryOpNode(op="kasta", operand=ExpressionPartsNode(parts=["fel"]))],
                error_var="fel",
                catch_block=[PrintNode(value=ExpressionPartsNode(parts=["fel"]))]
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_try_finally(self):
        """Verify that try-finally is parsed correctly."""
        source = "försök\n    skriv hej\nslutligen\n    skriv hejdå"
        expected = [
            TryCatchNode(
                try_block=[PrintNode(value=ExpressionPartsNode(parts=["hej"]))],
                error_var=None,
                catch_block=None,
                finally_block=[PrintNode(value=ExpressionPartsNode(parts=["hejdå"]))]
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_file_operations(self):
        """Verify that file operations are parsed correctly."""
        source = "stäng fil"
        expected = [
            CloseFileNode(target_var="fil")
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_named_arguments(self):
        """Verify that named arguments are preserved as ExpressionPartsNode."""
        source = "sätt resultat till foo med a 5, b 3"
        expected = [
            AssignNode(
                name="resultat",
                value=ExpressionPartsNode(parts=["foo", "med", "a", "5", ",", "b", "3"])
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_import_statement(self):
        """Verify that import statements are parsed correctly."""
        source = "använd listor"
        expected = [
            ImportNode(module_name="listor", import_all=True, resolved=False)
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_indentation_dedent(self):
        """Verify that indentation and dedentation are handled correctly."""
        source = "sätt x till 1\nsätt y till 2"
        expected = [
            AssignNode(name="x", value=ExpressionPartsNode(parts=["1"])),
            AssignNode(name="y", value=ExpressionPartsNode(parts=["2"]))
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_increment_statement(self):
        """Verify that 'öka x med 5' parses to IncrementNode."""
        source = "öka x med 5"
        expected = [
            IncrementNode(target="x", value=ExpressionPartsNode(parts=["5"]))
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_decrement_statement(self):
        """Verify that 'minska x med 10' parses to DecrementNode."""
        source = "minska x med 10"
        expected = [
            DecrementNode(target="x", value=ExpressionPartsNode(parts=["10"]))
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_increment_multi_word_variable(self):
        """Verify that 'öka min hälsa med 1,5' parses to IncrementNode with multi-word target."""
        source = "öka min hälsa med 1,5"
        expected = [
            IncrementNode(target="min hälsa", value=ExpressionPartsNode(parts=["1,5"]))
        ]
        self.assertNodesEqual(self.parse_source(source), expected)


if __name__ == '__main__':
    unittest.main()
