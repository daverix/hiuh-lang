"""Resolver tests — tests AST output after resolver transformation.
Runs all tests against both the Python resolver and the Hiuh resolver."""
import os
import unittest
from hiuh.frontend.ast import *
from hiuh.frontend.module_registry import ModuleRegistry
from hiuh.frontend.parser import Parser
from hiuh.frontend.resolver import Resolver
from hiuh.frontend.tokenizer import Tokenizer
from tests.ast_format import ast_to_string

class _BaseResolverTests:
    """Mixin with resolver tests. Subclasses provide resolve(source)."""

    def resolve(self, source, modules=None):
        raise NotImplementedError

    def assertResolvedEqual(self, source, expected_ast_nodes, modules=None):
        raise NotImplementedError

    def assertEqual(self, a, b, msg=None):
        raise NotImplementedError

    def test_casting_to_type(self):
        source = "sätt x till 5 som text"
        expected = [AssignNode(None, None, name='x', value=CastNode(None, None, value=IntNode(None, None, '5'), target_type='text'))]
        self.assertResolvedEqual(source, expected)

    def test_casting_to_character(self):
        source = "sätt x till 65 som tecken"
        expected = [AssignNode(None, None, name='x', value=CastNode(None, None, value=IntNode(None, None, '65'), target_type='tecken'))]
        self.assertResolvedEqual(source, expected)

    def test_casting_som_text(self):
        source = "sätt x till 123 som text"
        expected = [AssignNode(None, None, name='x', value=CastNode(None, None, value=IntNode(None, None, '123'), target_type='text'))]
        self.assertResolvedEqual(source, expected)

    def test_file_close(self):
        source = "stäng fil"
        expected = [CloseFileNode(None, None, target_var='fil')]
        self.assertResolvedEqual(source, expected)

    def test_list_length(self):
        source = """\
sätt frukt till lista med äpple
skriv längd från frukt"""
        expected = [AssignNode(None, None, name='frukt', value=FunctionCallNode(None, None, name='lista', args=[StringNode(None, None, 'äpple')])), PrintNode(None, None, value=PropertyAccessNode(None, None, property_name='längd', target=VarAccessNode(None, None, 'frukt')))]
        self.assertResolvedEqual(source, expected)

    def test_element_access(self):
        source = "skriv element 0 från lista"
        expected = [PrintNode(None, None, value=ElementAccessNode(None, None, index=IntNode(None, None, '0'), target=VarAccessNode(None, None, 'lista')))]
        self.assertResolvedEqual(source, expected)

    def test_list_membership_contains(self):
        source = """\
använd listor

sätt färger till lista med röd, grön
om färger innehåller röd
    skriv Japp
om färger innehåller blå
    skriv Nej"""
        expected = [ImportNode(None, None, module_name='listor', import_all=True, resolved=True), AssignNode(None, None, name='färger', value=FunctionCallNode(None, None, name='lista', args=[StringNode(None, None, 'röd'), StringNode(None, None, 'grön')])), IfNode(None, None, conditions=[IfCondition(None, None, test=InfixCallNode(None, None, left=VarAccessNode(None, None, 'färger'), operator='innehåller', right=StringNode(None, None, 'röd')), block=[PrintNode(None, None, StringNode(None, None, 'Japp'))])]), IfNode(None, None, conditions=[IfCondition(None, None, test=InfixCallNode(None, None, left=VarAccessNode(None, None, 'färger'), operator='innehåller', right=StringNode(None, None, 'blå')), block=[PrintNode(None, None, StringNode(None, None, 'Nej'))])])]
        self.assertResolvedEqual(source, expected)

    def test_comparison_with_property_target(self):
        source = """\
sätt frukt till lista med äpple
om x är mindre än längd från frukt
    skriv hej"""
        expected = [AssignNode(None, None, name='frukt', value=FunctionCallNode(None, None, name='lista', args=[StringNode(None, None, 'äpple')])), IfNode(None, None, conditions=[IfCondition(None, None, test=LessThanNode(None, None, left=VarAccessNode(None, None, 'x'), right=PropertyAccessNode(None, None, property_name='längd', target=VarAccessNode(None, None, 'frukt'))), block=[PrintNode(None, None, StringNode(None, None, 'hej'))])])]
        self.assertResolvedEqual(source, expected)

    def test_är_comparison_with_defined_variable(self):
        source = """\

sätt x till 10
om x är mindre än 5
    skriv hej
"""
        expected = [AssignNode(None, None, name='x', value=IntNode(None, None, '10')), IfNode(None, None, conditions=[IfCondition(None, None, test=LessThanNode(None, None, left=VarAccessNode(None, None, 'x'), right=IntNode(None, None, '5')), block=[PrintNode(None, None, StringNode(None, None, 'hej'))])])]
        self.assertResolvedEqual(source, expected)

    def test_är_comparison_with_unresolved_variable(self):
        source = "skriv x är mindre än 5"
        expected = [PrintNode(None, None, value=StringNode(None, None, 'x är mindre än 5'))]
        self.assertResolvedEqual(source, expected)

    def test_not_equal_comparison(self):
        source = """\

sätt x till 10
om x är inte 5
    skriv japp
om x är inte lika med 3
    skriv japp2
"""
        expected = [AssignNode(None, None, name='x', value=IntNode(None, None, '10')), IfNode(None, None, conditions=[IfCondition(None, None, test=NotEqualNode(None, None, left=VarAccessNode(None, None, 'x'), right=IntNode(None, None, '5')), block=[PrintNode(None, None, StringNode(None, None, 'japp'))])]), IfNode(None, None, conditions=[IfCondition(None, None, test=NotEqualNode(None, None, left=VarAccessNode(None, None, 'x'), right=IntNode(None, None, '3')), block=[PrintNode(None, None, StringNode(None, None, 'japp2'))])])]
        self.assertResolvedEqual(source, expected)

    def test_modulo_resolver(self):
        source = """\

sätt x till 10
sätt y till resten av x delat med 3
sätt z till resten av x delat på 4
"""
        expected = [AssignNode(None, None, name='x', value=IntNode(None, None, '10')), AssignNode(None, None, name='y', value=ModNode(None, None, left=VarAccessNode(None, None, 'x'), right=IntNode(None, None, '3'))), AssignNode(None, None, name='z', value=ModNode(None, None, left=VarAccessNode(None, None, 'x'), right=IntNode(None, None, '4')))]
        self.assertResolvedEqual(source, expected)

    def test_modulo_with_nested_expressions(self):
        source = "sätt x till resten av 3 gånger 2 delat på 4"
        expected = [AssignNode(None, None, name='x', value=ModNode(None, None, left=MulNode(None, None, left=IntNode(None, None, '3'), right=IntNode(None, None, '2')), right=IntNode(None, None, '4')))]
        self.assertResolvedEqual(source, expected)

    def test_infix_function_body_property_access(self):
        source = """\
sätt innehåller till infixgrej med värden som lista av heltal, värde som heltal ger boolesk
    sätt x till 0
    medan x är mindre än längd från värden
        ge SANT"""
        expected = [AssignNode(None, None, name='innehåller', value=FunctionDefNode(None, None, params=[('värden', 'lista av heltal'), ('värde', 'heltal')], body=[AssignNode(None, None, name='x', value=IntNode(None, None, '0')), WhileNode(None, None, condition=LessThanNode(None, None, left=VarAccessNode(None, None, 'x'), right=PropertyAccessNode(None, None, property_name='längd', target=VarAccessNode(None, None, 'värden'))), body=[ReturnNode(None, None, value=BoolNode(None, None, True))])], is_infix=True, return_type='boolesk'))]
        self.assertResolvedEqual(source, expected)

    def test_normal_function_body_property_access(self):
        source = """\
sätt foo till grej med a som heltal, b som heltal ger heltal
    skriv a är mindre än längd från b"""
        expected = [AssignNode(None, None, name='foo', value=FunctionDefNode(None, None, params=[('a', 'heltal'), ('b', 'heltal')], body=[PrintNode(None, None, value=LessThanNode(None, None, left=VarAccessNode(None, None, 'a'), right=PropertyAccessNode(None, None, property_name='längd', target=VarAccessNode(None, None, 'b'))))], is_infix=False, return_type='heltal'))]
        self.assertResolvedEqual(source, expected)

    def test_infix_function_custom_definition(self):
        source = """\
sätt är del av till infixgrej med del som heltal, helhet som lista av heltal ger boolesk
    sätt x till 0
    ge FALSKT"""
        expected = [AssignNode(None, None, name='är del av', value=FunctionDefNode(None, None, params=[('del', 'heltal'), ('helhet', 'lista av heltal')], body=[AssignNode(None, None, name='x', value=IntNode(None, None, '0')), ReturnNode(None, None, value=BoolNode(None, None, False))], is_infix=True, return_type='boolesk'))]
        self.assertResolvedEqual(source, expected)

    def test_infix_function_call_in_comparison(self):
        source = """\
sätt är del av till infixgrej med del som heltal, helhet som lista av heltal ger boolesk
    ge FALSKT
om grön är del av färger
    skriv Hittat"""
        expected = [AssignNode(None, None, name='är del av', value=FunctionDefNode(None, None, params=[('del', 'heltal'), ('helhet', 'lista av heltal')], body=[ReturnNode(None, None, value=BoolNode(None, None, False))], is_infix=True, return_type='boolesk')), IfNode(None, None, conditions=[IfCondition(None, None, test=InfixCallNode(None, None, left=StringNode(None, None, 'grön'), operator='är del av', right=StringNode(None, None, 'färger')), block=[PrintNode(None, None, StringNode(None, None, 'Hittat'))])])]
        self.assertResolvedEqual(source, expected)

    def test_named_args_in_function_call(self):
        source = """\
sätt beräkna till grej med a som heltal, b som heltal ger heltal
    ge 0
sätt resultat till beräkna med a 5, b 3"""
        expected = [AssignNode(None, None, name='beräkna', value=FunctionDefNode(None, None, params=[('a', 'heltal'), ('b', 'heltal')], body=[ReturnNode(None, None, value=IntNode(None, None, '0'))], is_infix=False, return_type='heltal')), AssignNode(None, None, name='resultat', value=FunctionCallNode(None, None, name='beräkna', args=[NamedArgNode(None, None, name='a', value=IntNode(None, None, '5')), NamedArgNode(None, None, name='b', value=IntNode(None, None, '3'))]))]
        self.assertResolvedEqual(source, expected)

    def test_try_catch_finally(self):
        source = """\

försök
    kasta Ojdå
fånga fel
    skriv fel
slutligen
    skriv mellanrum plus och hejdå
"""
        expected = [TryCatchNode(None, None, try_block=[UnaryOpNode(None, None, op='kasta', operand=StringNode(None, None, 'Ojdå'))], error_var='fel', catch_block=[PrintNode(None, None, VarAccessNode(None, None, 'fel'))], finally_block=[PrintNode(None, None, AddNode(None, None, VarAccessNode(None, None, 'mellanrum'), StringNode(None, None, 'och hejdå')))])]
        self.assertResolvedEqual(source, expected)

    def test_for_each_loop(self):
        source = """\
sätt min lista till lista med a, b, c
för varje mitt index i min lista
    skriv mitt index"""
        expected = [AssignNode(None, None, name='min lista', value=FunctionCallNode(None, None, name='lista', args=[StringNode(None, None, 'a'), StringNode(None, None, 'b'), StringNode(None, None, 'c')])), ForEachNode(None, None, variable='mitt index', iterable=VarAccessNode(None, None, 'min lista'), body=[PrintNode(None, None, value=VarAccessNode(None, None, 'mitt index'))])]
        self.assertResolvedEqual(source, expected)

    def test_try_finally(self):
        source = """\

försök
    skriv hej
slutligen
    skriv mellanrum plus och hejdå
"""
        expected = [TryCatchNode(None, None, try_block=[PrintNode(None, None, StringNode(None, None, 'hej'))], error_var=None, catch_block=[], finally_block=[PrintNode(None, None, AddNode(None, None, VarAccessNode(None, None, 'mellanrum'), StringNode(None, None, 'och hejdå')))])]
        self.assertResolvedEqual(source, expected)

    def test_infix_funktion_custom_definition(self):
        source = """\

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
        expected = [AssignNode(None, None, name='är del av', value=FunctionDefNode(None, None, params=[('del', 'heltal'), ('helhet', 'lista av heltal')], body=[AssignNode(None, None, name='x', value=IntNode(None, None, '0')), WhileNode(None, None, condition=LessThanNode(None, None, left=VarAccessNode(None, None, 'x'), right=PropertyAccessNode(None, None, property_name='längd', target=VarAccessNode(None, None, 'helhet'))), body=[IfNode(None, None, conditions=[IfCondition(None, None, test=EqualNode(None, None, left=ElementAccessNode(None, None, index=VarAccessNode(None, None, 'x'), target=VarAccessNode(None, None, 'helhet')), right=VarAccessNode(None, None, 'del')), block=[ReturnNode(None, None, value=BoolNode(None, None, True))])]), AssignNode(None, None, name='x', value=AddNode(None, None, VarAccessNode(None, None, 'x'), IntNode(None, None, '1')))]), ReturnNode(None, None, value=BoolNode(None, None, False))], is_infix=True, return_type='boolesk')), AssignNode(None, None, name='färger', value=FunctionCallNode(None, None, name='lista', args=[StringNode(None, None, 'röd'), StringNode(None, None, 'grön'), StringNode(None, None, 'blå')])), IfNode(None, None, conditions=[IfCondition(None, None, test=InfixCallNode(None, None, left=StringNode(None, None, 'grön'), operator='är del av', right=VarAccessNode(None, None, 'färger')), block=[PrintNode(None, None, StringNode(None, None, 'Hittat'))])]), IfNode(None, None, conditions=[IfCondition(None, None, test=InfixCallNode(None, None, left=StringNode(None, None, 'gul'), operator='är del av', right=VarAccessNode(None, None, 'färger')), block=[PrintNode(None, None, StringNode(None, None, 'Saknas'))])]), AssignNode(None, None, name='resultat', value=InfixCallNode(None, None, left=StringNode(None, None, 'blå'), operator='är del av', right=VarAccessNode(None, None, 'färger'))), PrintNode(None, None, value=VarAccessNode(None, None, 'resultat'))]
        self.assertResolvedEqual(source, expected)

    def test_listor_utility_callbacks(self):
        source = """\

