"""Parser tests - tests raw parser output without resolver transformation.

TestPythonParser: uses Python Tokenizer+Parser
TestHiuhParser: uses hiuh tokeniserare+parser via interpreter
"""
import os
import unittest
from hiuh.frontend.ast import *
from hiuh.frontend.parser import Parser
from hiuh.frontend.tokenizer import Tokenizer, TOKEN_PRINT, TOKEN_SET, TOKEN_TO, TOKEN_FUNC, TOKEN_WITH, TOKEN_GIVE, TOKEN_TYPE, TOKEN_IN, TOKEN_FROM, TOKEN_IF, TOKEN_ELSE, TOKEN_TRY, TOKEN_THROW, TOKEN_CATCH, TOKEN_WHILE, TOKEN_IMPORT, TOKEN_OPEN, TOKEN_CLOSE, TOKEN_AS, TOKEN_GREATER, TOKEN_LESS, TOKEN_EQUAL, TOKEN_THAN, TOKEN_OR, TOKEN_AND, TOKEN_OP_ADD, TOKEN_OP_SUB, TOKEN_OP_MUL, TOKEN_OP_DIV, TOKEN_OP_IS, TOKEN_LITERAL_INT, TOKEN_LITERAL_FLOAT, TOKEN_LITERAL_TRUE, TOKEN_LITERAL_FALSE, TOKEN_STRING, TOKEN_IDENTIFIER, TOKEN_NEWLINE, TOKEN_INDENT, TOKEN_DEDENT, TOKEN_COMMA, TOKEN_COPY, TOKEN_OF, TOKEN_INFIX, TOKEN_FOR, TOKEN_EACH, TOKEN_BREAK, TOKEN_CONTINUE, TOKEN_INHERITS, TOKEN_RETURNS
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
        if isinstance(node, tuple):
            return tuple(self._strip_locations(child) for child in node)
        if isinstance(node, ExpressionPart):
            return (node.value, node.token_type)
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
        expected = [PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('hej', TOKEN_IDENTIFIER)]))]
        self.assertParseEqual(source, expected)

    def test_return_statement(self):
        source = "ge 42"
        expected = [ReturnNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('42', TOKEN_LITERAL_INT)]))]
        self.assertParseEqual(source, expected)

    def test_variable_assignment(self):
        source = "sätt x till 5"
        expected = [AssignNode(None, None, name='x', value=ExpressionPartsNode(None, None, parts=[ExpressionPart('5', TOKEN_LITERAL_INT)]))]
        self.assertParseEqual(source, expected)

    def test_string_assignment(self):
        source = "sätt meddelande till hej världen"
        expected = [AssignNode(None, None, name='meddelande', value=ExpressionPartsNode(None, None, parts=[ExpressionPart('hej', TOKEN_IDENTIFIER), ExpressionPart('världen', TOKEN_IDENTIFIER)]))]
        self.assertParseEqual(source, expected)

    def test_indentation_dedent(self):
        source = """\
sätt x till 1
sätt y till 2"""
        expected = [AssignNode(None, None, name='x', value=ExpressionPartsNode(None, None, parts=[ExpressionPart('1', TOKEN_LITERAL_INT)])), AssignNode(None, None, name='y', value=ExpressionPartsNode(None, None, parts=[ExpressionPart('2', TOKEN_LITERAL_INT)]))]
        self.assertParseEqual(source, expected)

    def test_import_statement(self):
        source = "använd listor"
        expected = [ImportNode(None, None, module_name='listor', import_all=True, resolved=False)]
        self.assertParseEqual(source, expected)

    def test_while_loop(self):
        source = """\
medan x är mindre än 10
    sätt x till x plus 1"""
        expected = [WhileNode(None, None, condition=ExpressionPartsNode(None, None, parts=[ExpressionPart('x', TOKEN_IDENTIFIER), ExpressionPart('är', TOKEN_OP_IS), ExpressionPart('mindre', TOKEN_LESS), ExpressionPart('än', TOKEN_THAN), ExpressionPart('10', TOKEN_LITERAL_INT)]), body=[AssignNode(None, None, name='x', value=ExpressionPartsNode(None, None, parts=[ExpressionPart('x', TOKEN_IDENTIFIER), ExpressionPart('plus', TOKEN_OP_ADD), ExpressionPart('1', TOKEN_LITERAL_INT)]))])]
        self.assertParseEqual(source, expected)

    def test_nested_expressions(self):
        source = "sätt resultat till a plus b gånger c"
        expected = [AssignNode(None, None, name='resultat', value=ExpressionPartsNode(None, None, parts=[ExpressionPart('a', TOKEN_IDENTIFIER), ExpressionPart('plus', TOKEN_OP_ADD), ExpressionPart('b', TOKEN_IDENTIFIER), ExpressionPart('gånger', TOKEN_OP_MUL), ExpressionPart('c', TOKEN_IDENTIFIER)]))]
        self.assertParseEqual(source, expected)

    def test_comparison_operators(self):
        source = """\
om x är större än y
    skriv större"""
        expected = [IfNode(None, None, conditions=[IfCondition(None, None, test=ExpressionPartsNode(None, None, parts=[ExpressionPart('x', TOKEN_IDENTIFIER), ExpressionPart('är', TOKEN_OP_IS), ExpressionPart('större', TOKEN_GREATER), ExpressionPart('än', TOKEN_THAN), ExpressionPart('y', TOKEN_IDENTIFIER)]), block=[PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('större', TOKEN_GREATER)]))])])]
        self.assertParseEqual(source, expected)

    def test_boolean_literals(self):
        source = """\
om sant
    skriv det stämmer"""
        expected = [IfNode(None, None, conditions=[IfCondition(None, None, test=ExpressionPartsNode(None, None, parts=[ExpressionPart('sant', TOKEN_LITERAL_TRUE)]), block=[PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('det', TOKEN_IDENTIFIER), ExpressionPart('stämmer', TOKEN_IDENTIFIER)]))])])]
        self.assertParseEqual(source, expected)

    def test_bool_literal_sant(self):
        source = "skriv SANT"
        expected = [PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('SANT', TOKEN_LITERAL_TRUE)]))]
        self.assertParseEqual(source, expected)

    def test_bool_literal_falskt(self):
        source = "skriv FALSKT"
        expected = [PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('FALSKT', TOKEN_LITERAL_FALSE)]))]
        self.assertParseEqual(source, expected)

    def test_negation(self):
        source = """\
om inte x
    skriv falskt"""
        expected = [IfNode(None, None, conditions=[IfCondition(None, None, test=ExpressionPartsNode(None, None, parts=[ExpressionPart('inte', TOKEN_IDENTIFIER), ExpressionPart('x', TOKEN_IDENTIFIER)]), block=[PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('falskt', TOKEN_LITERAL_FALSE)]))])])]
        self.assertParseEqual(source, expected)

    def test_type_cast_som(self):
        source = "sätt x till 5 som text"
        expected = [AssignNode(None, None, name='x', value=ExpressionPartsNode(None, None, parts=[ExpressionPart('5', TOKEN_LITERAL_INT), ExpressionPart('som', TOKEN_AS), ExpressionPart('text', TOKEN_IDENTIFIER)]))]
        self.assertParseEqual(source, expected)

    def test_property_access_från(self):
        source = "skriv längd från lista"
        expected = [PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('längd', TOKEN_IDENTIFIER), ExpressionPart('från', TOKEN_FROM), ExpressionPart('lista', TOKEN_IDENTIFIER)]))]
        self.assertParseEqual(source, expected)

    def test_element_access(self):
        source = "skriv element 0 från lista"
        expected = [PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('element', TOKEN_IDENTIFIER), ExpressionPart('0', TOKEN_LITERAL_INT), ExpressionPart('från', TOKEN_FROM), ExpressionPart('lista', TOKEN_IDENTIFIER)]))]
        self.assertParseEqual(source, expected)

    def test_file_operations(self):
        source = "stäng fil"
        expected = [CloseFileNode(None, None, target_var='fil')]
        self.assertParseEqual(source, expected)

    def test_named_arguments(self):
        source = "sätt resultat till foo med a 5, b 3"
        expected = [AssignNode(None, None, name='resultat', value=ExpressionPartsNode(None, None, parts=[ExpressionPart('foo', TOKEN_IDENTIFIER), ExpressionPart('med', TOKEN_WITH), ExpressionPart('a', TOKEN_IDENTIFIER), ExpressionPart('5', TOKEN_LITERAL_INT), ExpressionPart(',', TOKEN_COMMA), ExpressionPart('b', TOKEN_IDENTIFIER), ExpressionPart('3', TOKEN_LITERAL_INT)]))]
        self.assertParseEqual(source, expected)

    def test_increment_statement(self):
        source = "öka x med 5"
        expected = [AddAssignNode(None, None, target='x', value=ExpressionPartsNode(None, None, parts=[ExpressionPart('5', TOKEN_LITERAL_INT)]))]
        self.assertParseEqual(source, expected)

    def test_decrement_statement(self):
        source = "minska x med 10"
        expected = [SubAssignNode(None, None, target='x', value=ExpressionPartsNode(None, None, parts=[ExpressionPart('10', TOKEN_LITERAL_INT)]))]
        self.assertParseEqual(source, expected)

    def test_multiply_assign_statements(self):
        source = "gångra x med 3"
        expected = [MultiplyAssignNode(None, None, target='x', value=ExpressionPartsNode(None, None, parts=[ExpressionPart('3', TOKEN_LITERAL_INT)]))]
        self.assertParseEqual(source, expected)

    def test_divide_assign_statements(self):
        source = "dela x med 2"
        expected = [DivideAssignNode(None, None, target='x', value=ExpressionPartsNode(None, None, parts=[ExpressionPart('2', TOKEN_LITERAL_INT)]))]
        self.assertParseEqual(source, expected)

    def test_bryt_statement(self):
        source = """\
medan sant
    bryt"""
        expected = [WhileNode(None, None, condition=ExpressionPartsNode(None, None, parts=[ExpressionPart('sant', TOKEN_LITERAL_TRUE)]), body=[BreakNode(None, None)])]
        self.assertParseEqual(source, expected)

    def test_fortsätt_statement(self):
        source = """\
medan sant
    fortsätt"""
        expected = [WhileNode(None, None, condition=ExpressionPartsNode(None, None, parts=[ExpressionPart('sant', TOKEN_LITERAL_TRUE)]), body=[ContinueNode(None, None)])]
        self.assertParseEqual(source, expected)

    def test_list_creation(self):
        source = "sätt nums till lista med 1, 2, 3"
        expected = [AssignNode(None, None, name='nums', value=ExpressionPartsNode(None, None, parts=[ExpressionPart('lista', TOKEN_IDENTIFIER), ExpressionPart('med', TOKEN_WITH), ExpressionPart('1', TOKEN_LITERAL_INT), ExpressionPart(',', TOKEN_COMMA), ExpressionPart('2', TOKEN_LITERAL_INT), ExpressionPart(',', TOKEN_COMMA), ExpressionPart('3', TOKEN_LITERAL_INT)]))]
        self.assertParseEqual(source, expected)

    def test_function_definition(self):
        source = """\
sätt foo till grej med a som heltal, b som heltal ger heltal
    ge a plus b"""
        expected = [AssignNode(None, None, name='foo', value=FunctionDefNode(None, None, params=[('a', 'heltal'), ('b', 'heltal')], body=[ReturnNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('a', TOKEN_IDENTIFIER), ExpressionPart('plus', TOKEN_OP_ADD), ExpressionPart('b', TOKEN_IDENTIFIER)]))], return_type='heltal'))]
        self.assertParseEqual(source, expected)

    def test_if_statement(self):
        source = """\
om x är 5
    skriv japp"""
        expected = [IfNode(None, None, conditions=[IfCondition(None, None, test=ExpressionPartsNode(None, None, parts=[ExpressionPart('x', TOKEN_IDENTIFIER), ExpressionPart('är', TOKEN_OP_IS), ExpressionPart('5', TOKEN_LITERAL_INT)]), block=[PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('japp', TOKEN_IDENTIFIER)]))])])]
        self.assertParseEqual(source, expected)

    def test_if_else_statement(self):
        source = """\
om x är 5
    skriv japp
annars
    skriv nej"""
        expected = [IfNode(None, None, conditions=[IfCondition(None, None, test=ExpressionPartsNode(None, None, parts=[ExpressionPart('x', TOKEN_IDENTIFIER), ExpressionPart('är', TOKEN_OP_IS), ExpressionPart('5', TOKEN_LITERAL_INT)]), block=[PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('japp', TOKEN_IDENTIFIER)]))])], else_block=[PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('nej', TOKEN_IDENTIFIER)]))])]
        self.assertParseEqual(source, expected)

    def test_grejtyp_declaration(self):
        """grejtyp declares a function type signature."""
        source = "grejtyp mingrej med x som heltal ger heltal"
        from hiuh.frontend.ast import FunctionTypeNode
        expected = [FunctionTypeNode(None, None, name='mingrej', params=[('x', 'heltal')], return_type='heltal')]
        self.assertParseEqual(source, expected)

