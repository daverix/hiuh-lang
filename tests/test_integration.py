import os
import unittest
from io import StringIO
from unittest.mock import patch
from hiuh.backend.interpreter.interpreter import Interpreter
from hiuh.frontend.module_registry import ModuleRegistry
from hiuh.frontend.parser import Parser
from hiuh.frontend.resolver import Resolver
from hiuh.frontend.tokenizer import Tokenizer

class TestHiuhFullIntegration(unittest.TestCase):

    def setUp(self):
        self.tokenizer = Tokenizer()
        self.repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.hiuh_folder = os.path.join(self.repo_root, "hiuh_i_hiuh")
        self.module_registry = ModuleRegistry(os.path.join(self.repo_root, "build", "symbols"))
        self.interpreter = Interpreter(self.module_registry)

    def run_source(self, source, script_dir=None):
        tokens = self.tokenizer.tokenize(source)
        parser = Parser(tokens)
        nodes = parser.parse()
        resolver = Resolver(self.module_registry, self.hiuh_folder, script_dir)
        resolver.discover_modules_from_ast("main", nodes, script_dir)
        resolver.discover_imports('main')
        resolver.resolve_all()
        nodes = resolver.get_ast("main")
        if script_dir:
            self.interpreter.script_dir_stack = [script_dir]
        return self.interpreter.execute(nodes)

    def test_arithmetic_precedence(self):
        """Tests that multiplication happens before addition (3 + 4 * 2 = 11)."""
        source = "skriv 3 plus 4 gånger 2"
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "11")

    def test_greedy_string_assignment(self):
        """Tests the README rule: anything after TILL that isn't a type is a string."""
        source = """\
sätt x till detta är en hemlighet
skriv x"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "detta är en hemlighet")

    def test_if_else_logic(self):
        """Tests control flow logic with Swedish comparison operators."""
        source = """\

sätt poäng till 85
om poäng större än eller lika med 50
    skriv godkänd
annars
    skriv underkänd
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "godkänd")

    def test_function_definition_and_call(self):
        """Tests function scope and return values."""
        source = """\

sätt hälsa till grej med namn som sträng ger sträng
    ge hej plus mellanrum plus namn

sätt meddelande till hälsa med Hiuh
skriv meddelande
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "hej Hiuh")

    def test_try_catch_blocks(self):
        """Tests the Swedish error handling keywords."""
        source = """\

försök
    kasta ett fel inträffade
fånga meddelande
    skriv meddelande
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "ett fel inträffade")

    def test_newline_swedish_literal(self):
        """Tests that 'ny rad' is interpreted as a newline character."""
        source = """\
skriv rad1
skriv ny rad
skriv rad2"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue(), "rad1\nrad2")

    def test_custom_type_bil(self):
        """Tests dynamic type definition and field access for a 'bil' type."""
        source = """\

typ bil
    märke som sträng
    modell som sträng
    år som heltal
sätt min bil till bil med Volvo, V60, 2020
sätt uppdaterad bil till kopia av min bil med år 2024

skriv märke från min bil
skriv ny rad
skriv år från uppdaterad bil
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue(), "Volvo\n2024")

    def test_stdin_input_inmatning(self):
        """Tests that 'inmatning' correctly reads from simulated stdin."""
        source = """\

sätt svar till inmatning
skriv Hej plus mellanrum plus svar
"""
        with patch('sys.stdin', StringIO("Daverix\n")):
            with patch('sys.stdout', new=StringIO()) as fake_out:
                self.run_source(source)
                self.assertEqual(fake_out.getvalue().strip(), "Hej Daverix")

    def test_multiple_concatenation(self):
        """Tests joining three parts together."""
        source = "skriv ett plus mellanrum plus två plus mellanrum plus tre"
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "ett två tre")

    def test_list_set_and_get(self):
        source = """\

sätt min_lista till lista med röd, grön
sätt element 0 i min_lista till blå
skriv element 0 från min_lista
skriv element 1 från min_lista
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "blågrön")

    def test_list_length(self):
        """Verify 'längd från [lista]' syntax."""
        source = """\

sätt frukter till lista med äpple, banan
skriv längd från frukter
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "2")

    def test_casting_som_tal(self):
        """Tests that strings can be converted to numbers for math."""
        source = """\
sätt x till 10 som tal
skriv x plus 5"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "15")

    def test_casting_som_text(self):
        """Tests converting a number back to text."""
        source = """\
