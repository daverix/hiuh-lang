"""Tests for generic type support in parser and resolver."""
import os
import unittest
from hiuh.frontend.ast import *
from hiuh.frontend.module_registry import ModuleRegistry
from hiuh.frontend.parser import Parser
from hiuh.frontend.resolver import Resolver
from hiuh.frontend.tokenizer import Tokenizer

class TestGenericParser(unittest.TestCase):
    """Test parser output for generic type syntax (before resolver)."""

    def setUp(self):
        self.tokenizer = Tokenizer()

    def parse_source(self, source):
        tokens = self.tokenizer.tokenize(source)
        parser = Parser(tokens)
        return parser.parse()

    def strip_locations(self, node):
        if isinstance(node, list):
            return [self.strip_locations(child) for child in node]
        if isinstance(node, ExpressionPart):
            return node.value
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

    def test_typ_with_generic_type_params(self):
        """typ ordlista av K, V with multi-line body."""
        source = 'typ par av nyckeltyp, värdetyp\n    nyckel som nyckeltyp\n    värde som värdetyp'
        expected = [TypeDefNode(None, None, name='par', fields=[('nyckel', 'nyckeltyp'), ('värde', 'värdetyp')], type_params=['nyckeltyp', 'värdetyp'])]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_typ_with_nested_generic_field_type(self):
        """Field type with nested generics: lista av par av K, V."""
        source = 'typ par av K, V\n    nyckel som K\n    värde som V\n\ntyp ordlista av nyckeltyp, värdetyp\n    värden som lista av par av nyckeltyp, värdetyp\n    putta som grej'
        expected = [TypeDefNode(None, None, name='par', fields=[('nyckel', 'K'), ('värde', 'V')], type_params=['K', 'V']), TypeDefNode(None, None, name='ordlista', fields=[('värden', 'lista av par av nyckeltyp, värdetyp'), ('putta', 'grej')], type_params=['nyckeltyp', 'värdetyp'])]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_generic_function_def(self):
        """sätt fn till grej av T1, T2 (no params)."""
        source = 'sätt make till grej av K, V ger V\n    ge lista av heltal'
        expected = [AssignNode(None, None, name='make', value=FunctionDefNode(None, None, params=[], body=[ReturnNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('lista', 0), ExpressionPart('av', 0), ExpressionPart('heltal', 0)]))], is_infix=False, type_params=['K', 'V'], return_type='V'))]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_generic_function_def_with_params(self):
        """sätt fn till grej av T1, T2 med x som T1."""
        source = 'sätt make till grej av K, V med key som K ger V\n    ge key'
        expected = [AssignNode(None, None, name='make', value=FunctionDefNode(None, None, params=[('key', 'K')], body=[ReturnNode(None, None, value=ExpressionPartsNode(None, None, parts=[ExpressionPart('key', 0)]))], is_infix=False, type_params=['K', 'V'], return_type='V'))]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_lista_av_type_annotation(self):
        """sätt x till lista av heltal - expression parts preserved for resolver."""
        source = "sätt x till lista av heltal"
        expected = [AssignNode(None, None, name='x', value=ExpressionPartsNode(None, None, parts=[ExpressionPart('lista', 0), ExpressionPart('av', 0), ExpressionPart('heltal', 0)]))]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_lista_av_nested_type(self):
        """sätt x till lista av par av K, V."""
        source = 'typ par av K, V\n    nyckel som K\n    värde som V\n\nsätt x till lista av par av K, V'
        expected = [TypeDefNode(None, None, name='par', fields=[('nyckel', 'K'), ('värde', 'V')], type_params=['K', 'V']), AssignNode(None, None, name='x', value=ExpressionPartsNode(None, None, parts=[ExpressionPart('lista', 0), ExpressionPart('av', 0), ExpressionPart('par', 0), ExpressionPart('av', 0), ExpressionPart('K', 0), ExpressionPart(',', 0), ExpressionPart('V', 0)]))]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_function_call_generic(self):
        """sätt x till ny tom ordlista av sträng, heltal."""
        source = "sätt x till ny tom ordlista av sträng, heltal"
        expected = [AssignNode(None, None, name='x', value=ExpressionPartsNode(None, None, parts=[ExpressionPart('ny', 0), ExpressionPart('tom', 0), ExpressionPart('ordlista', 0), ExpressionPart('av', 0), ExpressionPart('sträng', 0), ExpressionPart(',', 0), ExpressionPart('heltal', 0)]))]
        self.assertNodesEqual(self.parse_source(source), expected)

