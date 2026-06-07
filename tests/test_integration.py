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

        # Use Resolver to resolve imports (marks ImportNode.resolved = True)
        resolver = Resolver(self.module_registry, self.hiuh_folder, script_dir)
        resolver.discover_modules_from_ast("main", nodes, script_dir)
        resolver.discover_imports("main")  # Load imported modules
        resolver.resolve_all()
        nodes = resolver.get_ast("main")

        # Pass module registry and script directory to interpreter
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
        source = "sätt x till detta är en hemlighet\nskriv x"
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "detta är en hemlighet")

    def test_if_else_logic(self):
        """Tests control flow logic with Swedish comparison operators."""
        source = """
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
        source = """
sätt hälsa till grej med namn
    ge hej plus mellanrum plus namn

sätt meddelande till hälsa med Hiuh
skriv meddelande
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "hej Hiuh")

    def test_try_catch_blocks(self):
        """Tests the Swedish error handling keywords."""
        source = """
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
        source = "skriv rad1\nskriv ny rad\nskriv rad2"
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            # Standard print adds \n, and ny rad adds another \n
            self.assertEqual(fake_out.getvalue(), "rad1\nrad2")

    def test_custom_type_bil(self):
        """Tests dynamic type definition and field access for a 'bil' type."""
        source = """
typ bil med märke, modell, år
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
        # The Hiuh source code
        source = """
sätt svar till inmatning
skriv Hej plus mellanrum plus svar
"""
        # Mocking BOTH stdin (for input) and stdout (to verify the result)
        with patch('sys.stdin', StringIO("Daverix\n")):
            with patch('sys.stdout', new=StringIO()) as fake_out:
                self.run_source(source)
                # Output should be "Hej Daverix"
                self.assertEqual(fake_out.getvalue().strip(), "Hej Daverix")

    def test_multiple_concatenation(self):
        """Tests joining three parts together."""
        source = "skriv ett plus mellanrum plus två plus mellanrum plus tre"
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            # Should result in "ett två tre"
            # (Assuming 'ett', 'två', 'tre' fall back to strings)
            self.assertEqual(fake_out.getvalue().strip(), "ett två tre")

    def test_list_set_and_get(self):
        source = """
sätt min_lista till lista med röd, grön
sätt element 0 i min_lista till blå
skriv element 0 från min_lista
skriv element 1 från min_lista
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            # Should result in "blå"
            self.assertEqual(fake_out.getvalue().strip(), "blågrön")

    def test_list_length(self):
        """Verify 'längd från [lista]' syntax."""
        source = """
sätt frukter till lista med äpple, banan
skriv längd från frukter
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            # Output should be 2
            self.assertEqual(fake_out.getvalue().strip(), "2")

    def test_casting_som_tal(self):
        """Tests that strings can be converted to numbers for math."""
        # '10' is an unknown variable, so it's a StringNode via fallback
        source = "sätt x till 10 som tal\nskriv x plus 5"
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "15")

    def test_casting_som_text(self):
        """Tests converting a number back to text."""
        source = "sätt x till 100 som text\nsätt y till 2 som text\nskriv x plus y plus mellanrum plus är ett stort tal"
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            # Should join with space: "100 är ett stort tal"
            self.assertEqual(fake_out.getvalue().strip(), "1002 är ett stort tal")

    def test_list_append_lägg_till(self):
        """Verify adding items to a list using 'lägg till'."""
        source = """
sätt frukter till lista med äpple
lägg till banan i frukter
skriv element 1 från frukter
skriv mellanrum
skriv element 0 från frukter
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            # Result should be "banan äpple"
            # (Note: index 1 is banan because we appended it)
            self.assertEqual(fake_out.getvalue().strip(), "banan äpple")

    def test_list_removal_mixed(self):
        """Verify removal by value AND by index."""
        source = """
