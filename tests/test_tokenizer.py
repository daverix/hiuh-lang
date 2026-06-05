# -*- coding: utf-8 -*-
import unittest
from hiuh.frontend.tokenizer import Tokenizer, Token
from hiuh.frontend.tokenizer import (
    TOKEN_PRINT, TOKEN_SET, TOKEN_TO, TOKEN_FUNC, TOKEN_WITH, TOKEN_GIVE,
    TOKEN_TYPE, TOKEN_IN, TOKEN_FROM, TOKEN_IF, TOKEN_ELSE, TOKEN_TRY,
    TOKEN_THROW, TOKEN_CATCH, TOKEN_WHILE, TOKEN_IMPORT, TOKEN_OPEN,
    TOKEN_CLOSE, TOKEN_AS, TOKEN_GREATER, TOKEN_LESS, TOKEN_EQUAL,
    TOKEN_THAN, TOKEN_OR, TOKEN_AND, TOKEN_OP_ADD, TOKEN_OP_SUB,
    TOKEN_OP_MUL, TOKEN_OP_DIV, TOKEN_OP_IS, TOKEN_LITERAL_INT,
    TOKEN_LITERAL_FLOAT, TOKEN_LITERAL_TRUE, TOKEN_LITERAL_FALSE,
    TOKEN_STRING, TOKEN_IDENTIFIER, TOKEN_NEWLINE, TOKEN_INDENT,
    TOKEN_DEDENT, TOKEN_COMMA, TOKEN_INFIX
)

