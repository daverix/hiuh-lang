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
            actual_strs = [w.value for w in actual]
            expected_strs = [ast_to_string(n) for n in expected_ast_nodes]
            self.assertEqual(actual_strs, expected_strs)
        else:
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
        raise NotImplementedError("subclass must provide assertEqual")

    def test_simple_print(self):
        source = "skriv hej"
        expected = [PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=['hej']))]
        self.assertParseEqual(source, expected)

    def test_return_statement(self):
        source = "ge 42"
        expected = [ReturnNode(None, None, value=ExpressionPartsNode(None, None, parts=['42']))]
        self.assertParseEqual(source, expected)

    def test_variable_assignment(self):
        source = "sätt x till 5"
        expected = [AssignNode(None, None, name='x', value=ExpressionPartsNode(None, None, parts=['5']))]
        self.assertParseEqual(source, expected)

    def test_string_assignment(self):
        source = "sätt meddelande till hej världen"
        expected = [AssignNode(None, None, name='meddelande', value=ExpressionPartsNode(None, None, parts=['hej', 'världen']))]
        self.assertParseEqual(source, expected)

    def test_indentation_dedent(self):
        source = """\
sätt x till 1
sätt y till 2"""
        expected = [AssignNode(None, None, name='x', value=ExpressionPartsNode(None, None, parts=['1'])), AssignNode(None, None, name='y', value=ExpressionPartsNode(None, None, parts=['2']))]
        self.assertParseEqual(source, expected)

    def test_import_statement(self):
        source = "använd listor"
        expected = [ImportNode(None, None, module_name='listor', import_all=True, resolved=False)]
        self.assertParseEqual(source, expected)

    def test_while_loop(self):
        source = """\
medan x är mindre än 10
    sätt x till x plus 1"""
        expected = [WhileNode(None, None, condition=ExpressionPartsNode(None, None, parts=['x', 'är', 'mindre', 'än', '10']), body=[AssignNode(None, None, name='x', value=ExpressionPartsNode(None, None, parts=['x', 'plus', '1']))])]
        self.assertParseEqual(source, expected)

    def test_nested_expressions(self):
        source = "sätt resultat till a plus b gånger c"
        expected = [AssignNode(None, None, name='resultat', value=ExpressionPartsNode(None, None, parts=['a', 'plus', 'b', 'gånger', 'c']))]
        self.assertParseEqual(source, expected)

    def test_comparison_operators(self):
        source = """\
om x är större än y
    skriv större"""
        expected = [IfNode(None, None, conditions=[IfCondition(None, None, test=ExpressionPartsNode(None, None, parts=['x', 'är', 'större', 'än', 'y']), block=[PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=['större']))])])]
        self.assertParseEqual(source, expected)

    def test_boolean_literals(self):
        source = """\
om sant
    skriv det stämmer"""
        expected = [IfNode(None, None, conditions=[IfCondition(None, None, test=ExpressionPartsNode(None, None, parts=['sant']), block=[PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=['det', 'stämmer']))])])]
        self.assertParseEqual(source, expected)

    def test_bool_literal_sant(self):
        source = "skriv SANT"
        expected = [PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=['SANT']))]
        self.assertParseEqual(source, expected)

    def test_bool_literal_falskt(self):
        source = "skriv FALSKT"
        expected = [PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=['FALSKT']))]
        self.assertParseEqual(source, expected)

    def test_negation(self):
        source = """\
om inte x
    skriv falskt"""
        expected = [IfNode(None, None, conditions=[IfCondition(None, None, test=ExpressionPartsNode(None, None, parts=['inte', 'x']), block=[PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=['falskt']))])])]
        self.assertParseEqual(source, expected)

    def test_type_cast_som(self):
        source = "sätt x till 5 som text"
        expected = [AssignNode(None, None, name='x', value=ExpressionPartsNode(None, None, parts=['5', 'som', 'text']))]
        self.assertParseEqual(source, expected)

    def test_property_access_från(self):
        source = "skriv längd från lista"
        expected = [PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=['längd', 'från', 'lista']))]
        self.assertParseEqual(source, expected)

    def test_element_access(self):
        source = "skriv element 0 från lista"
        expected = [PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=['element', '0', 'från', 'lista']))]
        self.assertParseEqual(source, expected)

    def test_file_operations(self):
        source = "stäng fil"
        expected = [CloseFileNode(None, None, target_var='fil')]
        self.assertParseEqual(source, expected)

    def test_named_arguments(self):
        source = "sätt resultat till foo med a 5, b 3"
        expected = [AssignNode(None, None, name='resultat', value=ExpressionPartsNode(None, None, parts=['foo', 'med', 'a', '5', ',', 'b', '3']))]
        self.assertParseEqual(source, expected)

    def test_increment_statement(self):
        source = "öka x med 5"
        expected = [AddAssignNode(None, None, target='x', value=ExpressionPartsNode(None, None, parts=['5']))]
        self.assertParseEqual(source, expected)

    def test_decrement_statement(self):
        source = "minska x med 10"
        expected = [SubAssignNode(None, None, target='x', value=ExpressionPartsNode(None, None, parts=['10']))]
        self.assertParseEqual(source, expected)

    def test_multiply_assign_statements(self):
        source = "gångra x med 3"
        expected = [MultiplyAssignNode(None, None, target='x', value=ExpressionPartsNode(None, None, parts=['3']))]
        self.assertParseEqual(source, expected)

    def test_divide_assign_statements(self):
        source = "dela x med 2"
        expected = [DivideAssignNode(None, None, target='x', value=ExpressionPartsNode(None, None, parts=['2']))]
        self.assertParseEqual(source, expected)

    def test_bryt_statement(self):
        source = """\
medan sant
    bryt"""
        expected = [WhileNode(None, None, condition=ExpressionPartsNode(None, None, parts=['sant']), body=[BreakNode(None, None)])]
        self.assertParseEqual(source, expected)

    def test_fortsätt_statement(self):
        source = """\
medan sant
    fortsätt"""
        expected = [WhileNode(None, None, condition=ExpressionPartsNode(None, None, parts=['sant']), body=[ContinueNode(None, None)])]
        self.assertParseEqual(source, expected)

    def test_list_creation(self):
        source = "sätt nums till lista med 1, 2, 3"
        expected = [AssignNode(None, None, name='nums', value=ExpressionPartsNode(None, None, parts=['lista', 'med', '1', ',', '2', ',', '3']))]
        self.assertParseEqual(source, expected)

    def test_function_definition(self):
        source = """\
sätt foo till grej med a som heltal, b som heltal ger heltal
    ge a plus b"""
        expected = [AssignNode(None, None, name='foo', value=FunctionDefNode(None, None, params=[('a', 'heltal'), ('b', 'heltal')], body=[ReturnNode(None, None, value=ExpressionPartsNode(None, None, parts=['a', 'plus', 'b']))], return_type='heltal'))]
        self.assertParseEqual(source, expected)

    def test_if_statement(self):
        source = """\
om x är 5
    skriv japp"""
        expected = [IfNode(None, None, conditions=[IfCondition(None, None, test=ExpressionPartsNode(None, None, parts=['x', 'är', '5']), block=[PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=['japp']))])])]
        self.assertParseEqual(source, expected)

    def test_if_else_statement(self):
        source = """\
om x är 5
    skriv japp
annars
    skriv nej"""
        expected = [IfNode(None, None, conditions=[IfCondition(None, None, test=ExpressionPartsNode(None, None, parts=['x', 'är', '5']), block=[PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=['japp']))])], else_block=[PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=['nej']))])]
        self.assertParseEqual(source, expected)

    def test_grejtyp_declaration(self):
        """grejtyp declares a function type signature."""
        source = "grejtyp mingrej med x som heltal ger heltal"
        from hiuh.frontend.ast import FunctionTypeNode
        expected = [FunctionTypeNode(None, None, name='mingrej', params=[('x', 'heltal')], return_type='heltal')]
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
        line_strings = ', '.join((f'"{line}"' for line in lines))
        hiuh_source = f'använd parser\nanvänd tokeniserare\nanvänd testinterop\n\nsätt källkod till lista med {line_strings}\n\nsätt tokens till tokenisera med källkod\nsätt ast till parsa med tokens\nge formatera med ast\n'
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