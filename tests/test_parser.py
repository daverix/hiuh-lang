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
            PrintNode(StringNode("hejsan")),
            PrintNode(StringNode("\n")),
            PrintNode(StringNode("hoppsan"))
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_variables_boolean_or_comparison(self):
        source = "sätt x till SANT\nsätt y till x eller FALSKT"
        expected = [
            AssignNode("x", BoolNode(True)),
            AssignNode("y", ComparisonNode(VarAccessNode("x"), "eller", BoolNode(False)))
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_variables_boolean_and_comparison(self):
        source = "sätt x till SANT\nsätt y till x och FALSKT"
        expected = [
            AssignNode("x", BoolNode(True)),
            AssignNode("y", ComparisonNode(VarAccessNode("x"), "och", BoolNode(False)))
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_variables_boolean_greater_than(self):
        source = "sätt a till 3\nsätt b till a större än 2"
        expected = [
            AssignNode("a", IntNode(3)),
            AssignNode("b", ComparisonNode(VarAccessNode("a"), "större än", IntNode(2)))
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_variables_boolean_greater_than_or_equal(self):
        source = "sätt a till 3\nsätt b till a större än eller lika med 2"
        expected = [
            AssignNode("a", IntNode(3)),
            AssignNode("b", ComparisonNode(VarAccessNode("a"), "större än eller lika med", IntNode(2)))
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_variables_boolean_equal(self):
        source = "sätt a till 3\nsätt b till a lika med 2"
        expected = [
            AssignNode("a", IntNode(3)),
            AssignNode("b", ComparisonNode(VarAccessNode("a"), "lika med", IntNode(2)))
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_variables_boolean_less_than(self):
        source = "sätt a till 3\nsätt b till a mindre än 2"
        expected = [
            AssignNode("a", IntNode(3)),
            AssignNode("b", ComparisonNode(VarAccessNode("a"), "mindre än", IntNode(2)))
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_variables_boolean_less_than_or_equal(self):
        source = "sätt a till 3\nsätt b till a mindre än eller lika med 2"
        expected = [
            AssignNode("a", IntNode(3)),
            AssignNode("b", ComparisonNode(VarAccessNode("a"), "mindre än eller lika med", IntNode(2)))
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_variables_string_when_variable_not_found(self):
        source = "sätt x till SANT\nsätt b till a större än 2"
        expected = [
            AssignNode("x", BoolNode(True)),
            AssignNode("b", StringNode("a större än 2"))
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_variables_math_plus(self):
        source = "sätt c till 2 plus 3"
        expected = [
            AssignNode("c", AddNode(IntNode(2), IntNode(3)))
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_variables_math_subtract(self):
        source = "sätt c till 2 minus 3"
        expected = [
            AssignNode("c", SubNode(IntNode(2), IntNode(3)))
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_variables_math_multiply(self):
        source = "sätt c till 2 gånger 3"
        expected = [
            AssignNode("c", MulNode(IntNode(2), IntNode(3)))
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_variables_math_divide(self):
        source = "sätt c till 2 delat med 3"
        expected = [
            AssignNode("c", DivNode(IntNode(2), IntNode(3)))
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_variables_math_multiplication_before_addition(self):
        source = "sätt c till 3 plus 4 gånger 2"
        expected = [
            AssignNode("c", AddNode(IntNode(3), MulNode(IntNode(4), IntNode(2))))
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_variables_math_division_before_addition(self):
        source = "sätt c till 3 plus 4 delat med 2"
        expected = [
            AssignNode("c", AddNode(IntNode(3), DivNode(IntNode(4), IntNode(2))))
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_variables_float_section(self):
        source = "sätt y till 3,4"
        expected = [
            AssignNode("y", FloatNode("3,4"))
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_variables_list_with_initial_values(self):
        source = "sätt min lista till lista med 1, 2, 3"
        expected = [
            AssignNode("min lista", FunctionCallNode("lista", [
                IntNode(1),
                IntNode(2),
                IntNode(3)
            ]))
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_variables_list_empty(self):
        source = "sätt min lista till lista"
        expected = [
            AssignNode("min lista", FunctionCallNode("lista", []))
        ]
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
            AssignNode("ålder", IntNode(38), target_type="person")
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_if_statement_section(self):
        source = "om x är större än 2\n    skriv större\nannars\n    skriv mindre"
        expected = [
            IfNode(
                condition=ComparisonNode(VarAccessNode("x"), "större än", IntNode(2)),
                true_block=[PrintNode(StringNode("större"))],
                false_block=[PrintNode(StringNode("mindre"))]
            )
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_stdin_section(self):
        source = "sätt t till nästa rad från inmatning"
        ast = self.parse_source(source)
        self.assertIsInstance(ast[0], AssignNode)

    def test_error_handling_section(self):
        source = "prova\n    kasta fel\nfånga fel\n    skriv fel"
        expected = [
            TryCatchNode(
                try_block=[UnaryOpNode("kasta", StringNode("fel"))],
                error_var="fel",
                catch_block=[PrintNode(VarAccessNode("fel"))]
            )
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_comments_section(self):
        source = ". skriver\nskriv hej"
        expected = [
            PrintNode(StringNode("hej"))
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_multiple_indents_nested(self):
        source = "om SANT\n    skriv nivå 1\n    om SANT\n        skriv nivå 2"
        expected = [
            IfNode(
                condition=BoolNode(True),
                true_block=[
                    PrintNode(StringNode("nivå 1")),
                    IfNode(
                        condition=BoolNode(True),
                        true_block=[PrintNode(StringNode("nivå 2"))],
                        false_block=None
                    )
                ],
                false_block=None
            )
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_property_access_with_from_keyword(self):
        """Verify that 'fält från objekt' produces a VarAccessNode with a target."""
        # Pre-define the variable so the scope check doesn't trigger a string fallback
        source = "typ person med namn\nsätt p till person med David\nskriv namn från p"
        expected = [
            TypeDefNode("person", ["namn"]),
            AssignNode("p", FunctionCallNode("person", [StringNode("David")])),
            PrintNode(VarAccessNode("namn", "p"))
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_list_index_set_and_get_ast(self):
        """Verify the AST structure for element [n] i/från [lista]."""
        source = (
            "sätt min lista till lista med röd, grön\n"
            "sätt element 0 i min lista till blå\n"
            "skriv element 0 från min lista"
        )
        # Note: 'röd' and 'grön' fall back to StringNodes because they aren't variables
        expected = [
            AssignNode(name='min lista', value=FunctionCallNode(name='lista', args=[StringNode(value='röd'), StringNode(value='grön')]), target_type=None),
            AssignNode(name='0', value=StringNode(value='blå'), target_type='min lista'),
            PrintNode(value=VarAccessNode(name='0', target='min lista'))
        ]
        self.assertEqual(self.parse_source(source), expected)

    def test_greedy_expression_stops_before_preposition(self):
        """Pinpoint: Does greedy expression stop before 'från'?"""
        # We simulate the call made by parse_remove()
        source = "banan från frukter"
        tokens = self.tokenizer.tokenize(source)
        parser = Parser(tokens)

        # We manually call the greedy method to see what it gobbles
        node = parser.parse_greedy_expression()

        # 1. It should only return "banan"
        self.assertIsInstance(node, StringNode)
        self.assertEqual(node.value, "banan")

        # 2. CRITICAL: The next token should be 'från'
        self.assertEqual(parser.peek().type, "T_KEYWORD_FROM",
                         f"Parser consumed too much! Next token is {parser.peek()}")

    def test_greedy_expression_with_multiword_stops(self):
        """Pinpoint: Does it handle multi-word values but still stop at 'från'?"""
        source = "en gul banan från frukter"
        tokens = self.tokenizer.tokenize(source)
        parser = Parser(tokens)

        node = parser.parse_greedy_expression()

        self.assertEqual(node.value, "en gul banan")
        self.assertEqual(parser.peek().type, "T_KEYWORD_FROM")

    def test_remove_following_another_statement(self):
        """Pinpoint: Does a previous statement interfere with 'ta bort'?"""
        source = "sätt x till 1\nta bort banan från frukter"
        nodes = self.parse_source(source)
        # nodes[0] is AssignNode
        # nodes[1] should be RemoveValueNode
        self.assertIsInstance(nodes[1], RemoveValueNode)
        self.assertEqual(nodes[1].value.value, "banan")
        self.assertEqual(nodes[1].target_list, "frukter")

    def test_remove_with_multiword_target(self):
        """Pinpoint: Does 'ta bort' handle multi-word list names?"""
        source = "ta bort banan från min stora lista"
        nodes = self.parse_source(source)
        self.assertEqual(nodes[0].target_list, "min stora lista")

if __name__ == '__main__':
    unittest.main()
