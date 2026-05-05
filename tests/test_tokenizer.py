# -*- coding: utf-8 -*-
import unittest
from hiuh.frontend.tokenizer import Tokenizer, Token

class TestHiuhReadmeSpecification(unittest.TestCase):
    def setUp(self):
        self.tokenizer = Tokenizer()

    def test_stdout_section(self):
        source = "skriv hejsan\nskriv ny rad\nskriv hoppsan"
        expected = [
            Token("T_KEYWORD_PRINT", "skriv", 1, 1),
            Token("T_IDENTIFIER", "hejsan", 1, 7),
            Token("T_NEWLINE", "\n", 1, 13),
            Token("T_KEYWORD_PRINT", "skriv", 2, 1),
            Token("T_IDENTIFIER", "ny", 2, 7),
            Token("T_IDENTIFIER", "rad", 2, 10),
            Token("T_NEWLINE", "\n", 2, 13),
            Token("T_KEYWORD_PRINT", "skriv", 3, 1),
            Token("T_IDENTIFIER", "hoppsan", 3, 7)
        ]
        self.assertEqual(self.tokenizer.tokenize(source), expected)

    def test_variables_boolean_section(self):
        source = "sätt x till SANT\nsätt b till a större än 2"
        expected = [
            Token("T_KEYWORD_SET", "sätt", 1, 1),
            Token("T_IDENTIFIER", "x", 1, 6),
            Token("T_KEYWORD_TO", "till", 1, 8),
            Token("T_LITERAL_TRUE", "SANT", 1, 13),
            Token("T_NEWLINE", "\n", 1, 17),
            Token("T_KEYWORD_SET", "sätt", 2, 1),
            Token("T_IDENTIFIER", "b", 2, 6),
            Token("T_KEYWORD_TO", "till", 2, 8),
            Token("T_IDENTIFIER", "a", 2, 13),
            Token("T_KEYWORD_GREATER", "större", 2, 15),
            Token("T_KEYWORD_THAN", "än", 2, 22),
            Token("T_LITERAL_INT", "2", 2, 25)
        ]
        self.assertEqual(self.tokenizer.tokenize(source), expected)

    def test_variables_math_section(self):
        source = "sätt c till b gånger b plus a"
        expected = [
            Token("T_KEYWORD_SET", "sätt", 1, 1),
            Token("T_IDENTIFIER", "c", 1, 6),
            Token("T_KEYWORD_TO", "till", 1, 8),
            Token("T_IDENTIFIER", "b", 1, 13),
            Token("T_OP_MUL", "gånger", 1, 15),
            Token("T_IDENTIFIER", "b", 1, 22),
            Token("T_OP_ADD", "plus", 1, 24),
            Token("T_IDENTIFIER", "a", 1, 29)
        ]
        self.assertEqual(self.tokenizer.tokenize(source), expected)

    def test_variables_float_section(self):
        source = "sätt y till 3,4"
        expected = [
            Token("T_KEYWORD_SET", "sätt", 1, 1),
            Token("T_IDENTIFIER", "y", 1, 6),
            Token("T_KEYWORD_TO", "till", 1, 8),
            Token("T_LITERAL_FLOAT", "3,4", 1, 13)
        ]
        self.assertEqual(self.tokenizer.tokenize(source), expected)

    def test_variables_list_section(self):
        source = "sätt min lista till lista med 1, 2, 3"
        expected = [
            Token("T_KEYWORD_SET", "sätt", 1, 1),
            Token("T_IDENTIFIER", "min", 1, 6),
            Token("T_IDENTIFIER", "lista", 1, 10),
            Token("T_KEYWORD_TO", "till", 1, 16),
            Token("T_IDENTIFIER", "lista", 1, 21),
            Token("T_KEYWORD_WITH", "med", 1, 27),
            Token("T_LITERAL_INT", "1", 1, 31),
            Token("T_COMMA", ",", 1, 32),
            Token("T_LITERAL_INT", "2", 1, 34),
            Token("T_COMMA", ",", 1, 35),
            Token("T_LITERAL_INT", "3", 1, 37)
        ]
        self.assertEqual(self.tokenizer.tokenize(source), expected)

    def test_function_section(self):
        source = "sätt f till grej med a\n    ge a"
        expected = [
            Token("T_KEYWORD_SET", "sätt", 1, 1),
            Token("T_IDENTIFIER", "f", 1, 6),
            Token("T_KEYWORD_TO", "till", 1, 8),
            Token("T_KEYWORD_FUNC", "grej", 1, 13),
            Token("T_KEYWORD_WITH", "med", 1, 18),
            Token("T_IDENTIFIER", "a", 1, 22),
            Token("T_NEWLINE", "\n", 1, 23),
            Token("T_INDENT", "    ", 2, 1),
            Token("T_KEYWORD_GIVE", "ge", 2, 5),
            Token("T_IDENTIFIER", "a", 2, 8),
            Token("T_DEDENT", "", 3, 1)
        ]
        self.assertEqual(self.tokenizer.tokenize(source), expected)

    def test_typ_section(self):
        source = "typ person med namn, ålder\nsätt ålder i person till 38"
        expected = [
            Token("T_KEYWORD_TYPE", "typ", 1, 1),
            Token("T_IDENTIFIER", "person", 1, 5),
            Token("T_KEYWORD_WITH", "med", 1, 12),
            Token("T_IDENTIFIER", "namn", 1, 16),
            Token("T_COMMA", ",", 1, 20),
            Token("T_IDENTIFIER", "ålder", 1, 22),
            Token("T_NEWLINE", "\n", 1, 27),
            Token("T_KEYWORD_SET", "sätt", 2, 1),
            Token("T_IDENTIFIER", "ålder", 2, 6),
            Token("T_KEYWORD_IN", "i", 2, 12),
            Token("T_IDENTIFIER", "person", 2, 14),
            Token("T_KEYWORD_TO", "till", 2, 21),
            Token("T_LITERAL_INT", "38", 2, 26)
        ]
        self.assertEqual(self.tokenizer.tokenize(source), expected)

    def test_if_statement_section(self):
        source = "om x är större än 2\n    skriv större\nannars\n    skriv mindre"
        expected = [
            Token("T_KEYWORD_IF", "om", 1, 1),
            Token("T_IDENTIFIER", "x", 1, 4),
            Token("T_OP_IS", "är", 1, 6),
            Token("T_KEYWORD_GREATER", "större", 1, 9),
            Token("T_KEYWORD_THAN", "än", 1, 16),
            Token("T_LITERAL_INT", "2", 1, 19),
            Token("T_NEWLINE", "\n", 1, 20),
            Token("T_INDENT", "    ", 2, 1),
            Token("T_KEYWORD_PRINT", "skriv", 2, 5),
            Token("T_KEYWORD_GREATER", "större", 2, 11),
            Token("T_NEWLINE", "\n", 2, 17),
            Token("T_DEDENT", "", 3, 1),
            Token("T_KEYWORD_ELSE", "annars", 3, 1),
            Token("T_NEWLINE", "\n", 3, 7),
            Token("T_INDENT", "    ", 4, 1),
            Token("T_KEYWORD_PRINT", "skriv", 4, 5),
            Token("T_KEYWORD_LESS", "mindre", 4, 11),
            Token("T_DEDENT", "", 5, 1)
        ]
        self.assertEqual(self.tokenizer.tokenize(source), expected)

    def test_stdin_section(self):
        source = "sätt t till nästa rad från inmatning"
        expected = [
            Token("T_KEYWORD_SET", "sätt", 1, 1),
            Token("T_IDENTIFIER", "t", 1, 6),
            Token("T_KEYWORD_TO", "till", 1, 8),
            Token("T_IDENTIFIER", "nästa", 1, 13),
            Token("T_IDENTIFIER", "rad", 1, 19),
            Token("T_KEYWORD_FROM", "från", 1, 23),
            Token("T_IDENTIFIER", "inmatning", 1, 28)
        ]
        self.assertEqual(self.tokenizer.tokenize(source), expected)

    def test_error_handling_section(self):
        source = "prova\n    kasta fel\nfånga fel"
        expected = [
            Token("T_KEYWORD_TRY", "prova", 1, 1),
            Token("T_NEWLINE", "\n", 1, 6),
            Token("T_INDENT", "    ", 2, 1),
            Token("T_KEYWORD_THROW", "kasta", 2, 5),
            Token("T_IDENTIFIER", "fel", 2, 11),
            Token("T_NEWLINE", "\n", 2, 14),
            Token("T_DEDENT", "", 3, 1),
            Token("T_KEYWORD_CATCH", "fånga", 3, 1),
            Token("T_IDENTIFIER", "fel", 3, 7)
        ]
        self.assertEqual(self.tokenizer.tokenize(source), expected)

    def test_comments_section(self):
        source = ". skriver\nskriv hej"
        expected = [
            Token("T_COMMENT", ". skriver", 1, 1),
            Token("T_NEWLINE", "\n", 1, 10),
            Token("T_KEYWORD_PRINT", "skriv", 2, 1),
            Token("T_IDENTIFIER", "hej", 2, 7)
        ]
        self.assertEqual(self.tokenizer.tokenize(source), expected)

    def test_multiple_indents_nested(self):
        source = "om SANT\n    skriv nivå 1\n    om SANT\n        skriv nivå 2"
        expected = [
            Token("T_KEYWORD_IF", "om", 1, 1),
            Token("T_LITERAL_TRUE", "SANT", 1, 4),
            Token("T_NEWLINE", "\n", 1, 8),
            Token("T_INDENT", "    ", 2, 1),
            Token("T_KEYWORD_PRINT", "skriv", 2, 5),
            Token("T_IDENTIFIER", "nivå", 2, 11),
            Token("T_LITERAL_INT", "1", 2, 16),
            Token("T_NEWLINE", "\n", 2, 17),
            Token("T_KEYWORD_IF", "om", 3, 5),
            Token("T_LITERAL_TRUE", "SANT", 3, 8),
            Token("T_NEWLINE", "\n", 3, 12),
            Token("T_INDENT", "        ", 4, 1),
            Token("T_KEYWORD_PRINT", "skriv", 4, 9),
            Token("T_IDENTIFIER", "nivå", 4, 15),
            Token("T_LITERAL_INT", "2", 4, 20),
            Token("T_DEDENT", "", 5, 1),
            Token("T_DEDENT", "", 5, 1)
        ]
        self.assertEqual(self.tokenizer.tokenize(source), expected)

    def test_tokenize_from_keyword(self):
        """Verify that 'från' is tokenized correctly."""
        source = "skriv märke från min bil"
        tokens = self.tokenizer.tokenize(source)
        # Expected sequence: skriv, märke, från, min, bil
        # Check that 'från' is the 3rd token (index 2)
        self.assertEqual(tokens[2].type, "T_KEYWORD_FROM")
        self.assertEqual(tokens[2].value, "från")

    def test_tokenize_list_operations(self):
        """Verify tokens for setting and getting list elements."""
        source = (
            "sätt element 0 i minlista till röd\n"
            "skriv element 0 från minlista"
        )
        tokens = self.tokenizer.tokenize(source)

        # Expected types for the first line:
        # sätt (SET), element (ID), 0 (INT), i (IN), minlista (ID), till (TO), röd (ID)
        expected_types = [
            "T_KEYWORD_SET", "T_IDENTIFIER", "T_LITERAL_INT", "T_KEYWORD_IN",
            "T_IDENTIFIER", "T_KEYWORD_TO", "T_IDENTIFIER", "T_NEWLINE",
            "T_KEYWORD_PRINT", "T_IDENTIFIER", "T_LITERAL_INT", "T_KEYWORD_FROM",
            "T_IDENTIFIER"
        ]

        actual_types = [t.type for t in tokens if t.type not in ["T_EOF"]]
        self.assertEqual(actual_types, expected_types)

        # Specific Value Checks
        self.assertEqual(tokens[3].value, "i")
        self.assertEqual(tokens[11].value, "från")

if __name__ == '__main__':
    unittest.main()