# --- append (lägg till) ---
    def test_append_statement(self):
        source = "lägg till hej i lista"
        expected = [AppendNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('hej', TOKEN_IDENTIFIER)]), target_list='lista')]
        self.assertParseEqual(source, expected)

# --- remove (ta bort) ---
    def test_remove_value_statement(self):
        source = "ta bort hej från lista"
        expected = [RemoveValueNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('hej', TOKEN_IDENTIFIER)]), target_list='lista')]
        self.assertParseEqual(source, expected)

    def test_remove_index_statement(self):
        source = "ta bort element 0 från lista"
        expected = [RemoveIndexNode(None, None, index=ExpressionPartsNode(None, None, parts=[ExpressionPart('0', TOKEN_LITERAL_INT)]), target_list='lista')]
        self.assertParseEqual(source, expected)

# --- skicka call (putta X till Y) ---
    def test_skicka_call(self):
        source = "putta hej till min lista"
        expected = [AssignNode(None, None, name='min lista', value=FunctionCallNode(None, None, name='putta', args=[ExpressionPartsNode(None, None, parts=[ExpressionPart('hej', TOKEN_IDENTIFIER)]), VarAccessNode(None, None, 'min lista')]))]
        self.assertParseEqual(source, expected)

# --- for_each ---
    def test_for_each_loop(self):
        source = """\
för varje x i lista
    skriv x"""
        expected = [ForEachNode(None, None, variable='x', iterable=ExpressionPartsNode(None, None, parts=[ExpressionPart('lista', TOKEN_IDENTIFIER)]), body=[PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('x', TOKEN_IDENTIFIER)]))])]
        self.assertParseEqual(source, expected)

    def test_for_each_multipart_variable(self):
        source = """\
för varje mitt index i lista
    skriv mitt index"""
        expected = [ForEachNode(None, None, variable='mitt index', iterable=ExpressionPartsNode(None, None, parts=[ExpressionPart('lista', TOKEN_IDENTIFIER)]), body=[PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('mitt', TOKEN_IDENTIFIER), ExpressionPart('index', TOKEN_IDENTIFIER)]))])]
        self.assertParseEqual(source, expected)

