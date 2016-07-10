from pgcli.packages.tabulate import tabulate
from textwrap import dedent


def test_dont_strip_leading_whitespace():
    data = [['    abc']]
    headers = ['xyz']
    tbl, _ = tabulate(data, headers, tablefmt='psql')
    assert tbl == dedent('''
        +---------+
        | xyz     |
        |---------|
        |     abc |
        +---------+ ''').strip()

def test_no_headers():
    data = ['abc']
    tbl, _ = tabulate(data, tablefmt='psql')
    assert tbl == dedent('''
        +---+---+---+
        | a | b | c |
        +---+---+---+''').strip()
