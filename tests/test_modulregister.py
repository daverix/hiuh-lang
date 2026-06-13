"""Tests for modulregister.hiuh through the interpreter."""

import os
import unittest

from hiuh.frontend.module_registry import ModuleRegistry
from hiuh.frontend.parser import Parser
from hiuh.frontend.resolver import Resolver
from hiuh.frontend.tokenizer import Tokenizer


class TestHiuhModulregister(unittest.TestCase):
    """Test modulregister.hiuh functions through the interpreter."""

    def setUp(self):
        self.tokenizer = Tokenizer()
        self._repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _run_module(self, source):
        from hiuh.backend.interpreter.interpreter import Interpreter, ReturnException

        mr = ModuleRegistry("/tmp/test_modulregister")
        resolver = Resolver(mr, os.path.join(self._repo_root, "hiuh_i_hiuh"))

        tokens_py = self.tokenizer.tokenize(source)
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
            return e.value
        return None

    def test_nytt_register_creates_empty_dict(self):
        source = (
            "använd modulregister\n"
            "sätt reg till nytt register\n"
            "ge reg\n"
        )
        result = self._run_module(source)
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 0)

    def test_registrera_modul_adds_entry(self):
        source = (
            "använd modulregister\n"
            "sätt reg till nytt register\n"
            "registrera modul med testmodul, sökväg, reg\n"
            "ge reg\n"
        )
        result = self._run_module(source)
        self.assertIn("testmodul", result)
        modul = result["testmodul"]
        self.assertEqual(modul["namn"], "testmodul")
        self.assertEqual(modul["sökväg"], "sökväg")

    def test_hämta_modul_returns_module(self):
        source = (
            "använd modulregister\n"
            "sätt reg till nytt register\n"
            "registrera modul med test, väg, reg\n"
            "sätt resultat till hämta modul med test, reg\n"
            "ge resultat\n"
        )
        result = self._run_module(source)
        self.assertIsNotNone(result)
        self.assertEqual(result["namn"], "test")

    def test_hämta_modul_missing_returns_none(self):
        source = (
            "använd modulregister\n"
            "sätt reg till nytt register\n"
            "sätt resultat till hämta modul med saknas, reg\n"
            "ge resultat\n"
        )
        result = self._run_module(source)
        # 'inget av modulelement' stringifies to itself at runtime
        self.assertEqual(result, "inget av modulelement")

    def test_registrera_symbol_and_hämta(self):
        source = (
            "använd modulregister\n"
            "sätt reg till nytt register\n"
            "registrera modul med minmodul, väg, reg\n"
            "sätt sym till symbolelement med hej, var, minmodul\n"
            "registrera symbol med minmodul, sym, reg\n"
            "sätt resultat till hämta symbol med hej, minmodul, reg\n"
            "ge resultat\n"
        )
        result = self._run_module(source)
        self.assertIsNotNone(result)
        self.assertEqual(result["namn"], "hej")
        self.assertEqual(result["sort"], "var")


if __name__ == '__main__':
    unittest.main()