# --- try/catch/finally ---
    def test_try_catch(self):
        source = """\
försök
    skriv hej
fånga fel
    skriv fel"""
        expected = [TryCatchNode(None, None, try_block=[PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('hej', TOKEN_IDENTIFIER)]))], error_var='fel', catch_block=[PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('fel', TOKEN_IDENTIFIER)]))])]
        self.assertParseEqual(source, expected)

    def test_try_finally(self):
        source = """\
försök
    skriv hej
slutligen
    skriv klart"""
        expected = [TryCatchNode(None, None, try_block=[PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('hej', TOKEN_IDENTIFIER)]))], error_var=None, catch_block=None, finally_block=[PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('klart', TOKEN_IDENTIFIER)]))])]
        self.assertParseEqual(source, expected)

    def test_try_catch_finally(self):
        source = """\
försök
    skriv hej
fånga fel
    skriv fel
slutligen
    skriv klart"""
        expected = [TryCatchNode(None, None, try_block=[PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('hej', TOKEN_IDENTIFIER)]))], error_var='fel', catch_block=[PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('fel', TOKEN_IDENTIFIER)]))], finally_block=[PrintNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('klart', TOKEN_IDENTIFIER)]))])]
        self.assertParseEqual(source, expected)

# --- throw (kasta) ---
    def test_throw_statement(self):
        source = "kasta något fel"
        expected = [UnaryOpNode(None, None, op='kasta', operand=ExpressionPartsNode(None, None, parts=[ExpressionPart('något', TOKEN_IDENTIFIER), ExpressionPart('fel', TOKEN_IDENTIFIER)]))]
        self.assertParseEqual(source, expected)

