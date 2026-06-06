"""Parser and Resolver tests - tests AST output after resolver transformation."""
import os
import unittest

from hiuh.frontend.ast import *
from hiuh.frontend.module_registry import ModuleRegistry
from hiuh.frontend.parser import Parser
from hiuh.frontend.resolver import Resolver
from hiuh.frontend.tokenizer import Tokenizer


class TestParserResolverAST(unittest.TestCase):
    """Test parser and resolver together - verifies AST output after resolver transformation."""
    
    def setUp(self):
        self.tokenizer = Tokenizer()
        self.repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.hiuh_folder = os.path.join(self.repo_root, "hiuh_i_hiuh")
        self.module_registry = ModuleRegistry(os.path.join(self.repo_root, "build", "symbols"))
        self.resolver = Resolver(self.module_registry, self.hiuh_folder)

    def parse_source(self, source, modules=None):
        """Parse source and run resolver to get transformed AST."""
        tokens = self.tokenizer.tokenize(source)
        parser = Parser(tokens)
        ast = parser.parse()
        
        self.resolver.discover_modules_from_ast("main", ast, self.hiuh_folder)
        
        if modules:
            for name, module_source in modules.items():
                self.resolver.register_module_source(name, module_source)

        self.resolver.discover_imports("main")
        self.resolver.resolve_all()
        
        return self.resolver.get_ast("main")

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

    def test_casting_to_type(self):
        """Verify that 'X som Y' creates a CastNode."""
        source = "sätt x till 5 som text"
        expected = [
            AssignNode(
                name="x",
                value=CastNode(value=IntNode("5"), target_type="text")
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_casting_to_character(self):
        """Verify that 'X som tecken' creates a CastNode."""
        source = "sätt x till 65 som tecken"
        expected = [
            AssignNode(
                name="x",
                value=CastNode(value=IntNode("65"), target_type="tecken")
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_casting_som_text(self):
        """Verify that 'X som text' creates a CastNode."""
        source = "sätt x till 123 som text"
        expected = [
            AssignNode(
                name="x",
                value=CastNode(value=IntNode("123"), target_type="text")
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_file_close(self):
        """Verify that 'stäng X' creates CloseFileNode."""
        source = "stäng fil"
        expected = [
            CloseFileNode(target_var="fil")
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_list_length(self):
        """Verify that 'längd från lista' creates a PropertyAccessNode."""
        source = "sätt frukt till lista med äpple\nskriv längd från frukt"
        expected = [
            AssignNode(
                name="frukt",
                value=FunctionCallNode(
                    name="lista",
                    args=[StringNode("äpple")]
                )
            ),
            PrintNode(
                value=PropertyAccessNode(
                    property_name="längd",
                    target=VarAccessNode("frukt")
                )
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_element_access(self):
        """Verify that 'element 0 från lista' creates an ElementAccessNode."""
        source = "skriv element 0 från lista"
        expected = [
            PrintNode(
                value=ElementAccessNode(
                    index=IntNode("0"),
                    target=VarAccessNode("lista")
                )
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_list_membership_contains(self):
        """Verify that 'lista innehåller värde' creates an InfixCallNode."""
        source = """använd listor

sätt färger till lista med röd, grön
om färger innehåller röd
    skriv Japp
om färger innehåller blå
    skriv Nej"""
        expected = [
            ImportNode(module_name="listor", import_all=True, resolved=True),
            AssignNode(
                name="färger",
                value=FunctionCallNode(
                    name="lista",
                    args=[StringNode("röd"), StringNode("grön")]
                )
            ),
            IfNode(
                conditions=[
                    IfCondition(
                        test=InfixCallNode(
                            left=VarAccessNode("färger"),
                            operator="innehåller",
                            right=StringNode("röd")
                        ),
                        block=[PrintNode(StringNode("Japp"))]
                    )
                ]
            ),
            IfNode(
                conditions=[
                    IfCondition(
                        test=InfixCallNode(
                            left=VarAccessNode("färger"),
                            operator="innehåller",
                            right=StringNode("blå")
                        ),
                        block=[PrintNode(StringNode("Nej"))]
                    )
                ]
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_comparison_with_property_target(self):
        """Verify that comparisons with property access on the right are parsed correctly."""
        source = "sätt frukt till lista med äpple\nom x är mindre än längd från frukt\n    skriv hej"
        expected = [
            AssignNode(
                name="frukt",
                value=FunctionCallNode(
                    name="lista",
                    args=[StringNode("äpple")]
                )
            ),
            IfNode(
                conditions=[
                    IfCondition(
                        test=ComparisonNode(
                            left=VarAccessNode("x"),
                            op="mindre än",
                            right=PropertyAccessNode(property_name="längd", target=VarAccessNode("frukt"))
                        ),
                        block=[PrintNode(StringNode("hej"))]
                    )
                ]
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_infix_function_body_property_access(self):
        """Verify that infix function bodies with property access are parsed correctly."""
        source = "sätt innehåller till infix grej med lista, värde\n    sätt x till 0\n    medan x är mindre än längd från lista\n        ge SANT"
        expected = [
            AssignNode(
                name="innehåller",
                value=FunctionDefNode(
                    params=["lista", "värde"],
                    body=[
                        AssignNode(name="x", value=IntNode("0")),
                        WhileNode(
                            condition=ComparisonNode(
                                left=VarAccessNode("x"),
                                op="mindre än",
                                right=PropertyAccessNode(property_name="längd", target=VarAccessNode("lista"))
                            ),
                            body=[ReturnNode(value=BoolNode(True))]
                        )
                    ],
                    is_infix=True
                )
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_normal_function_body_property_access(self):
        """Verify that normal function bodies with property access are parsed correctly."""
        source = "sätt foo till grej med a, b\n    skriv a är mindre än längd från b"
        expected = [
            AssignNode(
                name="foo",
                value=FunctionDefNode(
                    params=["a", "b"],
                    body=[
                        PrintNode(
                            value=ComparisonNode(
                                left=VarAccessNode("a"),
                                op="mindre än",
                                right=PropertyAccessNode(property_name="längd", target=VarAccessNode("b"))
                            )
                        )
                    ],
                    is_infix=False
                )
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_infix_function_custom_definition(self):
        """Verify that custom infix function 'är del av' is defined correctly."""
        source = "sätt är del av till infix grej med del, helhet\n    sätt x till 0\n    ge FALSKT"
        expected = [
            AssignNode(
                name="är del av",
                value=FunctionDefNode(
                    params=["del", "helhet"],
                    body=[
                        AssignNode(name="x", value=IntNode("0")),
                        ReturnNode(value=BoolNode(False))
                    ],
                    is_infix=True
                )
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_infix_function_call_in_comparison(self):
        """Verify that infix function call in comparison is parsed correctly."""
        source = "sätt är del av till infix grej med del, helhet\n    ge FALSKT\nom grön är del av färger\n    skriv Hittat"
        expected = [
            AssignNode(
                name="är del av",
                value=FunctionDefNode(
                    params=["del", "helhet"],
                    body=[ReturnNode(value=BoolNode(False))],
                    is_infix=True
                )
            ),
            IfNode(
                conditions=[
                    IfCondition(
                        test=InfixCallNode(
                            left=StringNode("grön"),
                            operator="är del av",
                            right=StringNode("färger")
                        ),
                        block=[PrintNode(StringNode("Hittat"))]
                    )
                ]
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_named_args_in_function_call(self):
        """Verify that named arguments in function calls are parsed correctly."""
        source = "sätt beräkna till grej med a, b\n    ge 0\nsätt resultat till beräkna med a 5, b 3"
        expected = [
            AssignNode(
                name="beräkna",
                value=FunctionDefNode(
                    params=["a", "b"],
                    body=[ReturnNode(value=IntNode("0"))],
                    is_infix=False
                )
            ),
            AssignNode(
                name="resultat",
                value=FunctionCallNode(
                    name="beräkna",
                    args=[
                        NamedArgNode(name="a", value=IntNode("5")),
                        NamedArgNode(name="b", value=IntNode("3"))
                    ]
                )
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_try_catch_finally(self):
        """Verify that try-catch-finally error handling is parsed correctly."""
        source = "försök\n    kasta fel\nfånga fel\n    skriv fel\nslutligen\n    skriv hejdå"
        expected = [
            TryCatchNode(
                try_block=[UnaryOpNode(op="kasta", operand=VarAccessNode("fel"))],
                error_var="fel",
                catch_block=[PrintNode(VarAccessNode("fel"))],
                finally_block=[PrintNode(StringNode("hejdå"))]
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_try_finally(self):
        """Verify that try-finally (no catch) error handling is parsed correctly."""
        source = "försök\n    skriv hej\nslutligen\n    skriv hejdå"
        expected = [
            TryCatchNode(
                try_block=[PrintNode(StringNode("hej"))],
                error_var=None,
                catch_block=[],
                finally_block=[PrintNode(StringNode("hejdå"))]
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_infix_funktion_custom_definition(self):
        """Verify that custom infix function 'är del av' is defined and used correctly."""
        source = """
sätt är del av till infix grej med del, helhet
    sätt x till 0
    medan x är mindre än längd från helhet
        om element x från helhet är lika med del
            ge SANT
        sätt x till x plus 1
    ge FALSKT

sätt färger till lista med röd, grön, blå
om grön är del av färger
    skriv Hittat
om gul är del av färger
    skriv Saknas
sätt resultat till blå är del av färger
skriv resultat"""
        expected = [
            AssignNode(
                name="är del av",
                value=FunctionDefNode(
                    params=["del", "helhet"],
                    body=[
                        AssignNode(name="x", value=IntNode("0")),
                        WhileNode(
                            condition=ComparisonNode(
                                left=VarAccessNode("x"),
                                op="mindre än",
                                right=PropertyAccessNode(
                                    property_name="längd",
                                    target=VarAccessNode("helhet")
                                )
                            ),
                            body=[
                                IfNode(
                                    conditions=[
                                        IfCondition(
                                            test=ComparisonNode(
                                                left=ElementAccessNode(
                                                    index=VarAccessNode("x"),
                                                    target=VarAccessNode("helhet")
                                                ),
                                                op="lika med",
                                                right=VarAccessNode("del")
                                            ),
                                            block=[ReturnNode(value=BoolNode(True))]
                                        )
                                    ]
                                ),
                                AssignNode(name="x", value=AddNode(VarAccessNode("x"), IntNode("1")))
                            ]
                        ),
                        ReturnNode(value=BoolNode(False))
                    ],
                    is_infix=True
                )
            ),
            AssignNode(
                name="färger",
                value=FunctionCallNode(
                    name="lista",
                    args=[StringNode("röd"), StringNode("grön"), StringNode("blå")]
                )
            ),
            IfNode(
                conditions=[
                    IfCondition(
                        test=InfixCallNode(
                            left=StringNode("grön"),
                            operator="är del av",
                            right=VarAccessNode("färger")
                        ),
                        block=[PrintNode(StringNode("Hittat"))]
                    )
                ]
            ),
            IfNode(
                conditions=[
                    IfCondition(
                        test=InfixCallNode(
                            left=StringNode("gul"),
                            operator="är del av",
                            right=VarAccessNode("färger")
                        ),
                        block=[PrintNode(StringNode("Saknas"))]
                    )
                ]
            ),
            AssignNode(
                name="resultat",
                value=InfixCallNode(
                    left=StringNode("blå"),
                    operator="är del av",
                    right=VarAccessNode("färger")
                )
            ),
            PrintNode(value=VarAccessNode("resultat"))
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_listor_utility_callbacks(self):
        """Verify that listor.hiuh high-order functions are parsed and used correctly."""
        source = """
använd listor

sätt matchar_hiuh till grej med text_stycke
    ge text_stycke lika med Hiuh

sätt namn_lista till lista med Java, Python, Hiuh, Kotlin

sätt hittat_index till index på första matchande med namn_lista, matchar_hiuh
sätt hittat_namn till första matchande med namn_lista, matchar_hiuh
"""
        expected = [
            ImportNode(module_name="listor", import_all=True, resolved=True),
            AssignNode(
                name="matchar_hiuh",
                value=FunctionDefNode(
                    params=["text_stycke"],
                    body=[
                        ReturnNode(value=ComparisonNode(
                            left=VarAccessNode("text_stycke"),
                            op="lika med",
                            right=StringNode("Hiuh")
                        ))
                    ],
                    is_infix=False
                )
            ),
            AssignNode(
                name="namn_lista",
                value=FunctionCallNode(
                    name="lista",
                    args=[StringNode("Java"), StringNode("Python"), StringNode("Hiuh"), StringNode("Kotlin")]
                )
            ),
            AssignNode(
                name="hittat_index",
                value=FunctionCallNode(
                    name="index på första matchande",
                    args=[
                        VarAccessNode("namn_lista"),
                        VarAccessNode("matchar_hiuh")
                    ]
                )
            ),
            AssignNode(
                name="hittat_namn",
                value=FunctionCallNode(
                    name="första matchande",
                    args=[
                        VarAccessNode("namn_lista"),
                        VarAccessNode("matchar_hiuh")
                    ]
                )
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_named_args_grej_function(self):
        """Verify that grej functions support named arguments."""
        source = """
sätt add till grej med a, b
    ge a plus b

sätt resultat till add med a 5, b 3
skriv resultat
"""
        expected = [
            AssignNode(
                name="add",
                value=FunctionDefNode(
                    params=["a", "b"],
                    body=[
                        ReturnNode(value=AddNode(
                            left=VarAccessNode("a"),
                            right=VarAccessNode("b")
                        ))
                    ],
                    is_infix=False
                )
            ),
            AssignNode(
                name="resultat",
                value=FunctionCallNode(
                    name="add",
                    args=[
                        NamedArgNode(name="a", value=IntNode("5")),
                        NamedArgNode(name="b", value=IntNode("3"))
                    ]
                )
            ),
            PrintNode(value=VarAccessNode("resultat"))
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_ordlista_utility_callbacks(self):
        """Verify that ordlista.hiuh callback usage is parsed correctly."""
        source = """
använd ordlista
använd listor

sätt fruktantal till ny tom ordlista
putta från fruktantal med äpple, 2
putta från fruktantal med banan, 1
putta från fruktantal med citron, 3

rensa från fruktantal med banan

sätt fruktpar till värden från fruktantal

sätt fruktfunk till grej med par
    sätt fruktnamn till nyckel från par
    sätt fruktantal till värde från par
    skriv fruktnamn plus mellanrum plus fruktantal plus . plus mellanrum

för varje med fruktpar, fruktfunk
"""
        expected = [
            ImportNode(module_name="ordlista", import_all=True, resolved=True),
            ImportNode(module_name="listor", import_all=True, resolved=True),
            AssignNode(
                name="fruktantal",
                value=FunctionCallNode(name="ny tom ordlista", args=[])
            ),
            FunctionCallNode(
                name=VarAccessNode(name="putta", target="fruktantal"),
                args=[
                    StringNode("äpple"),
                    IntNode("2")
                ]
            ),
            FunctionCallNode(
                name=VarAccessNode(name="putta", target="fruktantal"),
                args=[
                    StringNode("banan"),
                    IntNode("1")
                ]
            ),
            FunctionCallNode(
                name=VarAccessNode(name="putta", target="fruktantal"),
                args=[
                    StringNode("citron"),
                    IntNode("3")
                ]
            ),
            FunctionCallNode(
                name=VarAccessNode(name="rensa", target="fruktantal"),
                args=[
                    StringNode("banan")
                ]
            ),
            AssignNode(
                name="fruktpar",
                value=PropertyAccessNode(
                    property_name="värden",
                    target=VarAccessNode("fruktantal")
                )
            ),
            AssignNode(
                name="fruktfunk",
                value=FunctionDefNode(
                    params=["par"],
                    body=[
                        AssignNode(
                            name="fruktnamn",
                            value=PropertyAccessNode(
                                property_name="nyckel",
                                target=VarAccessNode("par")
                            )
                        ),
                        AssignNode(
                            name="fruktantal",
                            value=PropertyAccessNode(
                                property_name="värde",
                                target=VarAccessNode("par")
                            )
                        ),
                        PrintNode(value=AddNode(
                            left=AddNode(
                                left=AddNode(
                                    left=AddNode(
                                        left=VarAccessNode("fruktnamn"),
                                        right=VarAccessNode("mellanrum")
                                    ),
                                    right=VarAccessNode("fruktantal")
                                ),
                                right=StringNode(".")
                            ),
                            right=VarAccessNode("mellanrum")
                        ))
                    ],
                    is_infix=False
                )
            ),
            FunctionCallNode(
                name="för varje",
                args=[
                    VarAccessNode("fruktpar"),
                    VarAccessNode("fruktfunk")
                ]
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_element_assign_int_index(self):
        """Verify that element assignment with integer index is parsed correctly."""
        source = """
sätt element 0 i lista till 42
        """
        expected = [
            ElementAssignNode(
                index=IntNode("0"),
                target=VarAccessNode("lista"),
                value=IntNode("42")
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_element_assign_variable_index(self):
        """Verify that element assignment with variable index is parsed correctly."""
        source = """
sätt x till 2
sätt element x i lista till hello
        """
        expected = [
            AssignNode("x", IntNode(2)),
            ElementAssignNode(
                index=VarAccessNode("x"),
                target=VarAccessNode("lista"),
                value=StringNode("hello")
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_element_assign_in_function(self):
        """Verify that element assignment works inside a function."""
        source = """
sätt uppdatera till grej med lst
    sätt element 0 i lst till 100
    ge element 0 från lst
        """
        expected = [
            AssignNode(
                name="uppdatera",
                value=FunctionDefNode(
                    params=["lst"],
                    body=[
                        ElementAssignNode(
                            index=IntNode("0"),
                            target=VarAccessNode("lst"),
                            value=IntNode("100")
                        ),
                        ReturnNode(
                            value=ElementAccessNode(
                            index=IntNode("0"),
                            target=VarAccessNode("lst")
                        ))
                    ],
                    is_infix=False
                )
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_längd_från_property_minus_expression(self):
        """Verify that 'längd från värden minus 1' is parsed correctly as arithmetic expression.
        
        The expression should be parsed as: (längd från värden) minus 1
        NOT: längd från (värden minus 1)
        """
        source = """
sätt värden till lista
sätt x till längd från värden minus 1
"""
        expected = [
            AssignNode(
                name="värden",
                value=FunctionCallNode(name="lista", args=[])
            ),
            AssignNode(
                name="x",
                value=SubNode(
                    left=PropertyAccessNode(
                        property_name="längd",
                        target=VarAccessNode("värden")
                    ),
                    right=IntNode("1")
                )
            )
        ]
        self.assertNodesEqual(self.parse_source(source), expected)

    def test_cannot_reassign_builtin_function(self):
        """Verify that trying to reassign a built-in function raises an error."""
        source = """
sätt lista till lista med 10, 20
"""
        with self.assertRaises(Exception) as context:
            self.parse_source(source)
        self.assertIn("Kan inte omdefiniera inbyggd funktion 'lista'", str(context.exception))

if __name__ == '__main__':
    unittest.main()