sätt x till 100 som text
sätt y till 2 som text
skriv x plus y plus mellanrum plus är ett stort tal"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "1002 är ett stort tal")

    def test_list_append_lägg_till(self):
        """Verify adding items to a list using 'lägg till'."""
        source = """\

sätt frukter till lista med äpple
lägg till banan i frukter
skriv element 1 från frukter
skriv mellanrum
skriv element 0 från frukter
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "banan äpple")

    def test_list_removal_mixed(self):
        """Verify removal by value AND by index."""
        source = """\

sätt frukter till lista med äpple, banan, citron
ta bort banan från frukter
ta bort element 1 från frukter
skriv element 0 från frukter
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "äpple")

    def test_list_membership_contains(self):
        """Verify 'lista innehåller värde' as a boolean check."""
        source = """\

använd listor

sätt färger till lista med röd, grön
om färger innehåller röd
    skriv Japp
om färger innehåller blå
    skriv Nej
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "Japp")

    def test_file_stream_operations(self):
        filename = "data.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write("Första raden\nAndra raden")
        try:
            source = """\

öppna data.txt som min fil
skriv nästa rad från min fil
stäng min fil
"""
            with patch('sys.stdout', new=StringIO()) as fake_out:
                self.run_source(source)
                self.assertEqual(fake_out.getvalue().strip(), "Första raden")
        finally:
            if os.path.exists(filename):
                os.remove(filename)

    def test_file_write_overwrite(self):
        filename = "skrivtest.txt"
        try:
            source_1 = '\nöppna skrivtest.txt för skrivning som f\nskriv Första texten till f\nstäng f\n'
            self.run_source(source_1)
            source_2 = '\nöppna skrivtest.txt för skrivning som f\nskriv Ny text till f\nstäng f\nöppna skrivtest.txt för läsning som f2\nskriv nästa rad från f2\nstäng f2\n'
            with patch('sys.stdout', new=StringIO()) as fake_out:
                self.run_source(source_2)
                self.assertEqual(fake_out.getvalue().strip(), "Ny text")
        finally:
            if os.path.exists(filename):
                os.remove(filename)

    def test_try_catch_finally(self):
        source = """\

försök
    kasta Ojdå
fånga fel
    skriv fel
slutligen
    skriv mellanrum plus och hejdå
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "Ojdå och hejdå")

    def test_try_finally(self):
        source = """\

försök
    skriv hej
slutligen
    skriv mellanrum plus och hejdå
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "hej och hejdå")

    def test_for_each_loop(self):
        """Verify that for-each loops iterate correctly with multi-word variable."""
        source = """\