sätt frukter till lista med äpple, banan, citron
ta bort banan från frukter
ta bort element 1 från frukter
skriv element 0 från frukter
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            # 1. Start: [äpple, banan, citron]
            # 2. 'ta bort banan': [äpple, citron]
            # 3. 'ta bort element 1' (citron): [äpple]
            # 4. Result: 'äpple'
            self.assertEqual(fake_out.getvalue().strip(), "äpple")

    def test_list_membership_contains(self):
        """Verify 'lista innehåller värde' as a boolean check."""
        source = """
använd listor

sätt färger till lista med röd, grön
om färger innehåller röd
    skriv Japp
om färger innehåller blå
    skriv Nej
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            # Should only print "Japp"
            self.assertEqual(fake_out.getvalue().strip(), "Japp")

    def test_file_stream_operations(self):
        filename = "data.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write("Första raden\nAndra raden")

        try:
            # Note: data.txt is now a greedy string, no quotes needed
            source = """
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
            # First, we write one thing
            source_1 = """
öppna skrivtest.txt för skrivning som f
skriv Första texten till f
stäng f
"""
            self.run_source(source_1)

            # Then, we overwrite it with something else
            source_2 = """
öppna skrivtest.txt för skrivning som f
skriv Ny text till f
stäng f
öppna skrivtest.txt för läsning som f2
skriv nästa rad från f2
stäng f2
"""
            with patch('sys.stdout', new=StringIO()) as fake_out:
                self.run_source(source_2)
                # Output should only be the NEW text
                self.assertEqual(fake_out.getvalue().strip(), "Ny text")
        finally:
            if os.path.exists(filename):
                os.remove(filename)

    def test_try_catch_finally(self):
        source = """
försök
    kasta Ojdå
fånga fel
    skriv fel
slutligen
    skriv mellanrum plus och hejdå
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            # Output: "Ojdå och hejdå"
            self.assertEqual(fake_out.getvalue().strip(), "Ojdå och hejdå")

    def test_try_finally(self):
        source = """
försök
    skriv hej
slutligen
    skriv mellanrum plus och hejdå
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            # Output: "Ojdå och hejdå"
            self.assertEqual(fake_out.getvalue().strip(), "hej och hejdå")

    def test_for_each_loop(self):
        """Verify that for-each loops iterate correctly with multi-word variable."""
        source = """
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

        # Create a helper module that exposes a function
        with open(module_filename, "w", encoding="utf-8") as f:
            f.write("""
sätt hälsa till grej med namn
    ge Hej plus mellanrum plus namn
        """)

        try:
            # We import the helper module using an alias ('som h')
            # and access its property using our standard property access parser rule ('från')
            source = """
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
        module_filename = "verktyg.hiuh"

        # Create a module that exposes multiple variables
        with open(module_filename, "w", encoding="utf-8") as f:
            f.write("""
sätt meddelande till Hej fràn Hiuh
sätt faktor till 10
sätt hälsa till grej med namn
    ge Hej plus mellanrum plus namn
""")

        try:
            # Wildcard import: all variables are available directly (no 'som')
            source = """
använd verktyg
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

        # Both modules expose 'namn'
        with open(module_a, "w", encoding="utf-8") as f:
            f.write("sätt namn till Alfa\n")
        with open(module_b, "w", encoding="utf-8") as f:
            f.write("sätt namn till Beta\n")

        try:
            source = """
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
            if os.path.exists(module_a): os.remove(module_a)
            if os.path.exists(module_b): os.remove(module_b)

    def test_module_directory_import(self):
        dir_name = "verktyg"
        module_filename = os.path.join(dir_name, "matematik.hiuh")

        # Create the subdirectory and the file
        os.makedirs(dir_name, exist_ok=True)
        with open(module_filename, "w", encoding="utf-8") as f:
            f.write("""
sätt addera till grej med a, b
    ge a plus b
        """)

        try:
            # We import from a directory via dot separation and use the default name 'matematik'
            source = """
använd verktyg.matematik
sätt summa till addera med 10, 5
skriv summa
            """
            with patch('sys.stdout', new=StringIO()) as fake_out:
                self.run_source(source)
                self.assertEqual(fake_out.getvalue().strip(), "15")
        finally:
            # Clean up both file and folder
            if os.path.exists(module_filename):
                os.remove(module_filename)
            if os.path.exists(dir_name):
                os.rmdir(dir_name)

    def test_bootstrapping_sanity_step(self):
        """Verify Hiuh can read a file line-by-line and simulate a basic tokenizer loop."""
        target_file = "källkod_test.hiuh"

        # 1. Create a mock source file that our Hiuh code will read
        with open(target_file, "w", encoding="utf-8") as f:
            f.write("sätt x till 10\nskriv x\n")

        try:
            # 2. The Hiuh source script that performs line-by-line inspection
            source = """
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
                # Line 1 starts with 's' (sätt), Line 2 starts with 's' (skriv)
                # Output should be "1.s 2.s "
                self.assertEqual(fake_out.getvalue(), "1.s 2.s ")
        finally:
            # 3. Securely clean up the file
            if os.path.exists(target_file):
                os.remove(target_file)

    def test_file_paths_with_and_without_spaces(self):
        """Verify that standard files are quote-less, but files with spaces use quotes."""
        file_simple = "källkod_test.hiuh"
        file_spaced = "mitt projekt.hiuh"

        with open(file_simple, "w", encoding="utf-8") as f: f.write("sätt x till 1")
        with open(file_spaced, "w", encoding="utf-8") as f: f.write("sätt y till 2")

        try:
            source = """
