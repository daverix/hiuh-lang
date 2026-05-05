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
prova
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

if __name__ == '__main__':
    unittest.main()