använd listor

sätt matchar_hiuh till grej med text_stycke som sträng ger boolesk
    ge text_stycke lika med Hiuh

sätt namn_lista till lista med Java, Python, Hiuh, Kotlin

sätt hittat_index till index på första matchande med namn_lista, matchar_hiuh
sätt hittat_namn till första matchande med namn_lista, matchar_hiuh
"""
        expected = [ImportNode(None, None, module_name='listor', import_all=True, resolved=True), AssignNode(None, None, name='matchar_hiuh', value=FunctionDefNode(None, None, params=[('text_stycke', 'sträng')], body=[ReturnNode(None, None, value=EqualNode(None, None, left=VarAccessNode(None, None, 'text_stycke'), right=StringNode(None, None, 'Hiuh')))], is_infix=False, return_type='boolesk')), AssignNode(None, None, name='namn_lista', value=FunctionCallNode(None, None, name='lista', args=[StringNode(None, None, 'Java'), StringNode(None, None, 'Python'), StringNode(None, None, 'Hiuh'), StringNode(None, None, 'Kotlin')])), AssignNode(None, None, name='hittat_index', value=FunctionCallNode(None, None, name='index på första matchande', args=[VarAccessNode(None, None, 'namn_lista'), VarAccessNode(None, None, 'matchar_hiuh')])), AssignNode(None, None, name='hittat_namn', value=FunctionCallNode(None, None, name='första matchande', args=[VarAccessNode(None, None, 'namn_lista'), VarAccessNode(None, None, 'matchar_hiuh')]))]
        self.assertResolvedEqual(source, expected)

    def test_named_args_grej_function(self):
        source = """\

