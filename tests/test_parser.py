import os
import unittest
from hiuh.frontend.tokenizer import Tokenizer
from hiuh.frontend.parser import Parser
from hiuh.frontend.resolver import Resolver
from hiuh.frontend.ast import *

class TestHiuhParserAST(unittest.TestCase):
    def setUp(self):
        self.tokenizer = Tokenizer()
        self.repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.hiuh_folder = os.path.join(self.repo_root, "hiuh_i_hiuh")

    def parse_source(self, source, stdlib_path=None, modules=None):
        """Parse source and run resolver to get transformed AST.
        
        Args:
            source: Source code string
            stdlib_path: Path to stdlib directory (optional)
            modules: Dict of {name: source_code} for in-memory module definitions
        """
        tokens = self.tokenizer.tokenize(source)
        parser = Parser(tokens)
        ast = parser.parse()
        
        # Run resolver to validate and transform symbols
        resolver = Resolver(stdlib_path=stdlib_path)
        resolver.discover_modules_from_ast("main", ast, stdlib_path or self.hiuh_folder)
        
        # Register in-memory module sources if provided
        if modules:
            for name, module_source in modules.items():
                resolver.register_module_source(name, module_source)
        
        resolver.discover_imports("main")
        resolver.resolve_all()
        
        # Return the resolver's transformed AST, not the original
        return resolver.get_ast("main")

    def strip_locations(self, node):
        if isinstance(node, list):
            return [self.strip_locations(child) for child in node]

        if not hasattr(node, '__dict__'):
            return node

        pure_fields = node.__dict__.copy()

        # 1. Simply wipe the primitive coordinate fields away to normalize the trees!
        pure_fields.pop('line', None)
        pure_fields.pop('column', None)

        # 2. Recursively process child blocks
        for key, value in pure_fields.items():
            pure_fields[key] = self.strip_locations(value)

        pure_fields['__type__'] = node.__class__.__name__
        return pure_fields

    def assertNodesEqual(self, actual, expected):
        self.assertEqual(self.strip_locations(actual), self.strip_locations(expected))

    def test_stdout_section(self):
        source = "skriv hejsan\nskriv ny rad\nskriv hoppsan"
        expected = [
            PrintNode(StringNode("hejsan")),
            PrintNode(StringNode("\n")),
            PrintNode(StringNode("hoppsan"))
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_variables_boolean_or_comparison(self):
        source = "sätt x till SANT\nsätt y till x eller FALSKT"
        expected = [
            AssignNode("x", BoolNode(True)),
            AssignNode("y", ComparisonNode(VarAccessNode("x"), "eller", BoolNode(False)))
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_variables_boolean_and_comparison(self):
        source = "sätt x till SANT\nsätt y till x och FALSKT"
        expected = [
            AssignNode("x", BoolNode(True)),
            AssignNode("y", ComparisonNode(VarAccessNode("x"), "och", BoolNode(False)))
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_variables_boolean_greater_than(self):
        source = "sätt a till 3\nsätt b till a större än 2"
        expected = [
            AssignNode("a", IntNode(3)),
            AssignNode("b", ComparisonNode(VarAccessNode("a"), "större än", IntNode(2)))
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_variables_boolean_greater_than_or_equal(self):
        source = "sätt a till 3\nsätt b till a större än eller lika med 2"
        expected = [
            AssignNode("a", IntNode(3)),
            AssignNode("b", ComparisonNode(VarAccessNode("a"), "större än eller lika med", IntNode(2)))
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_variables_boolean_equal(self):
        source = "sätt a till 3\nsätt b till a lika med 2"
        expected = [
            AssignNode("a", IntNode(3)),
            AssignNode("b", ComparisonNode(VarAccessNode("a"), "lika med", IntNode(2)))
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_variables_boolean_less_than(self):
        source = "sätt a till 3\nsätt b till a mindre än 2"
        expected = [
            AssignNode("a", IntNode(3)),
            AssignNode("b", ComparisonNode(VarAccessNode("a"), "mindre än", IntNode(2)))
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_variables_boolean_less_than_or_equal(self):
        source = "sätt a till 3\nsätt b till a mindre än eller lika med 2"
        expected = [
            AssignNode("a", IntNode(3)),
            AssignNode("b", ComparisonNode(VarAccessNode("a"), "mindre än eller lika med", IntNode(2)))
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_variables_string_when_variable_not_found(self):
        source = "sätt x till SANT\nsätt b till a större än 2"
        expected = [
            AssignNode("x", BoolNode(True)),
            AssignNode("b", StringNode("a större än 2"))
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_variables_math_plus(self):
        source = "sätt c till 2 plus 3"
        expected = [
            AssignNode("c", AddNode(IntNode(2), IntNode(3)))
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_variables_math_subtract(self):
        source = "sätt c till 2 minus 3"
        expected = [
            AssignNode("c", SubNode(IntNode(2), IntNode(3)))
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_variables_math_multiply(self):
        source = "sätt c till 2 gånger 3"
        expected = [
            AssignNode("c", MulNode(IntNode(2), IntNode(3)))
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_variables_math_divide(self):
        source = "sätt c till 2 delat med 3"
        expected = [
            AssignNode("c", DivNode(IntNode(2), IntNode(3)))
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_variables_math_multiplication_before_addition(self):
        source = "sätt c till 3 plus 4 gånger 2"
        expected = [
            AssignNode("c", AddNode(IntNode(3), MulNode(IntNode(4), IntNode(2))))
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_variables_math_division_before_addition(self):
        source = "sätt c till 3 plus 4 delat med 2"
        expected = [
            AssignNode("c", AddNode(IntNode(3), DivNode(IntNode(4), IntNode(2))))
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_variables_float_section(self):
        source = "sätt y till 3,4"
        expected = [
            AssignNode("y", FloatNode("3,4"))
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_variables_list_with_initial_values(self):
        source = "sätt min lista till lista med 1, 2, 3"
        expected = [
            AssignNode("min lista", FunctionCallNode("lista", [
                IntNode(1),
                IntNode(2),
                IntNode(3)
            ]))
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_variables_list_empty(self):
        source = "sätt min lista till lista"
        expected = [
            AssignNode("min lista", FunctionCallNode("lista", []))
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_function_section(self):
        source = "sätt f till grej med a\n    ge a"
        expected = [
            AssignNode("f", FunctionDefNode(
                params=["a"],
                body=[ReturnNode(VarAccessNode("a"))]
            ))
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_typ_section(self):
        source = "typ person med namn, ålder\nsätt ålder i person till 38"
        expected = [
            TypeDefNode("person", ["namn", "ålder"]),
            AssignNode("ålder", IntNode(38), target_type="person")
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_if_statement_section(self):
        source = "sätt x till 3\nom x är större än 2\n    skriv större\nannars\n    skriv mindre"
        expected = [
            AssignNode("x", IntNode(3)),
            IfNode(
                condition=ComparisonNode(VarAccessNode("x"), "större än", IntNode(2)),
                true_block=[PrintNode(StringNode("större"))],
                false_block=[PrintNode(StringNode("mindre"))]
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_stdin_section(self):
        source = "sätt t till nästa rad från inmatning"
        ast = self.parse_source(source)
        self.assertIsInstance(ast[0], AssignNode)

    def test_error_handling_section(self):
        source = "försök\n    kasta fel\nfånga fel\n    skriv fel"
        expected = [
            TryCatchNode(
                try_block=[UnaryOpNode("kasta", StringNode("fel"))],
                error_var="fel",
                catch_block=[PrintNode(VarAccessNode("fel"))]
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_comments_section(self):
        source = ". skriver\nskriv hej"
        expected = [
            PrintNode(StringNode("hej"))
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

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
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_property_access_with_from_keyword(self):
        """Verify that 'fält från objekt' produces a VarAccessNode with a target."""
        # Pre-define the variable so the scope check doesn't trigger a string fallback
        source = "typ person med namn\nsätt p till person med David\nskriv namn från p"
        expected = [
            TypeDefNode("person", ["namn"]),
            AssignNode("p", FunctionCallNode("person", [StringNode("David")])),
            PrintNode(VarAccessNode("namn", "p"))
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

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
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_remove_following_another_statement(self):
        """Pinpoint: Does a previous statement interfere with 'ta bort'?"""
        source = "sätt frukter till lista med banan\nta bort banan från frukter"
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

    def test_bootstrapping_sanity_ast(self):
        """Verify the precise AST node structure for the bootstrapping sanity test source."""
        source = """öppna källkod_test.hiuh för läsning som fil
sätt rad_nummer till 1

medan inte i slutet från fil
    sätt rad till nästa rad från fil

    . Inspect the first character of the line to find syntax shapes
    sätt första_tecken till element 0 från rad

    skriv rad_nummer plus . plus första_tecken plus mellanrum
    sätt rad_nummer till rad_nummer plus 1

stäng fil"""

        actual_nodes = self.parse_source(source)

        expected_nodes = [
            # öppna källkod_test.hiuh för läsning som fil
            AssignNode(
                name="fil",
                value=FunctionCallNode(
                    name="öppna",
                    args=[
                        StringNode("källkod_test.hiuh"),
                        StringNode("läsning")
                    ]
                )
            ),

            # sätt rad_nummer till 1
            AssignNode(
                name="rad_nummer",
                value=IntNode("1")
            ),

            # medan inte i slutet från fil
            # CORRECTED WHILE NODE CONTEXT:
            WhileNode(
                condition=NotNode( # Properly negates the statement
                    condition=VarAccessNode("i slutet", target="fil") # Single property name!
                ),
                body=[
                    AssignNode(name="rad", value=VarAccessNode("nästa rad", target="fil")),
                    AssignNode(name="första_tecken", value=VarAccessNode("0", target="rad")),
                    PrintNode(
                        value=AddNode(
                            left=AddNode(
                                left=AddNode(
                                    left=VarAccessNode("rad_nummer"),
                                    right=StringNode(".")
                                ),
                                right=VarAccessNode("första_tecken")
                            ),
                            right=VarAccessNode("mellanrum")
                        )
                    ),
                    AssignNode(
                        name="rad_nummer",
                        value=AddNode(left=VarAccessNode("rad_nummer"), right=IntNode("1"))
                    )
                ]
            ),

            # stäng fil
            CloseFileNode(target_var="fil")
        ]

        self.assertNodesEqual(actual_nodes, expected_nodes)

    def test_wildcard_import_includes_module_symbols(self):
        """Verify that wildcard import 'använd verktyg' makes all module symbols available."""
        # Module source code (in-memory)
        verktyg_source = """
sätt meddelande till Hej
sätt faktor till 10
sätt addera till grej med a, b
    ge a plus b
"""
        
        source = """
använd test_verktyg
skriv meddelande
skriv faktor
sätt summa till addera med 5, 3
skriv summa
        """
        nodes = self.parse_source(source, modules={"test_verktyg": verktyg_source})
        
        # Expected AST after import flattening:
        expected = [
            AssignNode("meddelande", StringNode("Hej")),
            AssignNode("faktor", IntNode("10")),
            AssignNode("addera", FunctionDefNode(["a", "b"], [ReturnNode(AddNode(VarAccessNode("a"), VarAccessNode("b")))])),
            PrintNode(VarAccessNode("meddelande")),
            PrintNode(VarAccessNode("faktor")),
            AssignNode("summa", FunctionCallNode("addera", [IntNode("5"), IntNode("3")])),
            PrintNode(VarAccessNode("summa")),
        ]
        self.assertNodesEqual(nodes, expected)

    def test_directory_import_includes_module_symbols(self):
        """Verify that directory import 'använd verktyg.matematik' makes symbols available."""
        # Module source code (in-memory)
        matematik_source = """
sätt addera till grej med a, b
    ge a plus b
"""
        
        source = """
använd test_verktyg.matematik
sätt summa till addera med 10, 5
skriv summa
        """
        nodes = self.parse_source(source, modules={"test_verktyg.matematik": matematik_source})
        
        expected = [
            AssignNode("addera", FunctionDefNode(["a", "b"], [ReturnNode(AddNode(VarAccessNode("a"), VarAccessNode("b")))])),
            AssignNode("summa", FunctionCallNode("addera", [IntNode("10"), IntNode("5")])),
            PrintNode(VarAccessNode("summa")),
        ]
        self.assertNodesEqual(nodes, expected)

    def test_listor_module_import_has_correct_structure(self):
        """Verify that listor.hiuh imports correctly and functions have expected structure."""
        source = """
använd listor

sätt matchar_hiuh till grej med text_stycke
    ge text_stycke lika med Hiuh

sätt namn_lista till lista

sätt hittat_index till index på första matchande med namn_lista, matchar_hiuh
        """
        nodes = self.parse_source(source, stdlib_path=self.hiuh_folder)

        # After import, the AST should have all the imported functions plus local code
        expected = [
            # Imported from listor
            AssignNode("index på första matchande", FunctionDefNode(
                ["värden", "anrop"],
                [
                    AssignNode("x", IntNode("0")),
                    WhileNode(
                        ComparisonNode(VarAccessNode("x"), "mindre än", FunctionCallNode("längd", [VarAccessNode("värden")])),
                        [
                            IfNode(
                                FunctionCallNode("anrop", [VarAccessNode("x", "värden")]),
                                [ReturnNode(VarAccessNode("x"))]
                            ),
                            AssignNode("x", AddNode(VarAccessNode("x"), IntNode("1")))
                        ]
                    ),
                    ReturnNode(IntNode("-1"))
                ]
            )),
            AssignNode("första matchande", FunctionDefNode(
                ["värden", "anrop"],
                [
                    AssignNode("x", FunctionCallNode("index på första matchande", [VarAccessNode("värden"), VarAccessNode("anrop")])),
                    IfNode(
                        ComparisonNode(VarAccessNode("x"), "lika med", IntNode("-1")),
                        [UnaryOpNode("kasta", StringNode("värdet finns inte!"))]
                    ),
                    ReturnNode(VarAccessNode("x", "värden"))
                ]
            )),
            AssignNode("för varje", FunctionDefNode(
                ["värden", "anrop"],
                [
                    AssignNode("x", IntNode("0")),
                    WhileNode(
                        ComparisonNode(VarAccessNode("x"), "mindre än", FunctionCallNode("längd", [VarAccessNode("värden")])),
                        [
                            FunctionCallNode(VarAccessNode("anrop"), [VarAccessNode("element x")]),
                        ]
                    )
                ]
            )),
            # Local code
            AssignNode("matchar_hiuh", FunctionDefNode(["text_stycke"], [ReturnNode(ComparisonNode(VarAccessNode("text_stycke"), "lika med", StringNode("Hiuh")))])),
            AssignNode("namn_lista", FunctionCallNode("lista", [])),
            AssignNode("hittat_index", FunctionCallNode("index på första matchande", [VarAccessNode("namn_lista"), VarAccessNode("matchar_hiuh")]))
        ]
        self.assertNodesEqual(nodes, expected)


    def test_forsta_matchande_function_has_correct_body(self):
        """Verify that 'första matchande' function body is correct."""
        source = """
använd listor

sätt matchar till grej med x
    ge x

sätt resultat till första matchande med lista, matchar
        """
        nodes = self.parse_source(source, stdlib_path=self.hiuh_folder)

        # The function 'första matchande' should be in the AST with correct structure
        func_assign = None
        for node in nodes:
            if isinstance(node, AssignNode) and node.name == 'första matchande':
                func_assign = node
                break

        self.assertIsNotNone(func_assign, "Function 'första matchande' not found")
        self.assertEqual(func_assign.value.params, ['värden', 'anrop'])

        # Expected structure of första matchande:
        # Note: Due to tokenizer treating -1 as identifier, the comparison is stringified
        expected_func = FunctionDefNode(
            ["värden", "anrop"],
            [
                AssignNode("x", FunctionCallNode("index på första matchande", [VarAccessNode("värden"), VarAccessNode("anrop")])),
                IfNode(
                    StringNode("x lika med -1"),
                    [UnaryOpNode("kasta", StringNode("värdet finns inte!"))]
                ),
                ReturnNode(VarAccessNode("x", "värden"))
            ]
        )
        self.assertNodesEqual(func_assign.value, expected_func)

    def test_ordlista_import_has_correct_structure(self):
        """Verify that ordlista module functions are imported correctly."""
        source = """
använd ordlista

sätt min_ordlista till ny tom ordlista
        """
        nodes = self.parse_source(source, stdlib_path=self.hiuh_folder)

        # Just check the structure matches
        names = [n.name for n in nodes if isinstance(n, AssignNode) and hasattr(n, 'name')]
        self.assertIn('ny tom ordlista', names)
        self.assertIn('ny ordlista', names)

    def test_import_preserves_function_body_structure(self):
        """Verify that imported FunctionDefNode body structure is preserved."""
        # Module source code (in-memory)
        callbacks_source = """
sätt köra till grej med lista, anrop
    sätt x till 0
    medan x är mindre än längd från lista
        anrop med element x från lista
        sätt x till x plus 1
"""
        
        source = """
använd test_callbacks

sätt min_lista till lista
sätt resultat till köra med min_lista, grej med n
skriv n
        """
        nodes = self.parse_source(source, modules={"test_callbacks": callbacks_source})
        
        # Find 'köra' function
        func_assign = None
        for node in nodes:
            if isinstance(node, AssignNode) and node.name == 'köra':
                func_assign = node
                break
        
        self.assertIsNotNone(func_assign, "Function 'köra' not found")
        self.assertEqual(func_assign.value.params, ['lista', 'anrop'])
        
        # Expected structure
        expected_func = FunctionDefNode(
            ["lista", "anrop"],
            [
                AssignNode("x", IntNode("0")),
                WhileNode(
                    ComparisonNode(VarAccessNode("x"), "mindre än", FunctionCallNode("längd", [VarAccessNode("lista")])),
                    [
                        FunctionCallNode(VarAccessNode("anrop"), [VarAccessNode("element x")]),
                        AssignNode("x", AddNode(VarAccessNode("x"), IntNode("1")))
                    ]
                )
            ]
        )
        self.assertNodesEqual(func_assign.value, expected_func)

    def test_index_pa_forsta_matchande_function_complete_structure(self):
        """Verify the complete structure of 'index på första matchande' from listor."""
        source = """
använd listor

sätt matchar_hiuh till grej med text_stycke
    ge text_stycke lika med Hiuh

sätt namn_lista till lista

sätt hittat_index till index på första matchande med namn_lista, matchar_hiuh
        """
        nodes = self.parse_source(source, stdlib_path=self.hiuh_folder)

        # Find 'index på första matchande' function
        func_assign = None
        for node in nodes:
            if isinstance(node, AssignNode) and node.name == 'index på första matchande':
                func_assign = node
                break

        self.assertIsNotNone(func_assign, "Function 'index på första matchande' not found")
        self.assertEqual(func_assign.value.params, ['värden', 'anrop'])

        # Expected structure
        expected_func = FunctionDefNode(
            ["värden", "anrop"],
            [
                AssignNode("x", IntNode("0")),
                WhileNode(
                    ComparisonNode(VarAccessNode("x"), "mindre än", FunctionCallNode("längd", [VarAccessNode("värden")])),
                    [
                        IfNode(
                            FunctionCallNode(VarAccessNode("anrop"), [VarAccessNode("element x")]),
                            [ReturnNode(VarAccessNode("x"))]
                        ),
                        AssignNode("x", AddNode(VarAccessNode("x"), IntNode("1")))
                    ]
                ),
                ReturnNode(IntNode("-1"))
            ]
        )
        self.assertNodesEqual(func_assign.value, expected_func)


if __name__ == '__main__':
    unittest.main()
