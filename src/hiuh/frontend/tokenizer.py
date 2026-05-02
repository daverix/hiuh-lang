from dataclasses import dataclass
from typing import List

@dataclass
class Token:
    """Represents a single lexical token."""
    type: str
    value: str
    line: int = 1
    column: int = 1

# --- Compiler Structural Tokens ---
# These tokens are emitted by the tokenizer based on expected grammar rules,
# fulfilling the requirement for the Parser's scope management.
TOKEN_INDENT = "INDENT"
TOKEN_DEDENT = "DEDENT"
TOKEN_SCOPE_CHANGE = "SCOPE_BREAK" # Generic token for block start/end context

class Tokenizer:
    """
    Tokenizes the input source code string character by character according 
    to hiue language rules, including structural scope markers.
    """
    
    # Define common keywords and structural identifiers
    KEYWORDS = {
        # Control Flow/Structure
        "sätt": "KEYWORD_SET",
        "om": "KEYWORD_IF",
        "annars": "KEYWORD_ELSE",
        "medan": "KEYWORD_WHILE",
        "prova": "KEYWORD_TRY",
        "fånga": "KEYWORD_CATCH",
        "är": "KEYWORD_IS",
        "till": "KEYWORD_TO",
        "namn": "TYPE_FIELD",
        "ålder": "TYPE_FIELD",
        "list": "TYPE_LIST",
        # Structural Markers
        "låsta": "BLOCK_START_KEYWORD", # Example: Keyword that MUST imply a block starts
        "slut": "STATEMENT_END_KEYWORD",
    }

    # Complex tokens that need multi-word detection
    MULTI_WORD_KEYWORDS = [
        "större än", 
        "större än eller lika med", 
        "mindre än", 
        "mindre än eller lika med", 
        "inte lika med"
    ]
    
    def __init__(self):
        pass

    def tokenize(self, code: str) -> List[Token]:
        """
        Takes a source code string and outputs a list of structured tokens 
        by scanning the code character by character.
        """
        tokens: List[Token] = []
        current_line = 1
        current_col = 1
        
        i = 0
        code_length = len(code)
        
        while i < code_length:
            start_i = i
            start_line = current_line
            current_token_value = ""
            token_type = None

            # 1. Skip Whitespace (and track newline for context)
            if code[i].isspace():
                if code[i] == '\n':
                    # A newline often signifies a structural break (potential scope change)
                    current_line += 1
                    current_col = 1
                    # Emit a soft structural break token for the parser
                    tokens.append(Token(type=TOKEN_SCOPE_CHANGE, value="", line=start_line, column=current_col))
                else:
                    current_col += 1
                i += 1
                continue

            # --- Structural/Multi-Word Token Detection ---
            
            # 2. Check for Multi-Word Keywords/Operators
            found_multi_word = False
            for phrase in self.MULTI_WORD_KEYWORDS:
                phrase_text = phrase
                phrase_len = len(phrase_text)
                if code[i:i + phrase_len].lower() == phrase_text:
                    token_type = self.KEYWORDS[phrase_text]
                    tokens.append(Token(type=token_type, value=phrase_text, line=start_line, column=current_col))
                    i += phrase_len
                    current_col += phrase_len
                    found_multi_word = True
                    break
            
            if found_multi_word:
                continue

            # 3. Check for Single-Word Keywords/Operators
            word_start = i
            word_end = i
            # Find the end of the current word/identifier
            while word_end < code_length and not code[word_end].isspace() and code[word_end] not in (',',):
                word_end += 1
            
            word = code[word_start:word_end]
            
            if word:
                token_type = None
                
                # A. Check for structural keywords that imply scope
                if word.lower() in self.KEYWORDS:
                    token_type = self.KEYWORDS[word.lower()]

                # B. Handle Punctuation
                elif word == ',':
                    token_type = "SEP_COMMA"
                
                # C. Check for Literals (assuming numbers only)
                elif word.isdigit():
                    token_type = "LITERAL_INT"
                
                # D. Default Token
                else:
                    token_type = "IDENTIFIER"

                # Token emission
                tokens.append(Token(type=token_type, value=word, line=start_line, column=current_col))
                
                # Update position trackers
                current_col += len(word)
                i = word_end
            else:
                break
        
        # Post-processing check for block structural tokens
        # A real implementation would look for keywords like ': ' or explicit markers 
        # to emit INDENT/DEDENT. Here, we add a heuristic for demonstration:
        final_tokens = []
        for token in tokens:
            if token.type == "KEYWORD_IF" and token.value == "if":
                final_tokens.append(token)
                # Heuristic: If 'if' is found, immediately append an INDENT token
                final_tokens.append(Token(type=TOKEN_INDENT, value="{}".format(token.type), line=token.line, column=token.column))
            elif token.type == "STATEMENT_END_KEYWORD":
                # Heuristic: If we hit a block end keyword, assume we need to DEDENT
                final_tokens.append(token)
                final_tokens.append(Token(type=TOKEN_DEDENT, value="{}".format(token.type), line=token.line, column=token.column))
            else:
                final_tokens.append(token)
                
        return final_tokens

# Example Usage (for testing purposes)
if __name__ == "__main__":
    # Demonstrating structural markers:
    sample_code = """
namn = 10
sätt x till 5
om x är större än 2
  print('Hello')
slut
"""
    
    tokenizer = Tokenizer()
    print("Tokenizing sample code with structural support...")
    
    tokens = tokenizer.tokenize(sample_code)
    for token in tokens:
        # Check for N/A type (internal indicator)
        display_type = token.type if token.type != "INDENT" else "INDENT"
        display_type = display_type if display_type != "DEDENT" else "DEDENT"
        print(f"[{display_type:<25}] '{token.value:<20}' (Line {token.line}, Col {token.column})")