sätt add till grej med a som heltal, b som heltal ger heltal
    ge a plus b

sätt resultat till add med a 5, b 3
skriv resultat
"""
        expected = [AssignNode(None, None, name='add', value=FunctionDefNode(None, None, params=[('a', 'heltal'), ('b', 'heltal')], body=[ReturnNode(None, None, value=AddNode(None, None, left=VarAccessNode(None, None, 'a'), right=VarAccessNode(None, None, 'b')))], is_infix=False, return_type='heltal')), AssignNode(None, None, name='resultat', value=FunctionCallNode(None, None, name='add', args=[NamedArgNode(None, None, name='a', value=IntNode(None, None, '5')), NamedArgNode(None, None, name='b', value=IntNode(None, None, '3'))])), PrintNode(None, None, value=VarAccessNode(None, None, 'resultat'))]
        self.assertResolvedEqual(source, expected)

    def test_element_assign_int_index(self):
        source = """\

sätt element 0 i lista till 42
        """
        expected = [ElementAssignNode(None, None, index=IntNode(None, None, '0'), target=VarAccessNode(None, None, 'lista'), value=IntNode(None, None, '42'))]
        self.assertResolvedEqual(source, expected)

    def test_element_assign_variable_index(self):
        source = """\

sätt x till 2
sätt element x i lista till hello
        """
        expected = [AssignNode(None, None, 'x', IntNode(None, None, 2)), ElementAssignNode(None, None, index=VarAccessNode(None, None, 'x'), target=VarAccessNode(None, None, 'lista'), value=StringNode(None, None, 'hello'))]
        self.assertResolvedEqual(source, expected)

    def test_element_assign_in_function(self):
        source = """\

