import pytest

import cstarmigrate.cql


@pytest.mark.parametrize('cql,statements', [
    # Two statements, with whitespace
    (
        """
        CREATE TABLE hello;
        CREATE TABLE world;
        """,
        ['CREATE TABLE hello', 'CREATE TABLE world'],
    ),

    # Two statements, no whitespace
    (
        """
        CREATE TABLE hello;
        CREATE TABLE world;
        """,
        ['CREATE TABLE hello', 'CREATE TABLE world'],
    ),

    # Two statements, with line and block comments
    (
        """
        // comment
        -- comment
        CREATE TABLE hello;
        /* comment; comment
        */
        CREATE TABLE world;
        """,
        ['CREATE TABLE hello', 'CREATE TABLE world']
    ),

    # Statements with semicolons inside strings
    (
        """
        CREATE TABLE 'hello;';
        CREATE TABLE "world;"
        """,
        ["CREATE TABLE 'hello;'", 'CREATE TABLE "world;"'],
    ),

    # Double-dollar-sign quoted strings
    (
        """
        INSERT INTO test (test)
        VALUES ($$Pesky semicolon here ;Hello$$);
        """,
        ["INSERT INTO test (test) VALUES ($$Pesky semicolon here ;Hello$$)"],
    ),
])
def test_cql_split(cql, statements):
    result = cstarmigrate.cql.CQLSplitter.split(cql.strip())

    assert result == statements
