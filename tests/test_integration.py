import os
import unittest
from io import StringIO
from unittest.mock import patch

from hiuh.backend.interpreter.interpreter import Interpreter
from hiuh.frontend.parser import Parser
from hiuh.frontend.resolver import Resolver
from hiuh.frontend.tokenizer import Tokenizer


class TestHiuhFullIntegration(unittest.TestCase):
    def setUp(self):
        self.tokenizer = Tokenizer()
        self.interpreter = Interpreter()

    def run_source(self, source, script_dir=None):
        tokens = self.tokenizer.tokenize(source)
        parser = Parser(tokens)
        nodes = parser.parse()
        
        # Use Resolver to resolve imports (marks ImportNode.resolved = True)
        resolver = Resolver()
        resolver.discover_modules_from_ast("main", nodes, script_dir)
        resolver.discover_imports("main")  # Load imported modules
        resolver.resolve_all()
        nodes = resolver.get_ast("main")

        # Pass module registry and script directory to interpreter
        if script_dir:
            self.interpreter.script_dir_stack = [script_dir]
        self.interpreter.module_registry = resolver.get_module_registry()
        
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
sätt min bil till bil
sätt märke i min bil till Volvo
sätt modell i min bil till V60
sätt år i min bil till 2024

skriv märke från min bil
skriv ny rad
skriv år från min bil
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
        source = "sätt x till 100 som text\nskriv x plus mellanrum plus är ett stort tal"
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.run_source(source)
            # Should join with space: "100 är ett stort tal"
            self.assertEqual(fake_out.getvalue().strip(), "100 är ett stort tal")

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

    def test_list_membership_i(self):
        """Verify 'val i lista' as a boolean check."""
        source = """
sätt färger till lista med röd, grön
om röd i färger
    skriv Japp
om blå i färger
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
            # Explicitly seed the base script folder context path so the
            # interpreter's 'använd listor' locator knows exactly where to look
            import os
            # Use the project root (parent of tests directory)
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            hiuh_folder = os.path.join(repo_root, "hiuh_i_hiuh")

            self.run_source(source, script_dir=hiuh_folder)

            # Index of 'Hiuh' in [Java, Python, Hiuh, Kotlin] is 2
            # Expected exact console dump: "2 Hiuh"
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

sätt fruktpar till värden i fruktantal

sätt fruktfunk till grej med par
    sätt fruktnamn till nyckel i par
    sätt fruktantal till värde i par
    skriv fruktnamn plus mellanrum plus fruktantal

för varje med fruktpar, fruktfunk

"""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            import os
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            hiuh_folder = os.path.join(repo_root, "hiuh_i_hiuh")

            self.run_source(source, script_dir=hiuh_folder)

            self.assertEqual(fake_out.getvalue().strip(), "äpple 2\ncitron 3")

if __name__ == '__main__':
    unittest.main()
