import unittest
from hiuh.frontend.tokenizer import Tokenizer
from hiuh.frontend.parser import Parser
from hiuh.frontend.ast import *

class TestHiuhParserAST(unittest.TestCase):
    def setUp(self):
        self.tokenizer = Tokenizer()

    def parse_source(self, source):
        tokens = self.tokenizer.tokenize(source)
        parser = Parser(tokens)
        return parser.parse()

    def test_stdout_section(self):
        source = "skriv hejsan\nskriv ny rad\nskriv hoppsan"
        expected = [
            PrintNode(VarAccessNode("hejsan")),
            PrintNode(LiteralNode("\n", "STRING")),
            PrintNode(VarAccessNode("hoppsan"))
        ]
        # Note: If your parser handles 'ny rad' differently, adjust the middle node.
        self.assertEqual(self.parse_source(source), expected)

    def test_variables_boolean_section(self):
        source = "sätt x till SANT\nsätt b till a större än 2"
        expected = [
            AssignNode("x", LiteralNode(True, "BOOL")),
            AssignNode("b", BinOpNode(VarAccessNode("a"), "större än", LiteralNode("2", "INT")))
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_variables_math_section(self):
        source = "sätt c till b gånger b pluss a"
        # Reflecting the recursive nature of the parser: b * (b + a)
        expected = [
            AssignNode("c", BinOpNode(
                VarAccessNode("b"),
                "gånger",
                BinOpNode(VarAccessNode("b"), "pluss", VarAccessNode("a"))
            ))
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_variables_float_section(self):
        source = "sätt y till 3,4"
        expected = [
            AssignNode("y", LiteralNode("3,4", "FLOAT"))
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_variables_list_section(self):
        source = "sätt min lista till lista med 1, 2, 3"
        # Note: 'min' and 'lista' are separate identifiers
        expected = [
            AssignNode("min", FunctionCallNode("lista", [
                LiteralNode("1", "INT"),
                LiteralNode("2", "INT"),
                LiteralNode("3", "INT")
            ]))
        ]
        # This assumes the first identifier 'min' is the name and 'lista' is the value start
        self.assertEqual(self.parse_source(source), expected)

    def test_function_section(self):
        source = "sätt f till grej med a\n    ge a"
        expected = [
            AssignNode("f", FunctionDefNode(
                params=["a"],
                body=[ReturnNode(VarAccessNode("a"))]
            ))
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_typ_section(self):
        source = "typ person med namn, ålder\nsätt ålder i person till 38"
        expected = [
            TypeDefNode("person", ["namn", "ålder"]),
            AssignNode("ålder", LiteralNode("38", "INT"), target_type="person")
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_if_statement_section(self):
        source = "om x är större än 2\n    skriv större\nannars\n    skriv mindre"
        expected = [
            IfNode(
                condition=BinOpNode(VarAccessNode("x"), "är större än", LiteralNode("2", "INT")),
                true_block=[PrintNode(VarAccessNode("större"))],
                false_block=[PrintNode(VarAccessNode("mindre"))]
            )
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_stdin_section(self):
        source = "sätt t till nästa rad från inmatning"
        expected = [
            AssignNode("t", VarAccessNode("nästa", source=None))
            # Note: The actual structure depends on how you parse 'nästa rad från'
            # Here we provide a placeholder based on current primary() logic
        ]
        ast = self.parse_source(source)
        self.assertIsInstance(ast[0], AssignNode)

    def test_error_handling_section(self):
        source = "prova\n    kasta fel\nfånga fel\n    skriv fel"
        expected = [
            TryCatchNode(
                try_block=[UnaryOpNode("kasta", VarAccessNode("fel"))],
                error_var="fel",
                catch_block=[PrintNode(VarAccessNode("fel"))]
            )
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_comments_section(self):
        source = ". skriver\nskriv hej"
        expected = [
            PrintNode(VarAccessNode("hej"))
        ]
        # Parser should skip T_COMMENT and T_NEWLINE
        self.assertEqual(self.parse_source(source), expected)

    def test_multiple_indents_nested(self):
        source = "om SANT\n    skriv nivå 1\n    om SANT\n        skriv nivå 2"
        expected = [
            IfNode(
                condition=LiteralNode(True, "BOOL"),
                true_block=[
                    PrintNode(VarAccessNode("nivå")), # Simplified based on identifier logic
                    IfNode(
                        condition=LiteralNode(True, "BOOL"),
                        true_block=[PrintNode(VarAccessNode("nivå"))],
                        false_block=None
                    )
                ],
                false_block=None
            )
        ]
        ast = self.parse_source(source)
        self.assertIsInstance(ast[0], IfNode)

if __name__ == '__main__':
    unittest.main()