sätt uppdatera till grej med lst som lista av heltal ger heltal
    sätt element 0 i lst till 100
    ge element 0 från lst
        """
        expected = [AssignNode(None, None, name='uppdatera', value=FunctionDefNode(None, None, params=[('lst', 'lista av heltal')], body=[ElementAssignNode(None, None, index=IntNode(None, None, '0'), target=VarAccessNode(None, None, 'lst'), value=IntNode(None, None, '100')), ReturnNode(None, None, value=ElementAccessNode(None, None, index=IntNode(None, None, '0'), target=VarAccessNode(None, None, 'lst')))], is_infix=False, return_type='heltal'))]
        self.assertResolvedEqual(source, expected)

    def test_längd_från_property_minus_expression(self):
        source = """\

sätt värden till lista av heltal
sätt x till längd från värden minus 1
"""
        expected = [AssignNode(None, None, name='värden', value=FunctionCallNode(None, None, name='lista', args=[])), AssignNode(None, None, name='x', value=SubNode(None, None, left=PropertyAccessNode(None, None, property_name='längd', target=VarAccessNode(None, None, 'värden')), right=IntNode(None, None, '1')))]
        self.assertResolvedEqual(source, expected)

    def test_cannot_reassign_builtin_function(self):
        source = """\

sätt lista till lista med 10, 20
"""
        with self.assertRaises(Exception) as context:
            self.resolve(source)
        self.assertIn("Kan inte omdefiniera inbyggd funktion 'lista'", str(context.exception))

    def test_resolver_increment_decrement(self):
        source = """\

