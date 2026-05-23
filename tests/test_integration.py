import os
import unittest
from io import StringIO
from unittest.mock import patch
from hiuh.frontend.tokenizer import Tokenizer
from hiuh.frontend.parser import Parser
from hiuh.backend.interpreter.interpreter import Interpreter

class TestHiuhFullIntegration(unittest.TestCase):
    def setUp(self):
        self.tokenizer = Tokenizer()
        self.interpreter = Interpreter()

    def run_source(self, source):
        tokens = self.tokenizer.tokenize(source)
        parser = Parser(tokens)
        nodes = parser.parse()
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
    """
            with patch('sys.stdout', new=StringIO()) as fake_out:
                self.run_source(source)
                self.assertEqual(fake_out.getvalue().strip(), "Hej David")
        finally:
            if os.path.exists(module_filename):
                os.remove(module_filename)

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
sätt summa till addera från matematik med 10, 5
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

if __name__ == '__main__':
    unittest.main()
