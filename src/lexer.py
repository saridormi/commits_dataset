from typing import List, Iterable, Dict, Tuple
from pygments import lex
from pygments.token import _TokenType, Text
from pygments.util import ClassNotFound
from pygments.lexers import guess_lexer_for_filename, TextLexer


class Lexer:
    """
    This class finds appropriate lexer for each file diff.
    It is used as pre-tokenizer for our custom BPE tokenizer.
    """

    @staticmethod
    def _lex_single_file_diff(fname: str, diff: str) -> Iterable[Tuple[_TokenType, str]]:
        """
        This method finds appropriate lexer based on diff and filename and returns resulting lexemes.

        In case pygments doesn't have appropriate lexer or decides to use TextLexer (which doesn't do anything),
        tokens are simply split by spaces.
        """
        try:
            lexer = guess_lexer_for_filename(fname, diff)
            if not isinstance(lexer, TextLexer):
                yield from lex(diff, lexer)
            else:
                yield from ((Text, token) for token in diff.split())
        except ClassNotFound:
            yield from ((Text, token) for token in diff.split())

    @staticmethod
    def lex(cur_mods: List[Dict[str, str]], sep_token: str) -> str:
        """
        This method iterates over all modifications in current commit and lexes each of them.
        """
        tokens: List[str] = []

        for mod in cur_mods:
            if mod["change_type"] == "UNKNOWN":
                continue
            if mod["change_type"] == "ADD":
                file_diff = f"new file {mod['new_path']}\n"
                fname = mod["new_path"]
            elif mod["change_type"] == "DELETE":
                file_diff = f"deleted file {mod['old_path']}\n"
                fname = mod["old_path"]
            elif mod["change_type"] == "RENAME":
                file_diff = f"rename from {mod['old_path']}\nrename to {mod['new_path']}\n"
                fname = mod["new_path"]
            elif mod["change_type"] == "COPY":
                file_diff = f"copy from {mod['old_path']}\ncopy to {mod['new_path']}\n"
                fname = mod["new_path"]
            else:
                file_diff = f"{mod['new_path']}\n"
                fname = mod["new_path"]

            mod_tokenized = Lexer._lex_single_file_diff(fname, mod["diff"])
            tokens.extend((token.strip() for token in file_diff.split()))
            tokens.extend((lexeme[1].strip() for lexeme in mod_tokenized if lexeme[1].strip()))

        return sep_token.join(tokens)