class TestGenericResolver(unittest.TestCase):
    """Test resolver output for generic type expressions."""

    def setUp(self):
        self.tokenizer = Tokenizer()
        self.module_registry = ModuleRegistry("/tmp/test_symbols_generics")

    def parse_and_resolve(self, source, definitions=None):
        """Parse source, register definitions, resolve."""
        tokens = self.tokenizer.tokenize(source)
        parser = Parser(tokens)
        ast = parser.parse()
        resolver = Resolver(self.module_registry)
        resolver.discover_modules_from_ast("main", ast, ".")
        resolver.resolve_all()
        return resolver.get_ast("main")

    def strip_locations(self, node):
        if isinstance(node, list):
            return [self.strip_locations(child) for child in node]
        if isinstance(node, ExpressionPart):
            return node.value
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

    def test_lista_av_heltal_resolves_to_lista_call(self):
        """lista av heltal -> FunctionCallNode('lista', [])."""
        source = "sätt x till lista av heltal"
        expected = [AssignNode(None, None, name='x', value=FunctionCallNode(None, None, name='lista', args=[]))]
        self.assertNodesEqual(self.parse_and_resolve(source), expected)

    def test_lista_av_nested_generics_resolves_to_lista_call(self):
        """lista av par av K, V -> FunctionCallNode('lista', [])."""
        source = 'typ par av K, V\n    nyckel som K\n    värde som V\n\nsätt x till lista av par av K, V'
        expected = [TypeDefNode(None, None, name='par', fields=[('nyckel', 'K'), ('värde', 'V')], type_params=['K', 'V']), AssignNode(None, None, name='x', value=FunctionCallNode(None, None, name='lista', args=[]))]
        self.assertNodesEqual(self.parse_and_resolve(source), expected)

    def test_function_with_generic_call(self):
        """ny tom ordlista av sträng, heltal -> FunctionCallNode('ny tom ordlista', [])."""
        source = "sätt x till ny tom ordlista av sträng, heltal"
        expected = [AssignNode(None, None, name='x', value=StringNode(None, None, value='ny tom ordlista av sträng, heltal'))]
        self.assertNodesEqual(self.parse_and_resolve(source), expected)

    def test_function_with_generic_call_defined(self):
        """ny tom ordlista is defined -> FunctionCallNode('ny tom ordlista', [])."""
        source = '\nsätt ny tom ordlista till grej ger ordlista av sträng, heltal\n    ge lista av heltal\n\nsätt x till ny tom ordlista av sträng, heltal\n'
        expected = [AssignNode(None, None, name='ny tom ordlista', value=FunctionDefNode(None, None, params=[], body=[ReturnNode(None, None, value=FunctionCallNode(None, None, name='lista', args=[]))], is_infix=False, type_params=[], return_type='ordlista av sträng, heltal')), AssignNode(None, None, name='x', value=FunctionCallNode(None, None, name='ny tom ordlista', args=[]))]
        self.assertNodesEqual(self.parse_and_resolve(source), expected)

class TestInheritanceParser(unittest.TestCase):
    """Test parser for ärver (inheritance) syntax."""

    def setUp(self):
        self.tokenizer = Tokenizer()

    def parse_source(self, source):
        tokens = self.tokenizer.tokenize(source)
        parser = Parser(tokens)
        return parser.parse()

    def strip_locations(self, node):
        if isinstance(node, list):
            return [self.strip_locations(child) for child in node]
        if isinstance(node, ExpressionPart):
            return node.value
        if not hasattr(node, '__dict__'):
            return node
        result = {}
        for key, value in node.__dict__.items():
            if key in ('line', 'column', 'token'):
                continue
            result[key] = self.strip_locations(value)
        return result

    def assertNodesEqual(self, actual, expected):
        self.assertEqual(self.strip_locations(actual), self.strip_locations(expected))

    def test_simple_inheritance(self):
        source = """\
typ IntNod ärver BasNod
    värde som heltal"""
        expected = [TypeDefNode(None, None, name='IntNod', fields=[('värde', 'heltal')], parent_types=[('BasNod', [])])]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_inheritance_with_type_params(self):
        source = """\
typ ordlista av K, V ärver lista av par av K, V
    extra som heltal"""
        expected = [TypeDefNode(None, None, name='ordlista', fields=[('extra', 'heltal')], type_params=['K', 'V'], parent_types=[('lista', ['par', 'av', 'K', ',', 'V'])])]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_inheritance_without_generics(self):
        source = """\
typ personbil ärver fordon
    märke som sträng"""
        expected = [TypeDefNode(None, None, name='personbil', fields=[('märke', 'sträng')], parent_types=[('fordon', [])])]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_multiple_inheritance(self):
        source = """\
typ bil ärver fordon, ägodel
    märke som sträng"""
        expected = [TypeDefNode(None, None, name='bil', fields=[('märke', 'sträng')], parent_types=[('fordon', []), ('ägodel', [])])]
        self.assertNodesEqual(self.parse_source(source), expected)

class TestInheritanceResolver(unittest.TestCase):
    """Test resolver validates field collisions in inheritance."""

    def setUp(self):
        self.tokenizer = Tokenizer()

    def parse_and_resolve(self, source):
        tokens = self.tokenizer.tokenize(source)
        parser = Parser(tokens)
        ast = parser.parse()
        mr = ModuleRegistry("/tmp/test_inherit_resolve")
        resolver = Resolver(mr)
        resolver.discover_modules_from_ast("main", ast, ".")
        resolver.resolve_all()
        return resolver.get_ast("main")

    def test_field_collision_between_parents(self):
        source = 'typ A\n    x som heltal\n\ntyp B\n    x som sträng\n\ntyp C ärver A, B\n    y som heltal'
        with self.assertRaises(Exception) as ctx:
            self.parse_and_resolve(source)
        self.assertIn("x", str(ctx.exception))

    def test_field_collision_with_own_field(self):
        source = 'typ A\n    x som heltal\n\ntyp B ärver A\n    x som sträng'
        with self.assertRaises(Exception) as ctx:
            self.parse_and_resolve(source)
        self.assertIn("x", str(ctx.exception))
if __name__ == '__main__':
    unittest.main()