sätt min lista till lista med äpple, banan, körsbär
för varje mitt index i min lista
    skriv mitt index
    skriv ny rad
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue(), "äpple\nbanan\nkörsbär\n")

    def test_module_import_and_aliasing(self):
        module_filename = "hjälpare.hiuh"
        with open(module_filename, "w", encoding="utf-8") as f:
            f.write('\nsätt hälsa till grej med namn som sträng ger sträng\n    ge Hej plus mellanrum plus namn\n        ')
        try:
            source = """\

använd hjälpare som h
sätt meddelande till hälsa från h med David
skriv meddelande
skriv ny rad
skriv hälsa med David
    """
            with patch('sys.stdout', new=StringIO()) as fake_out:
                self.run_source(source)
                self.assertEqual(fake_out.getvalue().strip(), "Hej David\nhälsa med David")
        finally:
            if os.path.exists(module_filename):
                os.remove(module_filename)

    def test_module_wildcard_import(self):
        """Tests that 'använd modul' (without 'som') imports all variables directly."""
        module_filename = "test.hiuh"
        with open(module_filename, "w", encoding="utf-8") as f:
            f.write('\nsätt meddelande till Hej fràn Hiuh\nsätt faktor till 10\nsätt hälsa till grej med namn som sträng ger sträng\n    ge Hej plus mellanrum plus namn\n')
        try:
            source = """\

använd test
skriv meddelande
skriv faktor
sätt hälsning till hälsa med Världen
skriv hälsning
"""
            with patch('sys.stdout', new=StringIO()) as fake_out:
                self.run_source(source)
                self.assertEqual(fake_out.getvalue().strip(), "Hej fràn Hiuh10Hej Världen")
        finally:
            if os.path.exists(module_filename):
                os.remove(module_filename)

    def test_module_wildcard_import_conflict(self):
        """Tests that importing modules with conflicting variable names raises a SyntaxError."""
        module_a = "modul_a.hiuh"
        module_b = "modul_b.hiuh"
        with open(module_a, "w", encoding="utf-8") as f:
            f.write("sätt namn till Alfa\n")
        with open(module_b, "w", encoding="utf-8") as f:
            f.write("sätt namn till Beta\n")
        try:
            source = """\

använd modul_a
använd modul_b
"""
            with patch('sys.stdout', new=StringIO()) as fake_out:
                with self.assertRaises(SyntaxError) as cm:
                    self.run_source(source)
                self.assertIn("namn", str(cm.exception))
                self.assertIn("modul_a", str(cm.exception))
                self.assertIn("modul_b", str(cm.exception))
        finally:
            if os.path.exists(module_a):
                os.remove(module_a)
            if os.path.exists(module_b):
                os.remove(module_b)

    def test_module_directory_import(self):
        dir_name = "verktyg"
        module_filename = os.path.join(dir_name, "matematik.hiuh")
        os.makedirs(dir_name, exist_ok=True)
        with open(module_filename, "w", encoding="utf-8") as f:
            f.write('\nsätt addera till grej med a som heltal, b som heltal ger heltal\n    ge a plus b\n        ')
        try:
            source = """\

använd verktyg.matematik
sätt summa till addera med 10, 5
skriv summa
            """
            with patch('sys.stdout', new=StringIO()) as fake_out:
                self.run_source(source)
                self.assertEqual(fake_out.getvalue().strip(), "15")
        finally:
            if os.path.exists(module_filename):
                os.remove(module_filename)
            if os.path.exists(dir_name):
                os.rmdir(dir_name)

    def test_bootstrapping_sanity_step(self):
        """Verify Hiuh can read a file line-by-line and simulate a basic tokenizer loop."""
        target_file = "källkod_test.hiuh"
        with open(target_file, "w", encoding="utf-8") as f:
            f.write("sätt x till 10\nskriv x\n")
        try:
            source = """\

öppna källkod_test.hiuh för läsning som fil
sätt rad_nummer till 1

medan inte i slutet från fil
    sätt rad till nästa rad från fil
    
    . Inspect the first character of the line to find syntax shapes
    sätt första_tecken till element 0 från rad
    
    skriv rad_nummer plus . plus första_tecken plus mellanrum
    sätt rad_nummer till rad_nummer plus 1

stäng fil
"""
            with patch('sys.stdout', new=StringIO()) as fake_out:
                self.run_source(source)
                self.assertEqual(fake_out.getvalue(), "1.s 2.s ")
        finally:
            if os.path.exists(target_file):
                os.remove(target_file)

    def test_file_paths_with_and_without_spaces(self):
        """Verify that standard files are quote-less, but files with spaces use quotes."""
        file_simple = "källkod_test.hiuh"
        file_spaced = "mitt projekt.hiuh"
        with open(file_simple, 'w', encoding='utf-8') as f:
            f.write('sätt x till 1')
        with open(file_spaced, 'w', encoding='utf-8') as f:
            f.write('sätt y till 2')
        try:
            source = """\

öppna källkod_test.hiuh för läsning som f1
öppna "mitt projekt.hiuh" för läsning som f2
stäng f1
stäng f2
"""
            self.run_source(source)
        finally:
            if os.path.exists(file_simple):
                os.remove(file_simple)
            if os.path.exists(file_spaced):
                os.remove(file_spaced)

    def test_ascii_character_casting_symmetry(self):
        """Verify that string characters can be evaluated as ASCII integers and vice versa."""
        source = """\

. Skapa en textsträng som innehåller citattecken, mellanslag och kommatecken
. I källkoden kan vi skriva \' och " eftersom de är tillåtna som filnamns-escapes,
. men vi kan också generera dem via ASCII-koder!

sätt textrad till "A, B"
sätt första_tecken till element 0 från textrad
sätt andra_tecken till element 1 från textrad

. 1. Omvandla tecken till ASCII-koder (som tal)
sätt kod_A till första_tecken som tal
sätt kod_komma till andra_tecken som tal

. 2. Skapa tecken direkt från ASCII-koder (som tecken)
sätt genererat_mellanslag till 32 som tecken
sätt genererat_dubbelcitat till 34 som tecken

. 3. Skriv ut resultaten för verifiering
skriv kod_A plus mellanrum plus kod_komma plus mellanrum
skriv genererat_dubbelcitat plus Hej plus genererat_mellanslag plus Världen plus genererat_dubbelcitat
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            expected_output = '65 44 "Hej Världen"'
            self.assertEqual(fake_out.getvalue().strip(), expected_output)

    def test_listor_utility_callbacks(self):
        """Verify that listor.hiuh can be imported and executed with high-order callback functions."""
        source = """\

