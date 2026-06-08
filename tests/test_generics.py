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
        source = """typ par av nyckeltyp, värdetyp
    nyckel som nyckeltyp
    värde som värdetyp"""
        expected = [
            TypeDefNode(
                name="par",
                fields=[("nyckel", "nyckeltyp"), ("värde", "värdetyp")],
                type_params=["nyckeltyp", "värdetyp"]
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_typ_with_nested_generic_field_type(self):
        """Field type with nested generics: lista av par av K, V."""
        source = """typ ordlista av nyckeltyp, värdetyp
    värden som lista av par av nyckeltyp, värdetyp
    putta som grej"""
        expected = [
            TypeDefNode(
                name="ordlista",
                fields=[
                    ("värden", "lista av par av nyckeltyp, värdetyp"),
                    ("putta", "grej")
                ],
                type_params=["nyckeltyp", "värdetyp"]
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_generic_function_def(self):
        """sätt fn till grej av T1, T2 (no params)."""
        source = """sätt make till grej av K, V
    ge lista"""
        expected = [
            AssignNode(
                name="make",
                value=FunctionDefNode(
                    params=[],
                    body=[ReturnNode(value=ExpressionPartsNode(parts=["lista"]))],
                    is_infix=False,
                    type_params=["K", "V"]
                )
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_generic_function_def_with_params(self):
        """sätt fn till grej av T1, T2 med x som T1."""
        source = """sätt make till grej av K, V med key som K
    ge key"""
        expected = [
            AssignNode(
                name="make",
                value=FunctionDefNode(
                    params=[("key", "K")],
                    body=[ReturnNode(value=ExpressionPartsNode(parts=["key"]))],
                    is_infix=False,
                    type_params=["K", "V"]
                )
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_lista_av_type_annotation(self):
        """sätt x till lista av heltal - expression parts preserved for resolver."""
        source = "sätt x till lista av heltal"
        expected = [
            AssignNode(
                name="x",
                value=ExpressionPartsNode(parts=["lista", "av", "heltal"])
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_lista_av_nested_type(self):
        """sätt x till lista av par av K, V."""
        source = "sätt x till lista av par av K, V"
        expected = [
            AssignNode(
                name="x",
                value=ExpressionPartsNode(parts=["lista", "av", "par", "av", "K", ",", "V"])
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_function_call_generic(self):
        """sätt x till ny tom ordlista av sträng, heltal."""
        source = "sätt x till ny tom ordlista av sträng, heltal"
        expected = [
            AssignNode(
                name="x",
                value=ExpressionPartsNode(parts=["ny", "tom", "ordlista", "av", "sträng", ",", "heltal"])
            )
        ]
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
        expected = [
            AssignNode(
                name="x",
                value=FunctionCallNode(name="lista", args=[])
            )
        ]
        self.assertNodesEqual(self.parse_and_resolve(source), expected)

    def test_lista_av_nested_generics_resolves_to_lista_call(self):
        """lista av par av K, V -> FunctionCallNode('lista', [])."""
        source = "sätt x till lista av par av K, V"
        expected = [
            AssignNode(
                name="x",
                value=FunctionCallNode(name="lista", args=[])
            )
        ]
        self.assertNodesEqual(self.parse_and_resolve(source), expected)

    def test_function_with_generic_call(self):
        """ny tom ordlista av sträng, heltal -> FunctionCallNode('ny tom ordlista', [])."""
        source = "sätt x till ny tom ordlista av sträng, heltal"
        # 'ny tom ordlista' is not defined, so it should stringify
        expected = [
            AssignNode(
                name="x",
                value=StringNode(value="ny tom ordlista av sträng, heltal")
            )
        ]
        self.assertNodesEqual(self.parse_and_resolve(source), expected)

    def test_function_with_generic_call_defined(self):
        """ny tom ordlista is defined -> FunctionCallNode('ny tom ordlista', [])."""
        source = """
sätt ny tom ordlista till grej
    ge lista

sätt x till ny tom ordlista av sträng, heltal
"""
        expected = [
            AssignNode(
                name="ny tom ordlista",
                value=FunctionDefNode(
                    params=[],
                    body=[ReturnNode(value=FunctionCallNode(name="lista", args=[]))],
                    is_infix=False,
                    type_params=[]
                )
            ),
            AssignNode(
                name="x",
                value=FunctionCallNode(name="ny tom ordlista", args=[])
            )
        ]
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
        source = "typ IntNod ärver BasNod\n    värde som heltal"
        expected = [
            TypeDefNode(
                name="IntNod",
                fields=[("värde", "heltal")],
                parent_types=[("BasNod", [])],
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_inheritance_with_type_params(self):
        source = "typ ordlista av K, V ärver lista av par av K, V\n    extra som heltal"
        expected = [
            TypeDefNode(
                name="ordlista",
                fields=[("extra", "heltal")],
                type_params=["K", "V"],
                parent_types=[("lista", ["par", "av", "K", ",", "V"])],
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_inheritance_without_generics(self):
        source = "typ personbil ärver fordon\n    märke som sträng"
        expected = [
            TypeDefNode(
                name="personbil",
                fields=[("märke", "sträng")],
                parent_types=[("fordon", [])],
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_multiple_inheritance(self):
        source = "typ bil ärver fordon, ägodel\n    märke som sträng"
        expected = [
            TypeDefNode(
                name="bil",
                fields=[("märke", "sträng")],
                parent_types=[("fordon", []), ("ägodel", [])],
            )
        ]
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
        source = """typ A
    x som heltal

typ B
    x som sträng

typ C ärver A, B
    y som heltal"""
        with self.assertRaises(Exception) as ctx:
            self.parse_and_resolve(source)
        self.assertIn("x", str(ctx.exception))

    def test_field_collision_with_own_field(self):
        source = """typ A
    x som heltal

typ B ärver A
    x som sträng"""
        with self.assertRaises(Exception) as ctx:
            self.parse_and_resolve(source)
        self.assertIn("x", str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