class TestHiuhReadmeSpecification(unittest.TestCase):
    def setUp(self):
        self.tokenizer = Tokenizer()

    def test_stdout_section(self):
        source = "skriv hejsan\nskriv ny rad\nskriv hoppsan"
        expected = [
            Token(TOKEN_PRINT, "skriv", 1, 1),
            Token(TOKEN_IDENTIFIER, "hejsan", 1, 7),
            Token(TOKEN_NEWLINE, "\n", 1, 13),
            Token(TOKEN_PRINT, "skriv", 2, 1),
            Token(TOKEN_IDENTIFIER, "ny", 2, 7),
            Token(TOKEN_IDENTIFIER, "rad", 2, 10),
            Token(TOKEN_NEWLINE, "\n", 2, 13),
            Token(TOKEN_PRINT, "skriv", 3, 1),
            Token(TOKEN_IDENTIFIER, "hoppsan", 3, 7)
        ]
        self.assertEqual(self.tokenizer.tokenize(source), expected)

    def test_variables_boolean_section(self):
        source = "sätt x till SANT\nsätt b till a större än 2"
        expected = [
            Token(TOKEN_SET, "sätt", 1, 1),
            Token(TOKEN_IDENTIFIER, "x", 1, 6),
            Token(TOKEN_TO, "till", 1, 8),
            Token(TOKEN_LITERAL_TRUE, "SANT", 1, 13),
            Token(TOKEN_NEWLINE, "\n", 1, 17),
            Token(TOKEN_SET, "sätt", 2, 1),
            Token(TOKEN_IDENTIFIER, "b", 2, 6),
            Token(TOKEN_TO, "till", 2, 8),
            Token(TOKEN_IDENTIFIER, "a", 2, 13),
            Token(TOKEN_GREATER, "större", 2, 15),
            Token(TOKEN_THAN, "än", 2, 22),
            Token(TOKEN_LITERAL_INT, "2", 2, 25)
        ]
        self.assertEqual(self.tokenizer.tokenize(source), expected)

    def test_variables_math_section(self):
        source = "sätt c till b gånger b plus a"
        expected = [
            Token(TOKEN_SET, "sätt", 1, 1),
            Token(TOKEN_IDENTIFIER, "c", 1, 6),
            Token(TOKEN_TO, "till", 1, 8),
            Token(TOKEN_IDENTIFIER, "b", 1, 13),
            Token(TOKEN_OP_MUL, "gånger", 1, 15),
            Token(TOKEN_IDENTIFIER, "b", 1, 22),
            Token(TOKEN_OP_ADD, "plus", 1, 24),
            Token(TOKEN_IDENTIFIER, "a", 1, 29)
        ]
        self.assertEqual(self.tokenizer.tokenize(source), expected)

    def test_variables_float_section(self):
        source = "sätt y till 3,4"
        expected = [
            Token(TOKEN_SET, "sätt", 1, 1),
            Token(TOKEN_IDENTIFIER, "y", 1, 6),
            Token(TOKEN_TO, "till", 1, 8),
            Token(TOKEN_LITERAL_FLOAT, "3,4", 1, 13)
        ]
        self.assertEqual(self.tokenizer.tokenize(source), expected)

    def test_variables_list_section(self):
        source = "sätt min lista till lista med 1, 2, 3"
        expected = [
            Token(TOKEN_SET, "sätt", 1, 1),
            Token(TOKEN_IDENTIFIER, "min", 1, 6),
            Token(TOKEN_IDENTIFIER, "lista", 1, 10),
            Token(TOKEN_TO, "till", 1, 16),
            Token(TOKEN_IDENTIFIER, "lista", 1, 21),
            Token(TOKEN_WITH, "med", 1, 27),
            Token(TOKEN_LITERAL_INT, "1", 1, 31),
            Token(TOKEN_COMMA, ",", 1, 32),
            Token(TOKEN_LITERAL_INT, "2", 1, 34),
            Token(TOKEN_COMMA, ",", 1, 35),
            Token(TOKEN_LITERAL_INT, "3", 1, 37)
        ]
        self.assertEqual(self.tokenizer.tokenize(source), expected)

    def test_function_section(self):
        source = "sätt f till grej med a\n    ge a"
        expected = [
            Token(TOKEN_SET, "sätt", 1, 1),
            Token(TOKEN_IDENTIFIER, "f", 1, 6),
            Token(TOKEN_TO, "till", 1, 8),
            Token(TOKEN_FUNC, "grej", 1, 13),
            Token(TOKEN_WITH, "med", 1, 18),
            Token(TOKEN_IDENTIFIER, "a", 1, 22),
            Token(TOKEN_NEWLINE, "\n", 1, 23),
            Token(TOKEN_INDENT, "    ", 2, 1),
            Token(TOKEN_GIVE, "ge", 2, 5),
            Token(TOKEN_IDENTIFIER, "a", 2, 8),
            Token(TOKEN_DEDENT, "", 3, 1)
        ]
        self.assertEqual(self.tokenizer.tokenize(source), expected)

    def test_typ_section(self):
        source = "typ person med namn, ålder\nsätt ålder i person till 38"
        expected = [
            Token(TOKEN_TYPE, "typ", 1, 1),
            Token(TOKEN_IDENTIFIER, "person", 1, 5),
            Token(TOKEN_WITH, "med", 1, 12),
            Token(TOKEN_IDENTIFIER, "namn", 1, 16),
            Token(TOKEN_COMMA, ",", 1, 20),
            Token(TOKEN_IDENTIFIER, "ålder", 1, 22),
            Token(TOKEN_NEWLINE, "\n", 1, 27),
            Token(TOKEN_SET, "sätt", 2, 1),
            Token(TOKEN_IDENTIFIER, "ålder", 2, 6),
            Token(TOKEN_IDENTIFIER, "i", 2, 12),
            Token(TOKEN_IDENTIFIER, "person", 2, 14),
            Token(TOKEN_TO, "till", 2, 21),
            Token(TOKEN_LITERAL_INT, "38", 2, 26)
        ]
        self.assertEqual(self.tokenizer.tokenize(source), expected)

    def test_if_statement_section(self):
        source = "om x är större än 2\n    skriv större\nannars\n    skriv mindre"
        expected = [
            Token(TOKEN_IF, "om", 1, 1),
            Token(TOKEN_IDENTIFIER, "x", 1, 4),
            Token(TOKEN_OP_IS, "är", 1, 6),
            Token(TOKEN_GREATER, "större", 1, 9),
            Token(TOKEN_THAN, "än", 1, 16),
            Token(TOKEN_LITERAL_INT, "2", 1, 19),
            Token(TOKEN_NEWLINE, "\n", 1, 20),
            Token(TOKEN_INDENT, "    ", 2, 1),
            Token(TOKEN_PRINT, "skriv", 2, 5),
            Token(TOKEN_GREATER, "större", 2, 11),
            Token(TOKEN_NEWLINE, "\n", 2, 17),
            Token(TOKEN_DEDENT, "", 3, 1),
            Token(TOKEN_ELSE, "annars", 3, 1),
            Token(TOKEN_NEWLINE, "\n", 3, 7),
            Token(TOKEN_INDENT, "    ", 4, 1),
            Token(TOKEN_PRINT, "skriv", 4, 5),
            Token(TOKEN_LESS, "mindre", 4, 11),
            Token(TOKEN_DEDENT, "", 5, 1)
        ]
        self.assertEqual(self.tokenizer.tokenize(source), expected)

    def test_stdin_section(self):
        source = "sätt t till nästa rad från inmatning"
        expected = [
            Token(TOKEN_SET, "sätt", 1, 1),
            Token(TOKEN_IDENTIFIER, "t", 1, 6),
            Token(TOKEN_TO, "till", 1, 8),
            Token(TOKEN_IDENTIFIER, "nästa", 1, 13),
            Token(TOKEN_IDENTIFIER, "rad", 1, 19),
            Token(TOKEN_FROM, "från", 1, 23),
            Token(TOKEN_IDENTIFIER, "inmatning", 1, 28)
        ]
        self.assertEqual(self.tokenizer.tokenize(source), expected)

    def test_error_handling_section(self):
        source = "försök\n    kasta fel\nfånga fel"
        expected = [
            Token(TOKEN_TRY, "försök", 1, 1),
            Token(TOKEN_NEWLINE, "\n", 1, 7),
            Token(TOKEN_INDENT, "    ", 2, 1),
            Token(TOKEN_THROW, "kasta", 2, 5),
            Token(TOKEN_IDENTIFIER, "fel", 2, 11),
            Token(TOKEN_NEWLINE, "\n", 2, 14),
            Token(TOKEN_DEDENT, "", 3, 1),
            Token(TOKEN_CATCH, "fånga", 3, 1),
            Token(TOKEN_IDENTIFIER, "fel", 3, 7)
        ]
        self.assertEqual(self.tokenizer.tokenize(source), expected)

    def test_comments_section(self):
        source = ". skriver\nskriv hej"
        expected = [
            Token(TOKEN_PRINT, "skriv", 2, 1),
            Token(TOKEN_IDENTIFIER, "hej", 2, 7)
        ]
        self.assertEqual(self.tokenizer.tokenize(source), expected)

    def test_multiple_indents_nested(self):
        source = "om SANT\n    skriv nivå 1\n    om SANT\n        skriv nivå 2"
        expected = [
            Token(TOKEN_IF, "om", 1, 1),
            Token(TOKEN_LITERAL_TRUE, "SANT", 1, 4),
            Token(TOKEN_NEWLINE, "\n", 1, 8),
            Token(TOKEN_INDENT, "    ", 2, 1),
            Token(TOKEN_PRINT, "skriv", 2, 5),
            Token(TOKEN_IDENTIFIER, "nivå", 2, 11),
            Token(TOKEN_LITERAL_INT, "1", 2, 16),
            Token(TOKEN_NEWLINE, "\n", 2, 17),
            Token(TOKEN_IF, "om", 3, 5),
            Token(TOKEN_LITERAL_TRUE, "SANT", 3, 8),
            Token(TOKEN_NEWLINE, "\n", 3, 12),
            Token(TOKEN_INDENT, "        ", 4, 1),
            Token(TOKEN_PRINT, "skriv", 4, 9),
            Token(TOKEN_IDENTIFIER, "nivå", 4, 15),
            Token(TOKEN_LITERAL_INT, "2", 4, 20),
            Token(TOKEN_DEDENT, "", 5, 1),
            Token(TOKEN_DEDENT, "", 5, 1)
        ]
        self.assertEqual(self.tokenizer.tokenize(source), expected)

    def test_tokenize_from_keyword(self):
        """Verify that 'från' is tokenized correctly."""
        source = "skriv märke från min bil"
        tokens = self.tokenizer.tokenize(source)
        # Expected sequence: skriv, märke, från, min, bil
        # Check that 'från' is the 3rd token (index 2)
        self.assertEqual(tokens[2].type, TOKEN_FROM)
        self.assertEqual(tokens[2].value, "från")

    def test_tokenize_list_operations(self):
        """Verify tokens for setting and getting list elements."""
        source = (
            "sätt element 0 i minlista till röd\n"
            "skriv element 0 från minlista"
        )
        tokens = self.tokenizer.tokenize(source)

        # Expected types for the first line:
        # sätt (SET), element (ID), 0 (INT), i (ID), minlista (ID), till (TO), röd (ID)
        expected_types = [
            TOKEN_SET, TOKEN_IDENTIFIER, TOKEN_LITERAL_INT, TOKEN_IDENTIFIER,
            TOKEN_IDENTIFIER, TOKEN_TO, TOKEN_IDENTIFIER, TOKEN_NEWLINE,
            TOKEN_PRINT, TOKEN_IDENTIFIER, TOKEN_LITERAL_INT, TOKEN_FROM,
            TOKEN_IDENTIFIER
        ]

        actual_types = [t.type for t in tokens]
        self.assertEqual(actual_types, expected_types)

        # Specific Value Checks
        self.assertEqual(tokens[3].value, "i")
        self.assertEqual(tokens[11].value, "från")

    def test_bootstrapping_sanity_tokens(self):
        """Verify the precise token layout for the bootstrapping sanity test source."""
        source = """öppna källkod_test.hiuh för läsning som fil
sätt rad_nummer till 1

medan inte i slutet från fil
    sätt rad till nästa rad från fil

    . Inspect the first character of the line to find syntax shapes
    sätt första_tecken till element 0 från rad

    skriv rad_nummer plus . plus första_tecken plus mellanrum
    sätt rad_nummer till rad_nummer plus 1

stäng fil"""

        expected = [
            Token(TOKEN_OPEN, "öppna", 1, 1),
            Token(TOKEN_IDENTIFIER, "källkod_test.hiuh", 1, 7),
            Token(TOKEN_IDENTIFIER, "för", 1, 25),
            Token(TOKEN_IDENTIFIER, "läsning", 1, 29),
            Token(TOKEN_AS, "som", 1, 37),
            Token(TOKEN_IDENTIFIER, "fil", 1, 41),
            Token(TOKEN_NEWLINE, "\n", 1, 44),
            Token(TOKEN_SET, "sätt", 2, 1),
            Token(TOKEN_IDENTIFIER, "rad_nummer", 2, 6),
            Token(TOKEN_TO, "till", 2, 17),
            Token(TOKEN_LITERAL_INT, "1", 2, 22),
            Token(TOKEN_NEWLINE, "\n", 2, 23),
            Token(TOKEN_WHILE, "medan", 4, 1),
            Token(TOKEN_IDENTIFIER, "inte", 4, 7),
            Token(TOKEN_IDENTIFIER, "i", 4, 12),
            Token(TOKEN_IDENTIFIER, "slutet", 4, 14),
            Token(TOKEN_FROM, "från", 4, 21),
            Token(TOKEN_IDENTIFIER, "fil", 4, 26),
            Token(TOKEN_NEWLINE, "\n", 4, 29),
            Token(TOKEN_INDENT, "    ", 5, 1),
            Token(TOKEN_SET, "sätt", 5, 5),
            Token(TOKEN_IDENTIFIER, "rad", 5, 10),
            Token(TOKEN_TO, "till", 5, 14),
            Token(TOKEN_IDENTIFIER, "nästa", 5, 19),
            Token(TOKEN_IDENTIFIER, "rad", 5, 25),
            Token(TOKEN_FROM, "från", 5, 29),
            Token(TOKEN_IDENTIFIER, "fil", 5, 34),
            Token(TOKEN_NEWLINE, "\n", 5, 37),
            Token(TOKEN_SET, "sätt", 8, 5),
            Token(TOKEN_IDENTIFIER, "första_tecken", 8, 10),
            Token(TOKEN_TO, "till", 8, 24),
            Token(TOKEN_IDENTIFIER, "element", 8, 29),
            Token(TOKEN_LITERAL_INT, "0", 8, 37),
            Token(TOKEN_FROM, "från", 8, 39),
            Token(TOKEN_IDENTIFIER, "rad", 8, 44),
            Token(TOKEN_NEWLINE, "\n", 8, 47),
            Token(TOKEN_PRINT, "skriv", 10, 5),
            Token(TOKEN_IDENTIFIER, "rad_nummer", 10, 11),
            Token(TOKEN_OP_ADD, "plus", 10, 22),
            Token(TOKEN_IDENTIFIER, ".", 10, 27),
            Token(TOKEN_OP_ADD, "plus", 10, 29),
            Token(TOKEN_IDENTIFIER, "första_tecken", 10, 34),
            Token(TOKEN_OP_ADD, "plus", 10, 48),
            Token(TOKEN_IDENTIFIER, "mellanrum", 10, 53),
            Token(TOKEN_NEWLINE, "\n", 10, 62),
            Token(TOKEN_SET, "sätt", 11, 5),
            Token(TOKEN_IDENTIFIER, "rad_nummer", 11, 10),
            Token(TOKEN_TO, "till", 11, 21),
            Token(TOKEN_IDENTIFIER, "rad_nummer", 11, 26),
            Token(TOKEN_OP_ADD, "plus", 11, 37),
            Token(TOKEN_LITERAL_INT, "1", 11, 42),
            Token(TOKEN_NEWLINE, "\n", 11, 43),
            Token(TOKEN_DEDENT, "", 13, 1),
            Token(TOKEN_CLOSE, "stäng", 13, 1),
            Token(TOKEN_IDENTIFIER, "fil", 13, 7)
        ]

        self.assertEqual(self.tokenizer.tokenize(source), expected)

    def test_infix_grej_tokens(self):
        """Verify tokenization of 'infix grej' syntax for infix function definition."""
        source = "sätt innehåller till infix grej med lista, värde"
        expected = [
            Token(TOKEN_SET, "sätt", 1, 1),
            Token(TOKEN_IDENTIFIER, "innehåller", 1, 6),
            Token(TOKEN_TO, "till", 1, 17),
            Token(TOKEN_INFIX, "infix", 1, 22),
            Token(TOKEN_FUNC, "grej", 1, 28),
            Token(TOKEN_WITH, "med", 1, 33),
            Token(TOKEN_IDENTIFIER, "lista", 1, 37),
            Token(TOKEN_COMMA, ",", 1, 42),
            Token(TOKEN_IDENTIFIER, "värde", 1, 44)
        ]
        self.assertEqual(self.tokenizer.tokenize(source), expected)

if __name__ == '__main__':
    unittest.main()