använd listor

. 1. Create a callback utility function to search for a specific name target
sätt matchar_hiuh till grej med text_stycke som sträng ger boolesk
    ge text_stycke lika med Hiuh

. 2. Initialize a flat sample list dataset
sätt namn_lista till lista med Java, Python, Hiuh, Kotlin

. 3. Invoke your high-order lookup functions using the callback
sätt hittat_index till index på första matchande med namn_lista, matchar_hiuh
sätt hittat_namn till första matchande med namn_lista, matchar_hiuh

skriv hittat_index plus mellanrum plus hittat_namn
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "2 Hiuh")

    def test_ordlista_builtin(self):
        """Verify built-in ordlista (dict) operations."""
        source = """\

sätt fruktantal till ordlista av sträng, heltal
putta äpple, 2 till fruktantal
putta banan, 1 till fruktantal

rensa banan till fruktantal

skriv hämta med äpple, fruktantal
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "2")

    def test_named_args_typ_constructor(self):
        """Test that typ constructors support named arguments in any order."""
        source = """\

typ person
    namn som sträng
    ålder som heltal
sätt p till person med ålder 37, namn David
skriv namn från p
skriv ny rad
skriv ålder från p
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue(), "David\n37")

    def test_named_args_typ_positional_still_works(self):
        """Test that typ constructors still support positional arguments."""
        source = """\

typ person
    namn som sträng
    ålder som heltal
sätt p till person med Eva, 25
skriv namn från p
skriv ny rad
skriv ålder från p
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue(), "Eva\n25")

    def test_named_args_kopia_av(self):
        """Test that kopia av supports named arguments."""
        source = """\

typ person
    namn som sträng
    ålder som heltal
sätt p till person med David, 37
sätt äldre till kopia av p med ålder 38
skriv ålder från p
skriv ny rad
skriv ålder från äldre
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue(), "37\n38")

    def test_named_args_grej_function(self):
        """Test that grej functions support named arguments."""
        source = """\

sätt add till grej med a som heltal, b som heltal ger heltal
    ge a plus b

sätt resultat till add med a 5, b 3
skriv resultat
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "8")

    def test_named_args_grej_positional_still_works(self):
        """Test that grej functions still support positional arguments."""
        source = """\

sätt add till grej med x som heltal, y som heltal ger heltal
    ge x minus y

sätt resultat till add med 10, 3
skriv resultat
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "7")

    def test_named_args_multiple_updates_kopia_av(self):
        """Test that kopia av supports multiple named argument updates."""
        source = """\

typ person
    namn som sträng
    ålder som heltal
sätt p till person med David, 37
sätt uppdaterad till kopia av p med ålder 40, namn Eva
skriv namn från uppdaterad
skriv ny rad
skriv ålder från uppdaterad
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue(), "Eva\n40")

    def test_named_args_multiword_property_value(self):
        """Test named args with multi-word property names."""
        source = """\

typ bil
    märke som sträng
    modell som sträng
sätt min bil till bil med modell V60, märke Volvo
skriv märke från min bil
skriv ny rad
skriv modell från min bil
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue(), "Volvo\nV60")

    def test_tokeniserare_tokenisera_with_indentation(self):
        """Verify that tokenisera correctly handles indentation tokens."""
        source = """\

använd tokeniserare

sätt rader till lista med "sätt x till 1", "  skriv x", "skriv x"

sätt tokens till tokenisera med rader

sätt indent_count till 0

för varje t i tokens
    om tokentyp från t är lika med 38
        sätt indent_count till indent_count plus 1
    om tokentyp från t är lika med 39
        sätt indent_count till indent_count minus 1

skriv indent_count
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "0")

    def test_delstrang_function_call(self):
        """Verify that delsträng can be defined and called with text, start, length."""
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
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "ejs")

    def test_infix_funktion_innehåller(self):
        """Verify that infix functions work correctly with the 'innehåller' function from listor."""
        source = """\

använd listor

sätt frukter till lista med äpple, banan, citron

. Test infix function syntax: lista innehåller värde
om frukter innehåller banan
    skriv Ja

om frukter innehåller druva
    skriv Nej