öppna källkod_test.hiuh för läsning som f1
öppna "mitt projekt.hiuh" för läsning som f2
stäng f1
stäng f2
"""
            # If it compiles and runs without an exception, the syntax layout is correct
            self.run_source(source)
        finally:
            if os.path.exists(file_simple): os.remove(file_simple)
            if os.path.exists(file_spaced): os.remove(file_spaced)

    def test_ascii_character_casting_symmetry(self):
        """Verify that string characters can be evaluated as ASCII integers and vice versa."""
        source = """
. Skapa en textsträng som innehåller citattecken, mellanslag och kommatecken
. I källkoden kan vi skriva ' och " eftersom de är tillåtna som filnamns-escapes,
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

            # --- EXPECTED RUNTIME METRICS ---
            # ASCII Code for 'A' is 65
            # ASCII Code for ',' is 44
            # 32 som tecken injects a space ' '
            # 34 som tecken injects a double quote '"'
            # Expected final console print layout: '65 44 "Hej Världen"'

            expected_output = '65 44 "Hej Världen"'
            self.assertEqual(fake_out.getvalue().strip(), expected_output)

    def test_listor_utility_callbacks(self):
        """Verify that listor.hiuh can be imported and executed with high-order callback functions."""
        # 1. Ensure listor.hiuh exists in the repository search paths or a module directory
        # For this test, we assume 'listor.hiuh' is located directly in your active project root folder
        source = """
använd listor

. 1. Create a callback utility function to search for a specific name target
sätt matchar_hiuh till grej med text_stycke
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

    def test_ordlista_utility_callbacks(self):
        """Verify that ordlista.hiuh can be imported and executed with high-order callback functions."""
        source = """
använd ordlista
använd listor

sätt fruktantal till ny tom ordlista
putta från fruktantal med äpple, 2
putta från fruktantal med banan, 1
putta från fruktantal med citron, 3

rensa från fruktantal med banan

sätt fruktpar till värden från fruktantal

för varje par i fruktpar
    sätt fruktnamn till nyckel från par
    sätt fruktantal till värde från par
    skriv fruktnamn plus mellanrum plus fruktantal plus . plus mellanrum

"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)

            self.assertEqual(fake_out.getvalue().strip(), "äpple 2. citron 3.")

    def test_named_args_typ_constructor(self):
        """Test that typ constructors support named arguments in any order."""
        source = """
typ person med namn, ålder
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
        source = """
typ person med namn, ålder
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
        source = """
typ person med namn, ålder
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
        source = """
sätt add till grej med a, b
    ge a plus b

sätt resultat till add med a 5, b 3
skriv resultat
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "8")

    def test_named_args_grej_positional_still_works(self):
        """Test that grej functions still support positional arguments."""
        source = """
sätt add till grej med x, y
    ge x minus y

sätt resultat till add med 10, 3
skriv resultat
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "7")

    def test_named_args_multiple_updates_kopia_av(self):
        """Test that kopia av supports multiple named argument updates."""
        source = """
typ person med namn, ålder
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
        source = """
typ bil med märke, modell
sätt min bil till bil med modell V60, märke Volvo
skriv märke från min bil
skriv ny rad
skriv modell från min bil
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue(), "Volvo\nV60")

    def test_tokeniserare_tokenisera(self):
        """Verify that tokeniserare.hiuh can be imported and tokenisera returns correct tokens."""
        source = """
använd tokeniserare

sätt rader till lista med "sätt x till 42", "skriv x"

sätt tokens till tokenisera med rader

för varje t i tokens
    skriv rad från t plus ":" plus tokentyp från t plus ":" plus värde från t

