import re
import collections


Token = collections.namedtuple('Token', 'tpe token')


LINE_COMMENT = 1
BLOCK_COMMENT = 2
STRING = 3
SEMICOLON = 4
OTHER = 5
WHITESPACE = 6


class CQLSplitter(object):
    """Makeshift CQL parser that can only split up multiple statements.

    C* does not accept multiple DDL queries as a single string, as it can with
    DML queries using batches. Hence, we must split up CQL files to run each
    statement individually. Do that by using a simple Regex scanner, that just
    recognizes strings, comments and delimiters, which is enough to split up
    statements without tripping when semicolons are commented or escaped.
    """

    @classmethod
    def scanner(cls):
        if not getattr(cls, '_scanner', None):
            def h(tpe):
                return lambda sc, token: Token(tpe, token)

            cls._scanner = re.Scanner([
                (r"(--|//).*?$",               h(LINE_COMMENT)),
                (r"\/\*.+?\*\/",               h(BLOCK_COMMENT)),
                (r'"(?:[^"\\]|\\.)*"',         h(STRING)),
                (r"'(?:[^'\\]|\\.)*'",         h(STRING)),
                (r"\$\$(?:[^\$\\]|\\.)*\$\$",  h(STRING)),
                (r";",                         h(SEMICOLON)),
                (r"\s+",                       h(WHITESPACE)),
                (r".",                         h(OTHER))
            ], re.MULTILINE | re.DOTALL)
        return cls._scanner

    @classmethod
    def split(cls, query):
        """Split up content, and return individual statements uncommented"""

        tokens, match = cls.scanner().scan(query)
        cur_statement = ''
        statements = []

        for token in tokens:
            if token.tpe == LINE_COMMENT:
                pass
            elif token.tpe == SEMICOLON:
                stm = cur_statement.strip()
                if stm:
                    statements.append(stm)
                cur_statement = ''
            elif token.tpe in (WHITESPACE, BLOCK_COMMENT):
                cur_statement += ' '
            elif token.tpe in (STRING, OTHER):
                cur_statement += token.token

        stm = cur_statement.strip()
        if stm:
            statements.append(stm)

        return statements