. Test that the function returns correct boolean values
sätt finns banan till frukter innehåller banan
sätt finns druva till frukter innehåller druva

skriv finns banan
skriv finns druva
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "JaSANTFALSKT")

    def test_infix_funktion_custom_definition(self):
        """Verify that custom infix functions can be defined and used."""
        source = """\

. Define a custom infix function 'är del av'
sätt är del av till infixgrej med del som heltal, helhet som lista av heltal ger boolesk
    sätt x till 0
    medan x är mindre än längd från helhet
        om element x från helhet är lika med del
            ge SANT
        sätt x till x plus 1
    ge FALSKT

sätt färger till lista med röd, grön, blå

. Use the infix function syntax
om grön är del av färger
    skriv Hittat

om gul är del av färger
    skriv Saknas

sätt resultat till blå är del av färger 
skriv resultat
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "HittatSANT")

    def test_element_assign_int_index(self):
        """Verify that element assignment with integer index works correctly."""
        source = """\

sätt saker till lista med 10, 20, 30

sätt element 0 i saker till 100
skriv element 0 från saker
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "100")

    def test_element_assign_variable_index(self):
        """Verify that element assignment with variable index works correctly."""
        source = """\

sätt saker till lista med 10, 20, 30

sätt idx till 1
sätt element idx i saker till 200
skriv element 1 från saker
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "200")

    def test_element_assign_in_function(self):
        """Verify that element assignment works inside a function."""
        source = """\

sätt uppdatera till grej med lst som lista av heltal, idx som heltal, värde som heltal ger lista av heltal
    sätt element idx i lst till värde
    ge element idx från lst

sätt saker till lista med 10, 20

sätt resultat till uppdatera med saker, 0, 99
skriv resultat
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "99")

    def test_increment_decrement_operations(self):
        """Verify that increment and decrement statements work correctly at runtime."""
        source = """\

sätt x till 10
öka x med 5
skriv x
skriv ny rad
minska x med 3
skriv x
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "15\n12")

    def test_increment_string_concatenation(self):
        """Verify that increment works as string concatenation for string values."""
        source = """\

sätt ord till hej
öka ord med då
skriv ord
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "hejdå")

    def test_increment_decrement_errors(self):
        """Verify that incrementing or decrementing undefined variables or invalid types raises errors."""
        source1 = "öka okänd med 5"
        with self.assertRaises(Exception) as context:
            self.run_source(source1)
        self.assertIn("inte definierad", str(context.exception))
        source2 = '\nsätt mintext till hej\nminska mintext med då\n'
        with self.assertRaises(Exception) as context:
            self.run_source(source2)
        self.assertIn("Kan inte minska", str(context.exception))

    def test_multiply_divide_assign_operations(self):
        """Verify that multiply/divide assign statements work correctly at runtime."""
        source1 = '\nsätt x till 10\ngångra x med 3\nskriv x\nskriv ny rad\nmultiplicera x med 2\nskriv x\n'
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source1)
            self.assertEqual(fake_out.getvalue().strip(), "30\n60")
        source2 = '\nsätt y till 100\ndela y med 4\nskriv y\nskriv ny rad\ndividera y med 5\nskriv y\n'
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source2)
            self.assertEqual(fake_out.getvalue().strip(), "25.0\n5.0")

    def test_multiply_string_replication(self):
        """Verify that multiplying a string by an integer replicates the string."""
        source = """\

sätt ord till ja
gångra ord med 3
skriv ord
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "jajaja")

    def test_multiply_divide_errors(self):
        """Verify that errors are raised for invalid types, undefined variables, or division by zero."""
        source1 = '\nsätt x till 10\ndela x med 0\n'
        with self.assertRaises(Exception) as context:
            self.run_source(source1)
        self.assertIn("Division med nolla", str(context.exception))
        source2 = '\nsätt ord till hej\ndela ord med 2\n'
        with self.assertRaises(Exception) as context:
            self.run_source(source2)
        self.assertIn("Kan inte dividera", str(context.exception))
        source3 = "gångra okänd med 2"
        with self.assertRaises(Exception) as context:
            self.run_source(source3)
        self.assertIn("inte definierad", str(context.exception))

    def test_modulo_operations(self):
        """Verify that modulo expressions are evaluated correctly."""
        source = """\

