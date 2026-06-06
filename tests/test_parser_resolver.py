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
        source = "sätt lista till lista med äpple\nom x är mindre än längd från lista\n    skriv hej"
        expected = [
            AssignNode(
                name="lista",
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
                            right=PropertyAccessNode(property_name="längd", target=VarAccessNode("lista"))
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


if __name__ == '__main__':
    unittest.main()
