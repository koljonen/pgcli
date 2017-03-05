from pgcli.packages.parseutils.meta import FunctionMetadata, ForeignKey
from prompt_toolkit.completion import Completion
from functools import partial
from itertools import product
from prompt_toolkit.document import Document
from mock import Mock

escape = lambda name: ('"' + name + '"' if not name.islower() or name in (
    'select', 'insert') else name)

def completion(display_meta, text, pos=0):
    return Completion(text, start_position=pos, display_meta=display_meta)

def get_result(completer, text, position=None):
    position = len(text) if position is None else position
    return completer.get_completions(
        Document(text=text, cursor_position=position), Mock()
    )

def result_set(completer, text, position=None):
    return set(get_result(completer, text, position))


# The code below is quivalent to
# def schema(text, pos=0):
#   return completion('schema', text, pos)
# and so on
schema, table, view, function, column, keyword, datatype, alias, name_join,\
    fk_join, join = [partial(completion, display_meta)
    for display_meta in('schema', 'table', 'view', 'function', 'column',
    'keyword', 'datatype', 'table alias', 'name join', 'fk join', 'join')]

def wildcard_expansion(cols, pos=-1):
        return Completion(cols, start_position=pos, display_meta='columns',
            display = '*')

class MetaData(object):
    def __init__(self, metadata):
        self.metadata = metadata

    def builtin_functions(self, pos=0):
        return [function(f, pos) for f in self.completer.functions]

    def builtin_datatypes(self, pos=0):
        return [datatype(dt, pos) for dt in self.completer.datatypes]

    def keywords(self, pos=0):
        return [keyword(kw, pos) for kw in self.completer.keywords]

    def columns(self, parent, schema='public', typ='tables', pos=0):
        if typ == 'functions':
            fun = [x for x in self.metadata[typ][schema] if x[0] == parent][0]
            cols = fun[1]
        else:
            cols = self.metadata[typ][schema][parent]
        return [column(escape(col), pos) for col in cols]

    def datatypes(self, schema='public', pos=0):
        return [datatype(escape(x), pos)
            for x in self.metadata.get('datatypes', {}).get(schema, [])]

    def tables(self, schema='public', pos=0):
        return [table(escape(x), pos)
            for x in self.metadata.get('tables', {}).get(schema, [])]

    def views(self, schema='public', pos=0):
        return [view(escape(x), pos)
            for x in self.metadata.get('views', {}).get(schema, [])]

    def functions(self, schema='public', pos=0):
        return [function(escape(x[0] + '()'), pos)
            for x in self.metadata.get('functions', {}).get(schema, [])]

    def schemas(self, pos=0):
        schemas = set(sch for schs in self.metadata.values() for sch in schs)
        return [schema(escape(s), pos=pos) for s in schemas]

    @property
    def completer(self):
        return self.get_completer()

    def get_completers(self, casing):
        '''
        Returns a function taking three bools `casing`, `filtr`, `alias` and
        the list `qualify`, all defaulting to None.
        Returns a list of completers.
        These parameters specify the allowed values for the corresponding
        completer parameters, `None` meaning any, i.e. (None, None, None, None)
        results in all 24 possible completers, whereas e.g.
        (True, False, True, ['never']) results in the one completer with casing,
        without `search_path` filtering of objects, with table aliasing, and
        without column qualification.
        '''
        def _cfg(_casing, filtr, alias, qualify):
            cfg = {'settings':{}}
            if _casing:
                cfg['casing'] = casing
            cfg['settings']['search_path_filter'] = filtr
            cfg['settings']['generate_aliases'] = alias
            cfg['settings']['qualify_columns'] = qualify
            return cfg

        def _cfgs(casing, filtr, alias, qualify):
            casings = [True, False] if casing is None else [casing]
            filtrs = [True, False] if filtr is None else [filtr]
            aliases = [True, False] if alias is None else [alias]
            qualifys = qualify or ['always', 'if_more_than_one_table', 'never']
            return [
                _cfg(*p) for p in product(casings, filtrs, aliases, qualifys)
            ]

        def completers(casing=None, filtr=None, alias=None, qualify=None):
            get_comp = self.get_completer
            return [
                get_comp(**c) for c in _cfgs(casing, filtr, alias, qualify)
            ]

        return completers

    def get_completer(self, settings=None, casing=None):
        metadata = self.metadata
        from pgcli.pgcompleter import PGCompleter
        comp = PGCompleter(smart_completion=True, settings=settings)

        schemata, tables, tbl_cols, views, view_cols = [], [], [], [], []

        for schema, tbls in metadata['tables'].items():
            schemata.append(schema)

            for table, cols in tbls.items():
                tables.append((schema, table))
                # Let all columns be text columns
                tbl_cols.extend([(schema, table, col, 'text') for col in cols])

        for schema, tbls in metadata.get('views', {}).items():
            for view, cols in tbls.items():
                views.append((schema, view))
                # Let all columns be text columns
                view_cols.extend([(schema, view, col, 'text') for col in cols])

        functions = [FunctionMetadata(schema, *func_meta)
                        for schema, funcs in metadata['functions'].items()
                        for func_meta in funcs]

        datatypes = [(schema, datatype)
                        for schema, datatypes in metadata['datatypes'].items()
                        for datatype in datatypes]

        foreignkeys = [ForeignKey(*fk) for fks in metadata['foreignkeys'].values()
            for fk in fks]

        comp.extend_schemata(schemata)
        comp.extend_relations(tables, kind='tables')
        comp.extend_relations(views, kind='views')
        comp.extend_columns(tbl_cols, kind='tables')
        comp.extend_columns(view_cols, kind='views')
        comp.extend_functions(functions)
        comp.extend_datatypes(datatypes)
        comp.extend_foreignkeys(foreignkeys)
        comp.set_search_path(['public'])
        comp.extend_casing(casing or [])

        return comp
