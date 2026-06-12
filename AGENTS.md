# hiuh-lang

We are building a compiler for a custom language called "hiue".

Check README.md for usage and language structure. **This is NOT pseudo code**.

We code the compiler in Python but the goal is to boostrap it.

## Structure

frontend with tokenizer and parser, backends for different platforms.

| filename | description |
|----------|-------------|
| src/hiuh/frontend/tokenizer.py | Inputs source code and outputs list of Token objects. |
| src/hiuh/frontend/parser.py | Inputs list of token objects and outputs an AST. |
| src/hiuh/backend/ | Directory different backends |
| src/hiuh/backend/x86/ | Directory for x86 backend |
| tests/   | Directory for tests. |

## Compiler

* The compiler should read hiuh code and provide an executable binary for the x86 backend.
* The tokenizer should output indent and dedent tokens to simplify the parser. 
* Each token should include row and column so that error reporting will be easier.
* The parser should output an intermediate representation so that different backends can output executables.

## Hiuh Language Constraints

When writing hiuh code (`.hiuh` files), use only characters available on a Swedish mobile keyboard:
* Swedish letters: a-ö (including å, ä, ö)
* Space
* Comma
* Dot

This ensures hiuh code can be written easily on mobile devices without switching keyboard layouts.

Try to make expression as clear as possible by breaking out parts as separate variables. Use ascii codes 
(`kod som tecken`) instead of quotes around a single character.

## Agent Protocol Updates

To ensure reliable development and prevent silent failures:
1.  **File Writing Verification:** After executing any `write` tool call for a source code file (`.py`):
    *   Immediately follow up with a `read` tool call for that specific file path.
    *   If the read operation fails (`ENOENT` or similar), the agent must halt and report the failure to the user, asking for confirmation or necessary context.
    *   If the read operation succeeds, the agent must confirm the content matches the written content and proceed.
2.  Any failure in this protocol must be reported before moving to the next logical step.
3.  **Build Verification:** After any code change in core files (e.g., src/), the agent MUST run `build.sh` to confirm compilation and test suite availability.

## Git Rules
- NEVER use `git checkout .` or `git checkout -- .` on all files
- If you get stuck: commit your progress first, then explain the problem
- Use `git stash` instead of checkout when you want to temporarily set aside changes
- Refactor one file at a time, verify, commit — then move to the next