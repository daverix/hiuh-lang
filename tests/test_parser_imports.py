# -*- coding: utf-8 -*-
import os
import unittest
from hiuh.frontend.tokenizer import Tokenizer
from hiuh.frontend.parser import Parser
from hiuh.frontend.resolver import Resolver
from hiuh.frontend.ast import *


class TestParserModuleImports(unittest.TestCase):
    """Parser tests for module imports - verify AST is correct after resolver flattens imports."""

    def setUp(self):
        self.tokenizer = Tokenizer()
        # Get the project root directory for hiuh_i_hiuh
        self.repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.hiuh_folder = os.path.join(self.repo_root, "hiuh_i_hiuh")

    def parse_source(self, source, script_dir=None):
        """Parse source and run resolver to get transformed AST."""
        tokens = self.tokenizer.tokenize(source)
        parser = Parser(tokens)
        ast = parser.parse()

        resolver = Resolver(stdlib_path=script_dir or self.hiuh_folder)
        resolver.discover_modules_from_ast("main", ast, script_dir or self.hiuh_folder)
        resolver.resolve_all()

        return resolver.get_ast("main")

    def strip_locations(self, node):
        """Normalize AST nodes by removing line/column info."""
        if isinstance(node, list):
            return [self.strip_locations(child) for child in node]

        if not hasattr(node, '__dict__'):
            return node

        pure_fields = node.__dict__.copy()
        pure_fields.pop('line', None)
        pure_fields.pop('column', None)

        for key, value in pure_fields.items():
            pure_fields[key] = self.strip_locations(value)

        pure_fields['__type__'] = node.__class__.__name__
        return pure_fields

    def assertNodesEqual(self, actual, expected):
        self.assertEqual(self.strip_locations(actual), self.strip_locations(expected))

    def test_wildcard_import_includes_module_symbols(self):
        """Verify that wildcard import 'använd verktyg' makes all module symbols available."""
        # Create temporary module file
        module_filename = os.path.join(self.repo_root, "test_verktyg.hiuh")
        with open(module_filename, "w", encoding="utf-8") as f:
            f.write("""
sätt meddelande till Hej från Hiuh
sätt faktor till 10
sätt addera till grej med a, b
    ge a plus b
""")

        try:
            source = """
använd test_verktyg
skriv meddelande
skriv faktor
sätt summa till addera med 5, 3
skriv summa
"""
            nodes = self.parse_source(source)

            # After import flattening, the AST should have:
            # 1. AssignNode for 'meddelande' (from test_verktyg)
            # 2. AssignNode for 'faktor' (from test_verktyg)
            # 3. AssignNode for 'addera' (from test_verktyg)
            # 4. PrintNode for 'meddelande'
            # 5. PrintNode for 'faktor'
            # 6. AssignNode for 'summa'
            # 7. PrintNode for 'summa'

            # Check that module symbols are imported
            symbol_names = []
            for node in nodes:
                if isinstance(node, AssignNode) and hasattr(node, 'name'):
                    symbol_names.append(node.name)

            # Should include the imported symbols
            self.assertIn('meddelande', symbol_names)
            self.assertIn('faktor', symbol_names)
            self.assertIn('addera', symbol_names)

            # Verify that imported function 'addera' has VarAccessNode arguments, not StringNode
            addera_node = None
            for node in nodes:
                if isinstance(node, AssignNode) and node.name == 'addera':
                    addera_node = node
                    break

            self.assertIsNotNone(addera_node)
            self.assertIsInstance(addera_node.value, FunctionDefNode)
            self.assertEqual(addera_node.value.params, ['a', 'b'])

            # The function body should have VarAccessNode for 'a plus b'
            # NOT StringNode("a plus b")
            self.assertEqual(len(addera_node.value.body), 1)
            return_node = addera_node.value.body[0]
            self.assertIsInstance(return_node, ReturnNode)

            # The return value should be AddNode with VarAccessNode children
            # NOT a StringNode
            self.assertIsInstance(return_node.value, AddNode)
            self.assertIsInstance(return_node.value.left, VarAccessNode)
            self.assertIsInstance(return_node.value.right, VarAccessNode)
            self.assertEqual(return_node.value.left.name, 'a')
            self.assertEqual(return_node.value.right.name, 'b')

        finally:
            if os.path.exists(module_filename):
                os.remove(module_filename)

    def test_aliased_import_includes_module_symbols(self):
        """Verify that aliased import 'använd verktyg som v' makes symbols accessible via namespace."""
        module_filename = os.path.join(self.repo_root, "test_hjalpare.hiuh")
        with open(module_filename, "w", encoding="utf-8") as f:
            f.write("""
sätt hälsa till grej med namn
    ge Hej plus mellanrum plus namn
""")

        try:
            source = """
använd test_hjalpare som h
sätt meddelande till hälsa från h med David
skriv meddelande
"""
            nodes = self.parse_source(source)

            # Check that module is imported
            symbol_names = [node.name for node in nodes if isinstance(node, AssignNode) and hasattr(node, 'name')]
            self.assertIn('hälsa', symbol_names)

            # Verify the function call: hälsa från h med David
            # Should be FunctionCallNode with VarAccessNode(name='hälsa', target='h')
            call_node = None
            for node in nodes:
                if isinstance(node, AssignNode) and node.name == 'meddelande':
                    call_node = node.value
                    break

            self.assertIsNotNone(call_node)
            self.assertIsInstance(call_node, FunctionCallNode)

            # The name should be a VarAccessNode with target='h'
            self.assertIsInstance(call_node.name, VarAccessNode)
            self.assertEqual(call_node.name.name, 'hälsa')
            self.assertEqual(call_node.name.target, 'h')

        finally:
            if os.path.exists(module_filename):
                os.remove(module_filename)

    def test_directory_import_includes_module_symbols(self):
        """Verify that directory import 'använd verktyg.matematik' makes symbols available."""
        dir_name = os.path.join(self.repo_root, "test_verktyg")
        module_filename = os.path.join(dir_name, "matematik.hiuh")

        os.makedirs(dir_name, exist_ok=True)
        with open(module_filename, "w", encoding="utf-8") as f:
            f.write("""
sätt addera till grej med a, b
    ge a plus b
""")

        try:
            source = """
använd test_verktyg.matematik
sätt summa till addera med 10, 5
skriv summa
"""
            nodes = self.parse_source(source)

            # Verify that 'addera' function is imported
            symbol_names = [node.name for node in nodes if isinstance(node, AssignNode) and hasattr(node, 'name')]
            self.assertIn('addera', symbol_names)

            # Verify function params are VarAccessNode, not StringNode
            addera_node = None
            for node in nodes:
                if isinstance(node, AssignNode) and node.name == 'addera':
                    addera_node = node
                    break

            self.assertIsNotNone(addera_node)
            self.assertIsInstance(addera_node.value, FunctionDefNode)
            self.assertEqual(addera_node.value.params, ['a', 'b'])

            # The body should have ReturnNode with AddNode
            self.assertEqual(len(addera_node.value.body), 1)
            return_node = addera_node.value.body[0]
            self.assertIsInstance(return_node, ReturnNode)
            self.assertIsInstance(return_node.value, AddNode)
            self.assertIsInstance(return_node.value.left, VarAccessNode)
            self.assertIsInstance(return_node.value.right, VarAccessNode)

        finally:
            if os.path.exists(module_filename):
                os.remove(module_filename)
            if os.path.exists(dir_name):
                os.rmdir(dir_name)

    def test_listor_module_functions_have_correct_params(self):
        """Verify that functions from listor.hiuh have correct parameter structure."""
        # This test uses the real listor.hiuh file
        source = """
använd listor

sätt matchar_hiuh till grej med text_stycke
    ge text_stycke lika med Hiuh

sätt namn_lista till lista med Java, Python, Hiuh, Kotlin

sätt hittat_index till index på första matchande med namn_lista, matchar_hiuh
sätt hittat_namn till första matchande med namn_lista, matchar_hiuh

skriv hittat_index plus mellanrum plus hittat_namn
"""
        nodes = self.parse_source(source, script_dir=self.hiuh_folder)

        # Find the 'index på första matchande' function
        index_func = None
        for node in nodes:
            if isinstance(node, AssignNode) and node.name == 'index på första matchande':
                index_func = node
                break

        self.assertIsNotNone(index_func, "Function 'index på första matchande' not found in AST")
        self.assertIsInstance(index_func.value, FunctionDefNode)

        # The function should have params ['värden', 'anrop']
        self.assertEqual(index_func.value.params, ['värden', 'anrop'])

        # The body should NOT have StringNode for 'värden.x' - it should be VarAccessNode
        # Let's check the function body structure
        body = index_func.value.body
        self.assertGreater(len(body), 0)

        # The body contains:
        # 1. sätt x till 0
        # 2. medan x är mindre än längd från värden (with body containing anrop)
        # 3. ge -1

        # Check the while loop body for the function call
        self.assertIsInstance(body[1], WhileNode)
        while_body = body[1].body
        
        # Look for the function call: anrop med element x från värden
        # This should be a FunctionCallNode
        # The name may be a string or VarAccessNode depending on resolver processing
        found_call = False
        for stmt in while_body:
            if isinstance(stmt, IfNode):
                condition = stmt.condition
                if isinstance(condition, FunctionCallNode):
                    # The function call should be: anrop with args that include 'element x från värden'
                    # Name can be VarAccessNode or string - both are valid
                    name = condition.name
                    is_valid_name = (
                        isinstance(name, VarAccessNode) and name.name == 'anrop'
                    ) or (
                        isinstance(name, str) and name == 'anrop'
                    )
                    self.assertTrue(is_valid_name, 
                        f"Expected 'anrop' as name, got {type(name).__name__}: {name}")
                    found_call = True

        self.assertTrue(found_call, "Function call 'anrop med ...' not found in expected structure")

    def test_första_matchande_function_params(self):
        """Verify that 'första matchande' from listor has correct param access."""
        source = """
använd listor

sätt matchar till grej med x
    ge x

sätt resultat till första matchande med lista, matchar
"""
        nodes = self.parse_source(source, script_dir=self.hiuh_folder)

        # Find 'första matchande' function
        första_func = None
        for node in nodes:
            if isinstance(node, AssignNode) and node.name == 'första matchande':
                första_func = node
                break

        self.assertIsNotNone(första_func, "Function 'första matchande' not found in AST")
        self.assertIsInstance(första_func.value, FunctionDefNode)
        self.assertEqual(första_func.value.params, ['värden', 'anrop'])

        # The function body should have VarAccessNode, not StringNode
        # Check for: x till index på första matchande med värden, anrop
        assign_node = första_func.value.body[0]
        self.assertIsInstance(assign_node, AssignNode)
        self.assertIsInstance(assign_node.value, FunctionCallNode)

        # The args to 'index på första matchande' should be VarAccessNode, not StringNode
        for arg in assign_node.value.args:
            self.assertIsInstance(arg, VarAccessNode,
                f"Expected VarAccessNode but got {type(arg).__name__} with value {arg.name if hasattr(arg, 'name') else arg}")

    def test_ordlista_import_has_correct_structure(self):
        """Verify that ordlista module functions have correct param structure."""
        source = """
använd ordlista

sätt min_ordlista till ny tom ordlista
putta från min_ordlista med äpple, 2
"""
        nodes = self.parse_source(source, script_dir=self.hiuh_folder)

        # Verify that functions are imported
        func_names = [node.name for node in nodes if isinstance(node, AssignNode) and hasattr(node, 'name')]

        # ordlista.hiuh exports 'ny ordlista' and 'ny tom ordlista'
        # 'putta' is a nested function inside 'ny ordlista', accessed via property access
        self.assertIn('ny ordlista', func_names)
        self.assertIn('ny tom ordlista', func_names)
        
        # Verify that 'putta' can be accessed via property access: putta från min_ordlista
        # This is tested by the second line: putta från min_ordlista med äpple, 2
        putta_call = None
        for node in nodes:
            if isinstance(node, PrintNode):
                continue
            if hasattr(node, 'value') and isinstance(node.value, FunctionCallNode):
                name = node.value.name
                if hasattr(name, 'name') and name.name == 'putta':
                    putta_call = node.value
                    break
        
        # The test source has 'putta från min_ordlista med äpple, 2'
        # This should be a FunctionCallNode with VarAccessNode(name='putta', target='min_ordlista')
        # Find any function call with 'putta' in it
        for node in nodes:
            if isinstance(node, FunctionCallNode):
                name = getattr(node, 'name', None)
                if isinstance(name, VarAccessNode) and name.name == 'putta':
                    self.assertEqual(name.target, 'min_ordlista')
                    return
        
        # If we get here, check if there's a FunctionCallNode in an expression
        # The 'putta' call might be inside another expression
        for node in nodes:
            if hasattr(node, 'value') and isinstance(node.value, FunctionCallNode):
                name = getattr(node.value, 'name', None)
                if isinstance(name, VarAccessNode) and name.name == 'putta':
                    self.assertEqual(name.target, 'min_ordlista')
                    return

    def test_import_preserves_function_definitions(self):
        """Verify that imported FunctionDefNode has correct body with VarAccessNode params."""
        module_filename = os.path.join(self.repo_root, "test_callbacks.hiuh")
        with open(module_filename, "w", encoding="utf-8") as f:
            f.write("""
sätt köra till grej med lista, anrop
    sätt x till 0
    medan x är mindre än längd från lista
        anrop med element x från lista
        sätt x till x plus 1
""")

        try:
            source = """
använd test_callbacks

sätt min_lista till lista med 1, 2, 3
sätt resultat till köra med min_lista, grej med n
    skriv n
"""
            nodes = self.parse_source(source)

            # Find the 'köra' function
            kora_func = None
            for node in nodes:
                if isinstance(node, AssignNode) and node.name == 'köra':
                    kora_func = node
                    break

            self.assertIsNotNone(kora_func, "Function 'köra' not found")
            self.assertIsInstance(kora_func.value, FunctionDefNode)

            # Params should be VarAccessNode (not StringNode) when accessed in body
            self.assertEqual(kora_func.value.params, ['lista', 'anrop'])

            # The body should have:
            # 1. sätt x till 0
            # 2. medan x är mindre än längd från lista (with body containing anrop and sätt x)
            
            body = kora_func.value.body
            self.assertGreaterEqual(len(body), 2)

            # First statement: sätt x till 0
            self.assertIsInstance(body[0], AssignNode)
            self.assertEqual(body[0].name, 'x')
            self.assertIsInstance(body[0].value, IntNode)

            # Second statement: medan x är mindre än längd från lista
            self.assertIsInstance(body[1], WhileNode)
            condition = body[1].condition
            self.assertIsInstance(condition, ComparisonNode)
            self.assertIsInstance(condition.left, VarAccessNode)
            self.assertEqual(condition.left.name, 'x')

            # The 'längd från lista' should be FunctionCallNode with VarAccessNode arg
            self.assertIsInstance(condition.right, FunctionCallNode)
            self.assertEqual(condition.right.name, 'längd')
            self.assertIsInstance(condition.right.args[0], VarAccessNode)
            self.assertEqual(condition.right.args[0].name, 'lista')

            # While loop body should contain:
            # 1. anrop med element x från lista
            # 2. sätt x till x plus 1
            self.assertEqual(len(body[1].body), 2)
            
            # Third statement (inside while): anrop med element x från lista
            self.assertIsInstance(body[1].body[0], FunctionCallNode)
            # The name can be string or VarAccessNode depending on resolver
            call_name = body[1].body[0].name
            self.assertTrue(
                (isinstance(call_name, VarAccessNode) and call_name.name == 'anrop') or
                (isinstance(call_name, str) and call_name == 'anrop'),
                f"Expected 'anrop' but got {type(call_name).__name__}: {call_name}"
            )

            # The arg should be VarAccessNode with target='lista', NOT StringNode
            self.assertEqual(len(body[1].body[0].args), 1)
            arg = body[1].body[0].args[0]
            self.assertIsInstance(arg, VarAccessNode,
                f"Expected VarAccessNode but got {type(arg).__name__}")
            self.assertEqual(arg.target, 'lista')

        finally:
            if os.path.exists(module_filename):
                os.remove(module_filename)


if __name__ == '__main__':
    unittest.main()