sätt poäng till 10
öka poäng med 5 plus 2
minska poäng med 1
"""
        expected = [AssignNode(None, None, name='poäng', value=IntNode(None, None, '10')), AddAssignNode(None, None, target='poäng', value=AddNode(None, None, left=IntNode(None, None, '5'), right=IntNode(None, None, '2'))), SubAssignNode(None, None, target='poäng', value=IntNode(None, None, '1'))]
        self.assertResolvedEqual(source, expected)

    def test_resolver_multiply_divide_assign(self):
        source = """\

sätt poäng till 10
gångra poäng med 3 plus 1
dela poäng med 2
"""
        expected = [AssignNode(None, None, name='poäng', value=IntNode(None, None, '10')), MultiplyAssignNode(None, None, target='poäng', value=AddNode(None, None, left=IntNode(None, None, '3'), right=IntNode(None, None, '1'))), DivideAssignNode(None, None, target='poäng', value=IntNode(None, None, '2'))]
        self.assertResolvedEqual(source, expected)

    def test_delstrang_function_call_ast(self):
        source = """\

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
        expected = [AssignNode(None, None, name='delsträng', value=FunctionDefNode(None, None, params=[('text', 'sträng'), ('start', 'heltal'), ('längd', 'heltal')], body=[AssignNode(None, None, name='resultat', value=StringNode(None, None, '')), AssignNode(None, None, name='pos', value=VarAccessNode(None, None, 'start')), AssignNode(None, None, name='slut', value=AddNode(None, None, left=VarAccessNode(None, None, 'start'), right=VarAccessNode(None, None, 'längd'))), WhileNode(None, None, condition=AndNode(None, None, left=LessThanNode(None, None, left=VarAccessNode(None, None, 'pos'), right=VarAccessNode(None, None, 'slut')), right=LessThanNode(None, None, left=VarAccessNode(None, None, 'pos'), right=PropertyAccessNode(None, None, property_name='längd', target=VarAccessNode(None, None, 'text')))), body=[AssignNode(None, None, name='resultat', value=AddNode(None, None, left=VarAccessNode(None, None, 'resultat'), right=ElementAccessNode(None, None, target=VarAccessNode(None, None, 'text'), index=VarAccessNode(None, None, 'pos')))), AddAssignNode(None, None, target='pos', value=IntNode(None, None, '1'))]), ReturnNode(None, None, value=VarAccessNode(None, None, 'resultat'))], return_type='sträng')), AssignNode(None, None, name='rad', value=StringNode(None, None, 'hejsan')), AssignNode(None, None, name='res', value=FunctionCallNode(None, None, name='delsträng', args=[VarAccessNode(None, None, 'rad'), IntNode(None, None, '1'), IntNode(None, None, '3')])), PrintNode(None, None, value=VarAccessNode(None, None, 'res'))]
        self.assertResolvedEqual(source, expected)

    def test_element_access_with_arithmetic_index_ast(self):
        source = """\

sätt pos till 1
sätt innehåll till "hejsan"
sätt nästa_tecken till element pos plus 1 från innehåll
"""
        expected = [AssignNode(None, None, name='pos', value=IntNode(None, None, '1')), AssignNode(None, None, name='innehåll', value=StringNode(None, None, 'hejsan')), AssignNode(None, None, name='nästa_tecken', value=ElementAccessNode(None, None, target=VarAccessNode(None, None, 'innehåll'), index=AddNode(None, None, left=VarAccessNode(None, None, 'pos'), right=IntNode(None, None, '1'))))]
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
        expected = [AssignNode(None, None, name='x', value=FunctionCallNode(None, None, name='lista', args=[]))]
        self.assertResolvedEqual(source, expected)

    def test_verb_grej_definition_and_call(self):
        source = """\

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
        expected = [AssignNode(None, None, name='upprepa', value=FunctionDefNode(None, None, params=[('ord', 'sträng'), ('antal', 'heltal')], body=[AssignNode(None, None, name='resultat', value=StringNode(None, None, '')), AssignNode(None, None, name='i', value=IntNode(None, None, '0')), WhileNode(None, None, condition=LessThanNode(None, None, left=VarAccessNode(None, None, 'i'), right=VarAccessNode(None, None, 'antal')), body=[AssignNode(None, None, name='resultat', value=AddNode(None, None, left=VarAccessNode(None, None, 'resultat'), right=VarAccessNode(None, None, 'ord'))), AddAssignNode(None, None, target='i', value=IntNode(None, None, '1'))]), ReturnNode(None, None, value=VarAccessNode(None, None, 'resultat'))], is_infix=False, return_type='sträng')), AssignNode(None, None, name='a', value=StringNode(None, None, 'hej')), AssignNode(None, None, name='a', value=FunctionCallNode(None, None, name='upprepa', args=[VarAccessNode(None, None, 'a'), IntNode(None, None, '3')]))]
        self.assertResolvedEqual(source, expected)

    def test_skicka_grej_definition_and_call(self):
        source = """\

