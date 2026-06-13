"""Resolver tests — tests AST output after resolver transformation.
Runs all tests against both the Python resolver and the Hiuh resolver."""

import os
import unittest

from hiuh.frontend.ast import *
from hiuh.frontend.module_registry import ModuleRegistry
from hiuh.frontend.parser import Parser
from hiuh.frontend.resolver import Resolver
from hiuh.frontend.tokenizer import Tokenizer


class _BaseResolverTests:
    """Mixin with resolver tests. Subclasses provide resolve(source)."""

    def resolve(self, source, modules=None):
        raise NotImplementedError

    def assertResolvedEqual(self, source, expected_ast_nodes, modules=None):
        raise NotImplementedError

    def assertEqual(self, a, b, msg=None):
        raise NotImplementedError

    # === Test cases ===

    def test_casting_to_type(self):
        source = "sätt x till 5 som text"
        expected = [
            AssignNode(
                name="x",
                value=CastNode(value=IntNode("5"), target_type="text")
            )
        ]
        self.assertResolvedEqual(source, expected)

    def test_casting_to_character(self):
        source = "sätt x till 65 som tecken"
        expected = [
            AssignNode(
                name="x",
                value=CastNode(value=IntNode("65"), target_type="tecken")
            )
        ]
        self.assertResolvedEqual(source, expected)

    def test_casting_som_text(self):
        source = "sätt x till 123 som text"
        expected = [
            AssignNode(
                name="x",
                value=CastNode(value=IntNode("123"), target_type="text")
            )
        ]
        self.assertResolvedEqual(source, expected)

    def test_file_close(self):
        source = "stäng fil"
        expected = [
            CloseFileNode(target_var="fil")
        ]
        self.assertResolvedEqual(source, expected)

    def test_list_length(self):
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
        self.assertResolvedEqual(source, expected)

    def test_element_access(self):
        source = "skriv element 0 från lista"
        expected = [
            PrintNode(
                value=ElementAccessNode(
                    index=IntNode("0"),
                    target=VarAccessNode("lista")
                )
            )
        ]
        self.assertResolvedEqual(source, expected)

    def test_list_membership_contains(self):
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
        self.assertResolvedEqual(source, expected)

    def test_comparison_with_property_target(self):
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
                        test=LessThanNode(
                            left=VarAccessNode("x"),
                            right=PropertyAccessNode(property_name="längd", target=VarAccessNode("frukt"))
                        ),
                        block=[PrintNode(StringNode("hej"))]
                    )
                ]
            )
        ]
        self.assertResolvedEqual(source, expected)

    def test_är_comparison_with_defined_variable(self):
        source = """
sätt x till 10
om x är mindre än 5
    skriv hej
"""
        expected = [
            AssignNode(
                name="x",
                value=IntNode("10")
            ),
            IfNode(
                conditions=[
                    IfCondition(
                        test=LessThanNode(
                            left=VarAccessNode("x"),
                            right=IntNode("5")
                        ),
                        block=[PrintNode(StringNode("hej"))]
                    )
                ]
            )
        ]
        self.assertResolvedEqual(source, expected)

    def test_är_comparison_with_unresolved_variable(self):
        source = "skriv x är mindre än 5"
        expected = [
            PrintNode(value=StringNode("x är mindre än 5"))
        ]
        self.assertResolvedEqual(source, expected)

    def test_not_equal_comparison(self):
        source = """
sätt x till 10
om x är inte 5
    skriv japp
om x är inte lika med 3
    skriv japp2
"""
        expected = [
            AssignNode(name="x", value=IntNode("10")),
            IfNode(
                conditions=[
                    IfCondition(
                        test=NotEqualNode(left=VarAccessNode("x"), right=IntNode("5")),
                        block=[PrintNode(StringNode("japp"))]
                    )
                ]
            ),
            IfNode(
                conditions=[
                    IfCondition(
                        test=NotEqualNode(left=VarAccessNode("x"), right=IntNode("3")),
                        block=[PrintNode(StringNode("japp2"))]
                    )
                ]
            )
        ]
        self.assertResolvedEqual(source, expected)

    def test_modulo_resolver(self):
        source = """
sätt x till 10
sätt y till resten av x delat med 3
sätt z till resten av x delat på 4
"""
        expected = [
            AssignNode(name="x", value=IntNode("10")),
            AssignNode(
                name="y",
                value=ModNode(left=VarAccessNode("x"), right=IntNode("3"))
            ),
            AssignNode(
                name="z",
                value=ModNode(left=VarAccessNode("x"), right=IntNode("4"))
            )
        ]
        self.assertResolvedEqual(source, expected)

    def test_modulo_with_nested_expressions(self):
        source = "sätt x till resten av 3 gånger 2 delat på 4"
        expected = [
            AssignNode(
                name="x",
                value=ModNode(
                    left=MulNode(left=IntNode("3"), right=IntNode("2")),
                    right=IntNode("4")
                )
            )
        ]
        self.assertResolvedEqual(source, expected)

    def test_infix_function_body_property_access(self):
        source = "sätt innehåller till infixgrej med lista som lista av heltal, värde som heltal ger boolesk\n    sätt x till 0\n    medan x är mindre än längd från lista\n        ge SANT"
        expected = [
            AssignNode(
                name="innehåller",
                value=FunctionDefNode(
                    params=[('lista', 'lista av heltal'), ('värde', 'heltal')],
                    body=[
                        AssignNode(name="x", value=IntNode("0")),
                        WhileNode(
                            condition=LessThanNode(
                                left=VarAccessNode("x"),
                                right=PropertyAccessNode(property_name="längd", target=VarAccessNode("lista"))
                            ),
                            body=[ReturnNode(value=BoolNode(True))]
                        )
                    ],
                    is_infix=True,
                    return_type="boolesk"
                ),
            )
        ]
        self.assertResolvedEqual(source, expected)

    def test_normal_function_body_property_access(self):
        source = "sätt foo till grej med a som heltal, b som heltal ger heltal\n    skriv a är mindre än längd från b"
        expected = [
            AssignNode(
                name="foo",
                value=FunctionDefNode(
                    params=[('a', 'heltal'), ('b', 'heltal')],
                    body=[
                        PrintNode(
                            value=LessThanNode(
                                left=VarAccessNode("a"),
                                right=PropertyAccessNode(property_name="längd", target=VarAccessNode("b"))
                            )
                        )
                    ],
                    is_infix=False,
                    return_type="heltal"
                )
            )
        ]
        self.assertResolvedEqual(source, expected)

    def test_infix_function_custom_definition(self):
        source = "sätt är del av till infixgrej med del som heltal, helhet som lista av heltal ger boolesk\n    sätt x till 0\n    ge FALSKT"
        expected = [
            AssignNode(
                name="är del av",
                value=FunctionDefNode(
                    params=[('del', 'heltal'), ('helhet', 'lista av heltal')],
                    body=[
                        AssignNode(name="x", value=IntNode("0")),
                        ReturnNode(value=BoolNode(False))
                    ],
                    is_infix=True,
                    return_type="boolesk"
                )
            )
        ]
        self.assertResolvedEqual(source, expected)

    def test_infix_function_call_in_comparison(self):
        source = "sätt är del av till infixgrej med del som heltal, helhet som lista av heltal ger boolesk\n    ge FALSKT\nom grön är del av färger\n    skriv Hittat"
        expected = [
            AssignNode(
                name="är del av",
                value=FunctionDefNode(
                    params=[('del', 'heltal'), ('helhet', 'lista av heltal')],
                    body=[ReturnNode(value=BoolNode(False))],
                    is_infix=True,
                    return_type="boolesk"
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
        self.assertResolvedEqual(source, expected)

    def test_named_args_in_function_call(self):
        source = "sätt beräkna till grej med a som heltal, b som heltal ger heltal\n    ge 0\nsätt resultat till beräkna med a 5, b 3"
        expected = [
            AssignNode(
                name="beräkna",
                value=FunctionDefNode(
                    params=[('a', 'heltal'), ('b', 'heltal')],
                    body=[ReturnNode(value=IntNode("0"))],
                    is_infix=False,
                    return_type="heltal"
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
        self.assertResolvedEqual(source, expected)

    def test_try_catch_finally(self):
        source = """
försök
    kasta Ojdå
fånga fel
    skriv fel
slutligen
    skriv mellanrum plus och hejdå
"""
        expected = [
            TryCatchNode(
                try_block=[UnaryOpNode(op="kasta", operand=StringNode("Ojdå"))],
                error_var="fel",
                catch_block=[PrintNode(VarAccessNode("fel"))],
                finally_block=[PrintNode(AddNode(VarAccessNode("mellanrum"), StringNode("och hejdå")))]
            )
        ]
        self.assertResolvedEqual(source, expected)

    def test_for_each_loop(self):
        source = "sätt min lista till lista med a, b, c\nför varje mitt index i min lista\n    skriv mitt index"
        expected = [
            AssignNode(
                name="min lista",
                value=FunctionCallNode(
                    name="lista",
                    args=[StringNode("a"), StringNode("b"), StringNode("c")]
                )
            ),
            ForEachNode(
                variable="mitt index",
                iterable=VarAccessNode("min lista"),
                body=[
                    PrintNode(value=VarAccessNode("mitt index"))
                ]
            )
        ]
        self.assertResolvedEqual(source, expected)

    def test_try_finally(self):
        source = """
försök
    skriv hej
slutligen
    skriv mellanrum plus och hejdå
"""
        expected = [
            TryCatchNode(
                try_block=[PrintNode(StringNode("hej"))],
                error_var=None,
                catch_block=[],
                finally_block=[PrintNode(AddNode(VarAccessNode("mellanrum"), StringNode("och hejdå")))]
            )
        ]
        self.assertResolvedEqual(source, expected)

    def test_infix_funktion_custom_definition(self):
        source = """
sätt är del av till infixgrej med del som heltal, helhet som lista av heltal ger boolesk
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
                    params=[('del', 'heltal'), ('helhet', 'lista av heltal')],
                    body=[
                        AssignNode(name="x", value=IntNode("0")),
                        WhileNode(
                            condition=LessThanNode(
                                left=VarAccessNode("x"),
                                right=PropertyAccessNode(
                                    property_name="längd",
                                    target=VarAccessNode("helhet")
                                )
                            ),
                            body=[
                                IfNode(
                                    conditions=[
                                        IfCondition(
                                            test=EqualNode(
                                                left=ElementAccessNode(
                                                    index=VarAccessNode("x"),
                                                    target=VarAccessNode("helhet")
                                                ),
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
                    is_infix=True,
                    return_type="boolesk"
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
        self.assertResolvedEqual(source, expected)

    def test_listor_utility_callbacks(self):
        source = """
använd listor

sätt matchar_hiuh till grej med text_stycke som sträng ger boolesk
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
                    params=[('text_stycke', 'sträng')],
                    body=[
                        ReturnNode(value=EqualNode(
                            left=VarAccessNode("text_stycke"),
                            right=StringNode("Hiuh")
                        ))
                    ],
                    is_infix=False,
                    return_type="boolesk"
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
        self.assertResolvedEqual(source, expected)

    def test_named_args_grej_function(self):
        source = """
sätt add till grej med a som heltal, b som heltal ger heltal
    ge a plus b

sätt resultat till add med a 5, b 3
skriv resultat
"""
        expected = [
            AssignNode(
                name="add",
                value=FunctionDefNode(
                    params=[('a', 'heltal'), ('b', 'heltal')],
                    body=[
                        ReturnNode(value=AddNode(
                            left=VarAccessNode("a"),
                            right=VarAccessNode("b")
                        ))
                    ],
                    is_infix=False,
                    return_type="heltal"
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
        self.assertResolvedEqual(source, expected)

    def test_element_assign_int_index(self):
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
        self.assertResolvedEqual(source, expected)

    def test_element_assign_variable_index(self):
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
        self.assertResolvedEqual(source, expected)

    def test_element_assign_in_function(self):
        source = """
sätt uppdatera till grej med lst som lista av heltal ger heltal
    sätt element 0 i lst till 100
    ge element 0 från lst
        """
        expected = [
            AssignNode(
                name="uppdatera",
                value=FunctionDefNode(
                    params=[('lst', 'lista av heltal')],
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
                    is_infix=False,
                    return_type="heltal"
                )
            )
        ]
        self.assertResolvedEqual(source, expected)

    def test_längd_från_property_minus_expression(self):
        source = """
sätt värden till lista av heltal
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
        self.assertResolvedEqual(source, expected)

    def test_cannot_reassign_builtin_function(self):
        source = """
sätt lista till lista med 10, 20
"""
        with self.assertRaises(Exception) as context:
            self.resolve(source)
        self.assertIn("Kan inte omdefiniera inbyggd funktion 'lista'", str(context.exception))

    def test_resolver_increment_decrement(self):
        source = """
sätt poäng till 10
öka poäng med 5 plus 2
minska poäng med 1
"""
        expected = [
            AssignNode(name="poäng", value=IntNode("10")),
            AddAssignNode(
                target="poäng",
                value=AddNode(left=IntNode("5"), right=IntNode("2"))
            ),
            SubAssignNode(
                target="poäng",
                value=IntNode("1")
            )
        ]
        self.assertResolvedEqual(source, expected)

    def test_resolver_multiply_divide_assign(self):
        source = """
sätt poäng till 10
gångra poäng med 3 plus 1
dela poäng med 2
"""
        expected = [
            AssignNode(name="poäng", value=IntNode("10")),
            MultiplyAssignNode(
                target="poäng",
                value=AddNode(left=IntNode("3"), right=IntNode("1"))
            ),
            DivideAssignNode(
                target="poäng",
                value=IntNode("2")
            )
        ]
        self.assertResolvedEqual(source, expected)

    def test_delstrang_function_call_ast(self):
        source = """
sätt delsträng till grej med text som sträng, start som heltal, längd som heltal ger sträng
    sätt resultat till ""
    sätt pos till start
    sätt slut till start plus längd
    medan pos är mindre än slut och pos är mindre än längd från text
        sätt resultat till resultat plus element pos från text
        öka pos med 1
    ge resultat

sätt rad till hejsan
sätt res till delsträng med rad, 1, 3
skriv res
"""
        expected = [
            AssignNode(
                name="delsträng",
                value=FunctionDefNode(
                    params=[('text', 'sträng'), ('start', 'heltal'), ('längd', 'heltal')],
                    body=[
                        AssignNode(name="resultat", value=StringNode("")),
                        AssignNode(name="pos", value=VarAccessNode("start")),
                        AssignNode(
                            name="slut",
                            value=AddNode(left=VarAccessNode("start"), right=VarAccessNode("längd"))
                        ),
                        WhileNode(
                            condition=AndNode(
                                left=LessThanNode(left=VarAccessNode("pos"), right=VarAccessNode("slut")),
                                right=LessThanNode(
                                    left=VarAccessNode("pos"),
                                    right=PropertyAccessNode(property_name="längd", target=VarAccessNode("text"))
                                )
                            ),
                            body=[
                                AssignNode(
                                    name="resultat",
                                    value=AddNode(
                                        left=VarAccessNode("resultat"),
                                        right=ElementAccessNode(target=VarAccessNode("text"), index=VarAccessNode("pos"))
                                    )
                                ),
                                AddAssignNode(target="pos", value=IntNode("1"))
                            ]
                        ),
                        ReturnNode(value=VarAccessNode("resultat"))
                    ],
                    return_type="sträng"
                )
            ),
            AssignNode(name="rad", value=StringNode("hejsan")),
            AssignNode(
                name="res",
                value=FunctionCallNode(
                    name="delsträng",
                    args=[
                        VarAccessNode("rad"),
                        IntNode("1"),
                        IntNode("3")
                    ]
                )
            ),
            PrintNode(value=VarAccessNode("res"))
        ]
        self.assertResolvedEqual(source, expected)

    def test_element_access_with_arithmetic_index_ast(self):
        source = """
sätt pos till 1
sätt innehåll till "hejsan"
sätt nästa_tecken till element pos plus 1 från innehåll
"""
        expected = [
            AssignNode(name="pos", value=IntNode("1")),
            AssignNode(name="innehåll", value=StringNode("hejsan")),
            AssignNode(
                name="nästa_tecken",
                value=ElementAccessNode(
                    target=VarAccessNode("innehåll"),
                    index=AddNode(left=VarAccessNode("pos"), right=IntNode("1"))
                )
            )
        ]
        self.assertResolvedEqual(source, expected)

    def test_lista_no_type_fails(self):
        source = "sätt x till lista"
        with self.assertRaises(Exception) as ctx:
            self.resolve(source)
        self.assertIn("okänd_typ", str(ctx.exception))

    def test_lista_av_unknown_type_fails(self):
        source = "sätt x till lista av okänd_typ"
        with self.assertRaises(Exception) as ctx:
            self.resolve(source)
        self.assertIn("okänd_typ", str(ctx.exception))

    def test_lista_av_known_type_passes(self):
        source = "sätt x till lista av heltal"
        expected = [
            AssignNode(
                name="x",
                value=FunctionCallNode(name="lista", args=[])
            )
        ]
        self.assertResolvedEqual(source, expected)

    def test_verb_grej_definition_and_call(self):
        source = """
sätt upprepa till verbgrej med ord som sträng, antal som heltal ger sträng
    sätt resultat till ""
    sätt i till 0
    medan i är mindre än antal
        sätt resultat till resultat plus ord
        öka i med 1
    ge resultat

sätt a till hej
upprepa a med 3
"""
        expected = [
            AssignNode(
                name="upprepa",
                value=FunctionDefNode(
                    params=[("ord", "sträng"), ("antal", "heltal")],
                    body=[
                        AssignNode(name="resultat", value=StringNode("")),
                        AssignNode(name="i", value=IntNode("0")),
                        WhileNode(
                            condition=LessThanNode(
                                left=VarAccessNode("i"),
                                right=VarAccessNode("antal")
                            ),
                            body=[
                                AssignNode(name="resultat", value=AddNode(
                                    left=VarAccessNode("resultat"),
                                    right=VarAccessNode("ord")
                                )),
                                AddAssignNode(target="i", value=IntNode("1"))
                            ]
                        ),
                        ReturnNode(value=VarAccessNode("resultat"))
                    ],
                    is_infix=False,
                    return_type="sträng"
                )
            ),
            AssignNode(name="a", value=StringNode("hej")),
            AssignNode(
                name="a",
                value=FunctionCallNode(
                    name="upprepa",
                    args=[VarAccessNode("a"), IntNode("3")]
                )
            )
        ]
        self.assertResolvedEqual(source, expected)

    def test_skicka_grej_definition_and_call(self):
        source = """
sätt lägg_till till skickagrej med sak som sträng, mål som lista av sträng ger lista av sträng
    lägg till sak i mål
    ge mål

sätt min lista till lista av sträng
lägg_till hej till min lista
"""
        expected = [
            AssignNode(
                name="lägg_till",
                value=FunctionDefNode(
                    params=[("sak", "sträng"), ("mål", "lista av sträng")],
                    body=[
                        AppendNode(value=VarAccessNode("sak"), target_list="mål"),
                        ReturnNode(value=VarAccessNode("mål"))
                    ],
                    is_infix=False,
                    return_type="lista av sträng"
                )
            ),
            AssignNode(
                name="min lista",
                value=FunctionCallNode(name="lista", args=[])
            ),
            AssignNode(
                name="min lista",
                value=FunctionCallNode(
                    name="lägg_till",
                    args=[StringNode("hej"), VarAccessNode("min lista")]
                )
            )
        ]
        self.assertResolvedEqual(source, expected)

    def test_hämta_grej_definition_and_call(self):
        source = """
sätt plocka till hämtagrej med namn som sträng, källa som lista av sträng ger sträng
    ge element 0 från källa

sätt frukter till lista av sträng med äpple, banan
sätt resultat till plocka banan från frukter
"""
        expected = [
            AssignNode(
                name="plocka",
                value=FunctionDefNode(
                    params=[("namn", "sträng"), ("källa", "lista av sträng")],
                    body=[ReturnNode(value=ElementAccessNode(
                        index=IntNode("0"),
                        target=VarAccessNode("källa")
                    ))],
                    is_infix=False,
                    return_type="sträng"
                )
            ),
            AssignNode(
                name="frukter",
                value=FunctionCallNode(
                    name="lista",
                    args=[StringNode("äpple"), StringNode("banan")]
                )
            ),
            AssignNode(
                name="resultat",
                value=FunctionCallNode(
                    name="plocka",
                    args=[StringNode("banan"), VarAccessNode("frukter")]
                )
            )
        ]
        self.assertResolvedEqual(source, expected)

    def test_nested_function_call_resolves_correctly(self):
        source = (
            "sätt yttre till grej med x som heltal ger heltal\n"
            "    sätt dubblera till grej med v som heltal ger heltal\n"
            "        ge v gånger 2\n"
            "    sätt resultat till dubblera med x\n"
            "    ge resultat\n"
        )
        resolved = self.resolve(source)
        yttre_def = resolved[0]
        self.assertIsInstance(yttre_def, AssignNode)
        yttre_body = yttre_def.value.body
        assign_resultat = next(
            s for s in yttre_body
            if isinstance(s, AssignNode) and s.name == "resultat"
        )
        self.assertIsInstance(
            assign_resultat.value, FunctionCallNode,
            f"Call to 'dubblera med x' must be FunctionCallNode, "
            f"got {type(assign_resultat.value).__name__}"
        )

    def test_struct_field_wrong_type_raises(self):
        source = (
            "typ mittresultat\n"
            "    nod som heltal\n"
            "    pos som heltal\n"
            "sätt foo till grej med x som sträng ger mittresultat\n"
            "    ge mittresultat med nod x, pos 0\n"
        )
        with self.assertRaises(Exception) as ctx:
            self.resolve(source)
        self.assertIn("Typfel", str(ctx.exception))
        self.assertIn("nod", str(ctx.exception))

    def test_struct_field_correct_type_passes(self):
        source = (
            "typ mittresultat\n"
            "    nod som heltal\n"
            "    pos som heltal\n"
            "sätt foo till grej med x som heltal ger mittresultat\n"
            "    ge mittresultat med nod x, pos 0\n"
        )
        self.resolve(source)  # Must not raise

    def test_list_wrong_element_type_raises(self):
        source = (
            "sätt foo till grej med x som heltal ger lista av sträng\n"
            "    ge lista med \"hej\", x\n"
        )
        with self.assertRaises(Exception) as ctx:
            self.resolve(source)
        self.assertIn("Typfel", str(ctx.exception))

    def test_list_correct_element_type_passes(self):
        source = (
            "sätt foo till grej med x som sträng ger lista av sträng\n"
            "    ge lista med \"hej\", x\n"
        )
        self.resolve(source)  # Must not raise

    def test_grej_allows_self_recursion(self):
        source = (
            "sätt nedräkning till grej med n som heltal ger heltal\n"
            "    om n är mindre än 1\n"
            "        ge 0\n"
            "    sätt nästa till n minus 1\n"
            "    ge nedräkning med nästa\n"
        )
        resolved = self.resolve(source)
        fn_def = resolved[0]
        body = fn_def.value.body
        return_stmt = body[-1]
        self.assertIsInstance(
            return_stmt.value, FunctionCallNode,
            f"Self-call should be FunctionCallNode, got {type(return_stmt.value).__name__}"
        )

    def test_grej_blocks_forward_reference_to_sibling(self):
        source = (
            "sätt yttre till grej med x som heltal ger heltal\n"
            "    sätt tidig till grej med v som heltal ger heltal\n"
            "        ge sen med v\n"
            "    sätt sen till grej med v som heltal ger heltal\n"
            "        ge v gånger 2\n"
            "    ge tidig med x\n"
        )
        resolved = self.resolve(source)
        yttre_body = resolved[0].value.body
        tidig_def = next(s for s in yttre_body if isinstance(s, AssignNode) and s.name == 'tidig')
        tidig_body = tidig_def.value.body
        return_stmt = tidig_body[0]
        self.assertIsInstance(
            return_stmt.value, StringNode,
            f"Forward ref to nested sibling with grej should be StringNode, got {type(return_stmt.value).__name__}"
        )

    def test_rekgrej_allows_mutual_recursion_between_siblings(self):
        source = (
            "sätt jämn till rekgrej med n som heltal ger boolesk\n"
            "    om n är 0\n"
            "        ge SANT\n"
            "    ge udda med n minus 1\n"
            "sätt udda till rekgrej med n som heltal ger boolesk\n"
            "    om n är 0\n"
            "        ge FALSKT\n"
            "    ge jämn med n minus 1\n"
        )
        resolved = self.resolve(source)
        jämn_body = resolved[0].value.body
        jämn_return = jämn_body[-1]
        self.assertIsInstance(jämn_return.value, FunctionCallNode)
        udda_body = resolved[1].value.body
        udda_return = udda_body[-1]
        self.assertIsInstance(udda_return.value, FunctionCallNode)


class TestPythonResolver(_BaseResolverTests, unittest.TestCase):
    """Tests using the Python resolver."""

    def setUp(self):
        self.tokenizer = Tokenizer()
        self.repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.hiuh_folder = os.path.join(self.repo_root, "hiuh_i_hiuh")
        self.module_registry = ModuleRegistry(os.path.join(self.repo_root, "build", "symbols"))
        self.resolver = Resolver(self.module_registry, self.hiuh_folder)

    def resolve(self, source, modules=None):
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

    def assertResolvedEqual(self, source, expected_ast_nodes, modules=None):
        actual = self.resolve(source, modules)
        actual_stripped = self._strip(actual)
        expected_stripped = self._strip(expected_ast_nodes)
        actual_stripped = self._strip_return_type(actual_stripped)
        expected_stripped = self._strip_return_type(expected_stripped)
        self.assertEqual(actual_stripped, expected_stripped)

    def _strip(self, node):
        if isinstance(node, list):
            return [self._strip(child) for child in node]
        if isinstance(node, ExpressionPart):
            return str(node)
        if not hasattr(node, '__dict__'):
            return node
        result = {}
        for key, value in node.__dict__.items():
            if key in ('line', 'column', 'token', 'kind'):
                continue
            result[key] = self._strip(value)
        return result

    def _strip_return_type(self, node):
        if isinstance(node, dict):
            return {k: self._strip_return_type(v) for k, v in node.items() if k != 'return_type'}
        if isinstance(node, list):
            return [self._strip_return_type(x) for x in node]
        return node

    def assertEqual(self, a, b, msg=None):
        unittest.TestCase.assertEqual(self, a, b, msg)


class TestHiuhResolver(_BaseResolverTests, unittest.TestCase):
    """Tests using the Hiuh resolver (via interpreter).

    Not yet implemented — will be filled in as resolver.hiuh grows.
    """

    def setUp(self):
        self.tokenizer = Tokenizer()
        self._repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        raise unittest.SkipTest("Hiuh resolver not yet implemented")

    def resolve(self, source, modules=None):
        raise unittest.SkipTest("Hiuh resolver not yet implemented")

    def assertResolvedEqual(self, source, expected_ast_nodes, modules=None):
        raise unittest.SkipTest("Hiuh resolver not yet implemented")

    def assertEqual(self, a, b, msg=None):
        unittest.TestCase.assertEqual(self, a, b, msg)


if __name__ == '__main__':
    unittest.main()