"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            output = fake_out.getvalue().strip()
            
            # Token types (from tokeniserare.hiuh):
            # TOKEN SET = 2, TOKEN TO = 3, TOKEN PRINT = 1
            # TOKEN IDENTIFIER = 36, TOKEN LITERAL INT = 31, TOKEN NEWLINE = 37
            # Verify we have tokens from both lines
            self.assertIn("1:skriv", output)  # PRINT token for "skriv"
            self.assertIn("2:skriv", output)  # PRINT token on line 2
            self.assertIn("2:x", output)     # IDENTIFIER "x" on line 2
            self.assertIn("31:42", output)    # LITERAL INT for "42"

    def test_tokeniserare_tokenisera_with_indentation(self):
        """Verify that tokenisera correctly handles indentation tokens."""
        source = """
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
            # After processing, indent_count should be 0 (balanced)
            self.assertEqual(fake_out.getvalue().strip(), "0")

    def test_infix_funktion_innehåller(self):
        """Verify that infix functions work correctly with the 'innehåller' function from listor."""
        source = """
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
        source = """
. Define a custom infix function 'är del av'
sätt är del av till infix grej med del, helhet
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
        source = """
sätt saker till lista med 10, 20, 30

sätt element 0 i saker till 100
skriv element 0 från saker
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "100")

    def test_element_assign_variable_index(self):
        """Verify that element assignment with variable index works correctly."""
        source = """
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
        source = """
sätt uppdatera till grej med lst, idx, värde
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
        source = """
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
        source = """
sätt ord till hej
öka ord med då
skriv ord
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "hejdå")

    def test_increment_decrement_errors(self):
        """Verify that incrementing or decrementing undefined variables or invalid types raises errors."""
        # Undefined variable
        source1 = "öka okänd med 5"
        with self.assertRaises(Exception) as context:
            self.run_source(source1)
        self.assertIn("inte definierad", str(context.exception))

        # Decrement non-numeric
        source2 = """
sätt mintext till hej
minska mintext med då
"""
        with self.assertRaises(Exception) as context:
            self.run_source(source2)
        self.assertIn("Kan inte minska", str(context.exception))

    def test_multiply_divide_assign_operations(self):
        """Verify that multiply/divide assign statements work correctly at runtime."""
        # Test multiplication (both keywords)
        source1 = """
sätt x till 10
gångra x med 3
skriv x
skriv ny rad
multiplicera x med 2
skriv x
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source1)
            self.assertEqual(fake_out.getvalue().strip(), "30\n60")

        # Test division (both keywords)
        source2 = """
sätt y till 100
dela y med 4
skriv y
skriv ny rad
dividera y med 5
skriv y
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source2)
            self.assertEqual(fake_out.getvalue().strip(), "25.0\n5.0")

    def test_multiply_string_replication(self):
        """Verify that multiplying a string by an integer replicates the string."""
        source = """
sätt ord till ja
gångra ord med 3
skriv ord
"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            self.assertEqual(fake_out.getvalue().strip(), "jajaja")

    def test_multiply_divide_errors(self):
        """Verify that errors are raised for invalid types, undefined variables, or division by zero."""
        # Division by zero
        source1 = """
sätt x till 10
dela x med 0
"""
        with self.assertRaises(Exception) as context:
            self.run_source(source1)
        self.assertIn("Division med nolla", str(context.exception))

        # Non-numeric division
        source2 = """
sätt ord till hej
dela ord med 2
"""
        with self.assertRaises(Exception) as context:
            self.run_source(source2)
        self.assertIn("Kan inte dividera", str(context.exception))

        # Undefined variable multiplication
        source3 = "gångra okänd med 2"
        with self.assertRaises(Exception) as context:
            self.run_source(source3)
        self.assertIn("inte definierad", str(context.exception))

    def test_modulo_operations(self):
        """Verify that modulo expressions are evaluated correctly."""
        # Standard positive integer modulo
        source = """
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

        # Modulo by zero error
        source_err1 = """
sätt x till 10
sätt y till resten av x delat med 0
"""
        with self.assertRaises(Exception) as context:
            self.run_source(source_err1)
        self.assertIn("Division med nolla", str(context.exception))

        # Modulo non-numeric error
        source_err2 = """
sätt ord till hej
sätt y till resten av ord delat med 2
"""
        with self.assertRaises(Exception) as context:
            self.run_source(source_err2)
        self.assertIn("Kan inte utföra modulo", str(context.exception))


if __name__ == '__main__':
    unittest.main()