sätt lägg_till till skickagrej med sak som sträng, mål som lista av sträng ger lista av sträng
    lägg till sak i mål
    ge mål

sätt min lista till lista av sträng
lägg_till hej till min lista
"""
        expected = [AssignNode(None, None, name='lägg_till', value=FunctionDefNode(None, None, params=[('sak', 'sträng'), ('mål', 'lista av sträng')], body=[AppendNode(None, None, value=VarAccessNode(None, None, 'sak'), target_list='mål'), ReturnNode(None, None, value=VarAccessNode(None, None, 'mål'))], is_infix=False, return_type='lista av sträng')), AssignNode(None, None, name='min lista', value=FunctionCallNode(None, None, name='lista', args=[])), AssignNode(None, None, name='min lista', value=FunctionCallNode(None, None, name='lägg_till', args=[StringNode(None, None, 'hej'), VarAccessNode(None, None, 'min lista')]))]
        self.assertResolvedEqual(source, expected)

    def test_hämta_grej_definition_and_call(self):
        source = """\

sätt plocka till hämtagrej med namn som sträng, källa som lista av sträng ger sträng
    ge element 0 från källa

sätt frukter till lista av sträng med äpple, banan
sätt resultat till plocka banan från frukter
"""
        expected = [AssignNode(None, None, name='plocka', value=FunctionDefNode(None, None, params=[('namn', 'sträng'), ('källa', 'lista av sträng')], body=[ReturnNode(None, None, value=ElementAccessNode(None, None, index=IntNode(None, None, '0'), target=VarAccessNode(None, None, 'källa')))], is_infix=False, return_type='sträng')), AssignNode(None, None, name='frukter', value=FunctionCallNode(None, None, name='lista', args=[StringNode(None, None, 'äpple'), StringNode(None, None, 'banan')])), AssignNode(None, None, name='resultat', value=FunctionCallNode(None, None, name='plocka', args=[StringNode(None, None, 'banan'), VarAccessNode(None, None, 'frukter')]))]
        self.assertResolvedEqual(source, expected)

    def test_nested_function_call_resolves_correctly(self):
        source = """\