# --- type definition (typ) ---
    def test_type_definition(self):
        source = """\
typ person
    namn som sträng
    ålder som heltal"""
        expected = [TypeDefNode(None, None, name='person', fields=[('namn', 'sträng'), ('ålder', 'heltal')])]
        self.assertParseEqual(source, expected)

# --- element assignment (sätt element X i Y till Z) ---
    def test_element_assign_int_index(self):
        source = "sätt element 0 i lista till 42"
        expected = [ElementAssignNode(None, None, index='0', target='lista', value=ExpressionPartsNode(None, None, parts=[ExpressionPart('42', TOKEN_LITERAL_INT)]))]
        self.assertParseEqual(source, expected)

    def test_element_assign_variable_index(self):
        source = "sätt element x i lista till hej"
        expected = [ElementAssignNode(None, None, index='x', target='lista', value=ExpressionPartsNode(None, None, parts=[ExpressionPart('hej', TOKEN_IDENTIFIER)]))]
        self.assertParseEqual(source, expected)

# --- function kinds ---
    def test_infixgrej_definition(self):
        source = """\
sätt är del av till infixgrej med del som heltal, helhet som lista av heltal ger boolesk
    ge FALSKT"""
        expected = [AssignNode(None, None, name='är del av', value=FunctionDefNode(None, None, params=[('del', 'heltal'), ('helhet', 'lista av heltal')], body=[ReturnNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('FALSKT', TOKEN_LITERAL_FALSE)]))], kind='infix', return_type='boolesk'))]
        self.assertParseEqual(source, expected)

    def test_verbgrej_definition(self):
        source = """\
sätt upprepa till verbgrej med ord som sträng, antal som heltal ger sträng
    ge ord"""
        expected = [AssignNode(None, None, name='upprepa', value=FunctionDefNode(None, None, params=[('ord', 'sträng'), ('antal', 'heltal')], body=[ReturnNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('ord', TOKEN_IDENTIFIER)]))], kind='verb', return_type='sträng'))]
        self.assertParseEqual(source, expected)

    def test_skickagrej_definition(self):
        source = """\
sätt lägg_till till skickagrej med sak som sträng, mål som lista av sträng ger lista av sträng
    ge mål"""
        expected = [AssignNode(None, None, name='lägg_till', value=FunctionDefNode(None, None, params=[('sak', 'sträng'), ('mål', 'lista av sträng')], body=[ReturnNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('mål', TOKEN_IDENTIFIER)]))], kind='skicka', return_type='lista av sträng'))]
        self.assertParseEqual(source, expected)

    def test_hämtagrej_definition(self):
        source = """\
sätt plocka till hämtagrej med namn som sträng, källa som lista av sträng ger sträng
    ge element 0 från källa"""
        expected = [AssignNode(None, None, name='plocka', value=FunctionDefNode(None, None, params=[('namn', 'sträng'), ('källa', 'lista av sträng')], body=[ReturnNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('element', TOKEN_IDENTIFIER), ExpressionPart('0', TOKEN_LITERAL_INT), ExpressionPart('från', TOKEN_FROM), ExpressionPart('källa', TOKEN_IDENTIFIER)]))], kind='hämta', return_type='sträng'))]
        self.assertParseEqual(source, expected)

    def test_rekgrej_definition(self):
        source = """\
sätt fakultet till rekgrej med n som heltal ger heltal
    om n är mindre än 2
        ge 1
    ge n gånger fakultet med n minus 1"""
        expected = [AssignNode(None, None, name='fakultet', value=FunctionDefNode(None, None, params=[('n', 'heltal')], body=[IfNode(None, None, conditions=[IfCondition(None, None, test=ExpressionPartsNode(None, None, parts=[ExpressionPart('n', TOKEN_IDENTIFIER), ExpressionPart('är', TOKEN_OP_IS), ExpressionPart('mindre', TOKEN_LESS), ExpressionPart('än', TOKEN_THAN), ExpressionPart('2', TOKEN_LITERAL_INT)]), block=[ReturnNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('1', TOKEN_LITERAL_INT)]))])]), ReturnNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('n', TOKEN_IDENTIFIER), ExpressionPart('gånger', TOKEN_OP_MUL), ExpressionPart('fakultet', TOKEN_IDENTIFIER), ExpressionPart('med', TOKEN_WITH), ExpressionPart('n', TOKEN_IDENTIFIER), ExpressionPart('minus', TOKEN_OP_SUB), ExpressionPart('1', TOKEN_LITERAL_INT)]))], kind='rek', return_type='heltal'))]
        self.assertParseEqual(source, expected)

# --- open file ---
    def test_open_file(self):
        source = "öppna fil.txt som input"
        expected = [AssignNode(None, None, name='input', value=FunctionCallNode(None, None, name='öppna', args=[VarAccessNode(None, None, 'fil.txt'), StringNode(None, None, 'läsning')]))]
        self.assertParseEqual(source, expected)

# --- kopia av ---
    def test_kopia_av(self):
        source = "sätt uppdaterad till kopia av p med ålder 40"
        expected = [CopyWithPropNode(None, None, name='uppdaterad', source='p', updates=[('ålder', IntNode(None, None, '40'))])]
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