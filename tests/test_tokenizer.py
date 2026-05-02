import unittest
from hiuh.frontend.tokenizer import Tokenizer # Assuming Tokenizer is available here

class TestTokenizer(unittest.TestCase):
    """
    Tests covering various language constructs based on examples in README.md.
    """

    def test_simple_stdout(self):
        """Example: simple stdout command."""
        source_code = "skriv hejsan hoppsan"
        # In a real test, we would assert the tokens match what the tokenizer should produce.
        # For this example, we just ensure the tokenizer runs with the code.
        # print(Tokenizer().tokenize(source_code)) 
        pass # Placeholder test

    def test_newline_keyword(self):
        """Example: using 'ny rad' keyword."""
        source_code = """skriv hejsan
skriv ny rad
skriv hoppsan"""
        pass # Placeholder test

    def test_boolean_variables(self):
        """Example: setting and comparing boolean variables."""
        source_code = """sätt x till SANT
sätt y till x eller FALSKT

sätt a till 2
sätt b till a större än 2"""
        pass # Placeholder test

    def test_int_variables_simple(self):
        """Example: setting a simple integer variable."""
        source_code = """sätt x till 2
skriv 2"""
        pass # Placeholder test

    def test_int_variables_expression(self):
        """Example: setting variables using mathematical expressions."""
        source_code = """sätt a till 2
sätt b till a gånger 3
sätt c till b gånger b pluss a"""
        pass # Placeholder test

    def test_float_variable(self):
        """Example: setting a float variable."""
        source_code = "sätt y till 3,4"
        pass # Placeholder test

    def test_list_variable_empty(self):
        """Example: creating an empty list."""
        source_code = "sätt min lista till ny lista"
        pass # Placeholder test
        
    def test_list_variable_initialize(self):
        """Example: initializing a list with values."""
        source_code = "sätt min lista till lista med 1, 2, 3"
        pass # Placeholder test

    def test_function_variable(self):
        """Example: defining and calling a function variable."""
        source_code = """sätt min funktion till grej med param1, param2, param3
    ge param1 pluss param2 minus param3

sätt x till min funktion med 1, 2, 3

skriv x"""
        pass # Placeholder test

    def test_typed_variable(self):
        """Example: defining and accessing a custom type variable."""
        source_code = """typ person med namn, ålder

sätt p till person med David, 37

skriv Namn
skriv ny rad
skriv namn från p
skriv ny rad
skriv Ålder
skriv ålder från p"""
        pass # Placeholder test

    def test_string_literal(self):
        """Example: setting a string literal."""
        source_code = "sätt x till en lång fin text som innehåller skriv och kommer inte tolkas som keyword\n"
        pass # Placeholder test

    def test_if_statements(self):
        """Example: simple if/else block."""
        source_code = """sätt x till 3
om x är större än 2
    skriv större
annars
    skriv mindre eller lika med"""
        pass # Placeholder test

    def test_while_loops(self):
        """Example: while loop structure."""
        source_code = """sätt x till 0
medan x är mindre än 10
    skriv x pluss 1
    sätt x till x pluss 1"""
        pass # Placeholder test

    def test_stdin_handling(self):
        """Example: reading from stdin."""
        source_code = """sätt nummer som text till nästa rad från inmatning
sätt nummer till konvertera till nummer med nummer som text

om nummer är större än 10
    skriv stort nummer
annars
    skriv litet nummer"""
        pass # Placeholder test

    def test_reading_single_file(self):
        """Example: reading one line from a file."""
        source_code = """sätt input till inläsning från fil.txt
sätt rad1 till nästa rad från input
skriv rad1"""
        pass # Placeholder test

    def test_reading_multiple_files(self):
        """Example: reading multiple lines from a file."""
        source_code = """sätt data till inläsning från fil2.txt
sätt rader till ny lista

medan rad finns från data
    sätt nuvarande rad till nästa rad från data
    lägg till nuvarande rad i rader
    

skriv längd från rader"""
        pass # Placeholder test
    
    def test_error_handling(self):
        """Example: try/except block."""
        source_code = """prova
    skriv här testar vi något och det blev fel
    skriv ny rad
    kasta något fel här
fånga fel
    skriv det blev ett fel
    skriv ny rad
    skriv meddelande från fel"""
        pass # Placeholder test

    def test_scopes(self):
        """Example: variable scope demonstration."""
        source_code = """sätt x till 3
sätt y till grej med a
    sätt b till grej med c
        ge c gånger a

    ge b med x delat med a

skriv y med 4"""
        pass # Placeholder test

    def test_comments(self):
        """Example: handling comments."""
        source_code = ". skriver en text
skriv hej

. jämför något
om längd från hej är större än 2
    . skriver hoppsan för att längden är större än två
    skriv hoppsan"""
        pass # Placeholder test

    def test_packages_main_app(self):
        """Example: referencing files/packages."""
        source_code = """hämta bibliotek.exempel
hämta mattematik som matte

sätt s till slumpa från matte
skriv nästa tal från s
skriv ny rad
skriv min variabel från exempel"""
        pass # Placeholder test

if __name__ == '__main__':
    unittest.main()