sätt yttre till grej med x som heltal ger heltal
    sätt dubblera till grej med v som heltal ger heltal
        ge v gånger 2
    sätt resultat till dubblera med x
    ge resultat
"""
        resolved = self.resolve(source)
        yttre_def = resolved[0]
        self.assertIsInstance(yttre_def, AssignNode)
        yttre_body = yttre_def.value.body
        assign_resultat = next((s for s in yttre_body if isinstance(s, AssignNode) and s.name == 'resultat'))
        self.assertIsInstance(assign_resultat.value, FunctionCallNode, f"Call to 'dubblera med x' must be FunctionCallNode, got {type(assign_resultat.value).__name__}")

    def test_struct_field_wrong_type_raises(self):
        source = """\
typ mittresultat
    nod som heltal
    pos som heltal
sätt foo till grej med x som sträng ger mittresultat
    ge mittresultat med nod x, pos 0
"""
        with self.assertRaises(Exception) as ctx:
            self.resolve(source)
        self.assertIn("Typfel", str(ctx.exception))
        self.assertIn("nod", str(ctx.exception))

    def test_struct_field_correct_type_passes(self):
        source = """\
typ mittresultat
    nod som heltal
    pos som heltal
sätt foo till grej med x som heltal ger mittresultat
    ge mittresultat med nod x, pos 0
"""
        self.resolve(source)

    def test_list_wrong_element_type_raises(self):
        source = """\
sätt foo till grej med x som heltal ger lista av sträng
    ge lista med "hej", x
"""
        with self.assertRaises(Exception) as ctx:
            self.resolve(source)
        self.assertIn("Typfel", str(ctx.exception))

    def test_list_correct_element_type_passes(self):
        source = """\
sätt foo till grej med x som sträng ger lista av sträng
    ge lista med "hej", x
"""
        self.resolve(source)

    def test_bool_literals_resolve(self):
        source = """\
skriv SANT
skriv FALSKT"""
        expected = [PrintNode(None, None, value=BoolNode(None, None, True)), PrintNode(None, None, value=BoolNode(None, None, False))]
        self.assertResolvedEqual(source, expected)

    def test_grej_allows_self_recursion(self):
        source = """\
sätt nedräkning till grej med n som heltal ger heltal
    om n är mindre än 1
        ge 0
    sätt nästa till n minus 1
    ge nedräkning med nästa