sätt x till 10
sätt y till resten av x delat med 3
sätt z till resten av x delat på 4
skriv y
skriv " "
skriv z
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip().split(), ["1", "2"])
        source_err1 = '\nsätt x till 10\nsätt y till resten av x delat med 0\n'
        with self.assertRaises(Exception) as context:
            self.run_source(source_err1)
        self.assertIn("Division med nolla", str(context.exception))
        source_err2 = '\nsätt ord till hej\nsätt y till resten av ord delat med 2\n'
        with self.assertRaises(Exception) as context:
            self.run_source(source_err2)
        self.assertIn("Kan inte utföra modulo", str(context.exception))

    def test_arg_name_matches_param_name_still_positional(self):
        """When a variable name matches a function param name, args stay positional.

        Regression test: the resolver's named-arg detection must not treat
        'my_func med tokens, 1' as a named arg just because 'tokens' matches
        the parameter name 'tokens'.
        """
        source = """\

sätt my_func till grej med tokens som lista av heltal, pos som heltal ger lista av heltal
    ge element pos från tokens

sätt tokens till lista med a, b, c
sätt resultat till my_func med tokens, 1
skriv resultat
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "b")

    def test_verb_grej_user_defined(self):
        """User-defined verbgrej function works at runtime."""
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
skriv a
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "hejhejhej")

    def test_skicka_grej_user_defined(self):
        """User-defined skickagrej function works at runtime."""
        source = """\

sätt skicka till skickagrej med sak som sträng, mål som lista av sträng ger lista av sträng
    lägg till sak i mål
    ge mål

sätt min lista till lista av sträng
skicka hej till min lista
skicka då till min lista
skriv element 0 från min lista
skriv element 1 från min lista
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "hejdå")

    def test_hämta_grej_user_defined(self):
        """User-defined hämtagrej function works at runtime."""
        source = """\

sätt plocka till hämtagrej med namn som sträng, källa som lista av sträng ger sträng
    ge element 0 från källa

sätt frukter till lista av sträng med äpple, banan, citron
sätt resultat till plocka banan från frukter
skriv resultat
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "äpple")

    def test_typ_av_heltal(self):
        """typ av 42 returns hiuhtyp with namn 'heltal'."""
        source = """\

sätt ht till typ av 42
skriv namn från ht
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "heltal")

    def test_typ_av_sträng(self):
        """typ av returns hiuhtyp with namn 'sträng' for strings."""
        source = """\

sätt ht till typ av "hej"
skriv namn från ht
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "sträng")

    def test_typ_av_flyttal(self):
        source = """\

sätt ht till typ av 3,14
skriv namn från ht
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "flyttal")

    def test_typ_av_boolesk(self):
        source = """\

sätt ht till typ av SANT
skriv namn från ht
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "boolesk")

    def test_typ_av_comparison_equal(self):
        """typ av 42 är lika med heltal."""
        source = """\

sätt x till 42
om typ av x är lika med heltal
    skriv "ja"
annars
    skriv "nej"
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "ja")

    def test_typ_av_comparison_not_equal(self):
        """typ av sträng är inte lika med heltal."""
        source = """\

sätt x till "hej"
om typ av x är inte lika med heltal
    skriv "inte heltal"
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "inte heltal")

    def test_typ_av_user_defined_type(self):
        """typ av for user-defined typ returns correct hiuhtyp."""
        source = """\

typ person
    namn som sträng
    ålder som heltal

sätt p till person med David, 37
sätt ht till typ av p
skriv namn från ht
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "person")

    def test_typ_av_same_type_equal(self):
        """Two instances of same type have equal typ av."""
        source = """\

typ person
    namn som sträng
    ålder som heltal

sätt p1 till person med David, 37
sätt p2 till person med Eva, 25
om typ av p1 är lika med typ av p2
    skriv "samma"
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "samma")

    def test_typ_av_inheritance_parents(self):
        """typ av includes parent types in föräldrar."""
        source = """\

typ fordon
    hastighet som heltal

typ bil ärver fordon
    märke som sträng

sätt b till bil med 120, Volvo
sätt ht till typ av b
sätt fl till föräldrar från ht
skriv längd från fl
om längd från fl är större än 0
    sätt förälder till element 0 från fl
    skriv " "
    skriv namn från förälder
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "1 fordon")

    def test_texter_trimma_text(self):
        """typ av includes parent types in föräldrar."""
        source = """\

använd texter
skriv start
sätt x till "    hejsan    "
skriv trimma med x
skriv slut
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue(), "starthejsanslut")
if __name__ == '__main__':
    unittest.main()