"""
        resolved = self.resolve(source)
        fn_def = resolved[0]
        body = fn_def.value.body
        return_stmt = body[-1]
        self.assertIsInstance(return_stmt.value, FunctionCallNode, f'Self-call should be FunctionCallNode, got {type(return_stmt.value).__name__}')

    def test_grej_blocks_forward_reference_to_sibling(self):
        source = """\
sätt yttre till grej med x som heltal ger heltal
    sätt tidig till grej med v som heltal ger heltal
        ge sen med v
    sätt sen till grej med v som heltal ger heltal
        ge v gånger 2
    ge tidig med x
"""
        resolved = self.resolve(source)
        yttre_body = resolved[0].value.body
        tidig_def = next((s for s in yttre_body if isinstance(s, AssignNode) and s.name == 'tidig'))
        tidig_body = tidig_def.value.body
        return_stmt = tidig_body[0]
        self.assertIsInstance(return_stmt.value, StringNode, f'Forward ref to nested sibling with grej should be StringNode, got {type(return_stmt.value).__name__}')

    def test_return_variable_type_mismatch_raises(self):
        """Returning a variable of wrong type must raise Typfel."""
        source = """\
sätt foo till grej med ger heltal
    sätt x till lista av sträng
    ge x
"""
        with self.assertRaises(Exception) as ctx:
            self.resolve(source)
        self.assertIn("Typfel", str(ctx.exception))

    def test_return_variable_correct_type_passes(self):
        """Returning a variable of correct type must pass."""
        source = """\
sätt foo till grej med ger lista av sträng
    sätt x till lista av sträng
    ge x
"""
        self.resolve(source)

    def test_rekgrej_allows_mutual_recursion_between_siblings(self):
        source = """\
sätt jämn till rekgrej med n som heltal ger boolesk
    om n är 0
        ge SANT
    ge udda med n minus 1
sätt udda till rekgrej med n som heltal ger boolesk
    om n är 0
        ge FALSKT
    ge jämn med n minus 1
"""
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
            return node.value
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
    """Tests using the Hiuh tokeniserare + parser + resolver + formatera."""

    def setUp(self):
        self.tokenizer = Tokenizer()
        self._repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def resolve(self, source, modules=None):
        """Run source through full hiuh pipeline, return formatted strings."""
        from hiuh.backend.interpreter.interpreter import Interpreter, ReturnException
        from hiuh.frontend.module_registry import ModuleRegistry
        from hiuh.frontend.resolver import Resolver
        lines = source.split("\n")
        line_strings = ', '.join((f'"{line}"' for line in lines))
        hiuh_source = f'använd parser\nanvänd tokeniserare\nanvänd resolver\nanvänd testinterop\n\nsätt källkod till lista med {line_strings}\n\nsätt tokens till tokenisera med källkod\nsätt rå ast till parsa med tokens\nsätt löst ast till lös med rå ast\nge formatera med löst ast\n'
        mr = ModuleRegistry("/tmp/hiuh_resolver_test")
        resolver_py = Resolver(mr, os.path.join(self._repo_root, "hiuh_i_hiuh"))
        tokens_py = self.tokenizer.tokenize(hiuh_source)
        parser_py = Parser(tokens_py)
        ast = parser_py.parse()
        resolver_py.discover_modules_from_ast("main", ast, self._repo_root)
        resolver_py.discover_imports("main")
        resolver_py.resolve_all()
        ast = resolver_py.get_ast("main")
        interp = Interpreter(mr)
        interp.modules = resolver_py.modules
        try:
            interp.execute(ast)
        except ReturnException as e:
            result = e.value
            if isinstance(result, list):
                return result
        return []

    def assertResolvedEqual(self, source, expected_ast_nodes, modules=None):
        actual = self.resolve(source)
        expected = [ast_to_string([n]) for n in expected_ast_nodes]
        expected = [s[1:-1] if s.startswith('[') and s.endswith(']') else s for s in expected]
        self.assertEqual(actual, expected)

    def assertEqual(self, a, b, msg=None):
        unittest.TestCase.assertEqual(self, a, b, msg)
if __name__ == '__main__':
    unittest.main()