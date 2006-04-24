#
# Copyright (C) 2006 Stefan Seefeld
# All rights reserved.
# Licensed to the public under the terms of the GNU LGPL (>= 2),
# see the file COPYING for details.
#

from Synopsis import AST, Type
from Synopsis.SourceFile import SourceFile
from Synopsis.DocString import DocString
import pattern
import parser
import token
import tokenize
import symbol
import keyword

HAVE_ENCODING_DECL = hasattr(symbol, "encoding_decl") # python 2.3
HAVE_IMPORT_NAME = hasattr(symbol, "import_name") # python 2.4
HAVE_DECORATOR = hasattr(symbol,"decorator") # python 2.4

def stringify(ptree):
    """Convert the given ptree to a string."""

    if type(ptree) == int: return ''
    elif type(ptree) != tuple: return str(ptree)
    else: return ''.join([stringify(i) for i in ptree])


def num_tokens(ptree):
    """Count the number of leaf tokens in the given ptree."""

    if type(ptree) == str: return 1
    else: return sum([num_tokens(n) for n in ptree[1:]])


class _DummyFile:

    def write(self, data): pass


class LexerDebugger:

    def __init__(self, lexer):

        self.lexer = lexer

    def next(self):

        n = self.lexer.next()
        print 'next is "%s" (%s)'%(n[1], n[0])
        return n

header="""
<?xml version="1.0"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html>
  <head>
    <title>%(title)s</title>
    <style type="text/css">
    pre { background-color:#eeeeee;}
    .lineno
    {
      font-style: italic;
      font-size: 90%%;
      padding-left: .5em;
    }
    .py-line
    {
      border-left: 1px solid black;
      margin-left: .2em;
      padding-left: .4em;
    }
    .py-string { background: transparent; color: #006030; }
    .py-comment { background: transparent; color: #003060; }
    .py-keyword { background: transparent; color: #600000; }
    </style>
  </head>
<body>
<pre>
<span class="lineno">%(lineno)s</span><span class="py-line">"""

trailer="""</span>
</pre>
</body>
</html>
"""

def escape(text):

    for p in [('&', '&amp;'), ('<', '&lt;'), ('>', '&gt;'),]:
        text = text.replace(*fix)
    return text


class ASTTranslator:
    """Translate a Python parse tree into the Synopsis AST.
    Unfortunately using the Python parser module alone is not enough
    as it doesn't preserve all the necessary information, such as token
    positions. Therefor we travers the parse tree and the token stream
    in parallel."""

    def __init__(self, scope, types):
        """Create an ASTTranslator.
        :Parameters:
          :'scope': scope to place all toplevel declarations into.
          :'types': type dictionary into which to inject newly declared types."""

        self.handlers = {}
        self.handlers[token.ENDMARKER] = self.handle_end_marker
        self.handlers[token.NEWLINE] = self.handle_newline
        self.handlers[token.INDENT] = self.handle_indent
        self.handlers[token.DEDENT] = self.handle_dedent
        self.handlers[token.STRING] = self.handle_string
        self.handlers[symbol.funcdef]= self.handle_function
        self.handlers[symbol.parameters] = self.handle_parameters
        self.handlers[symbol.classdef] = self.handle_class
        self.handlers[token.NAME] = self.handle_name
        #self.handlers[symbol.expr_stmt] = self.handle_expression
        #self.handlers[token.OP] = self.handle_op
        self.handlers[symbol.power] = self.handle_power
        if HAVE_ENCODING_DECL:
            self.handlers[symbol.encoding_decl] = self.handle_encoding_decl
        if HAVE_IMPORT_NAME:
            self.handlers[symbol.import_as_names] = self.handle_import_as_names
            self.handlers[symbol.dotted_as_names] = self.handle_dotted_as_names
            self.handlers[symbol.import_from] = self.handle_import_from
            self.handlers[symbol.import_name] = self.handle_import_name
        else:
            self.handlers[symbol.import_stmt] = self.handle_import
        if HAVE_DECORATOR:
            self.handlers[symbol.decorator] = self.handle_decorator

        self._any_type = Type.Base('Python',('',))
        self._sourcefile = scope.file()
        self._col = 0
        self._lineno = 1
        self._parameters = []
        self._scopes = [scope]
        self._types = types
        self._imported_modules = []


    def imported_modules(self):

        return self._imported_modules

    
    def process_file(self, filename, xref):

        input = open(filename, 'r+')
        src = input.readlines()
        self._lines = len(`len(src) + 1`)
        ptree = parser.ast2tuple(parser.suite(''.join(src)))
        input.seek(0)
        self.lexer = tokenize.generate_tokens(input.readline)
        #self.lexer = LexerDebugger(tokenize.generate_tokens(input.readline))
        if xref:
            self.xref = open(xref, 'w+')
            lineno_template = '%%%ds' % self._lines
            lineno = lineno_template % self._lineno
            self.xref.write(header % {'title':'a title',
                                      'lineno':lineno})
        else:
            self.xref = _DummyFile()
        try:
            self.handle(ptree)
        except StopIteration:
            raise
        self.xref.write(trailer)


    def handle(self, ptree):

        if type(ptree) == tuple:
            kind = ptree[0]
            value = ptree[1:]
            handler = self.handlers.get(kind, self.default_handler)
            #print 'handle', kind, handler, value
            handler(value)
        else:
            raise Exception("Process error: Type is not a tuple %s" % str(ptree))


    def default_handler(self, ptree):

        for node in ptree:
            if type(node) == tuple: self.handle(node)
            elif type(node) == str: self.handle_token(node)
            else: raise Exception("Invalid ptree node")


    def handle_token(self, item = None):

        t = self.lexer.next()
        # Some tokens are not part of the parse tree.
        # Handle them silently.
        while t[0] in [tokenize.NL, tokenize.COMMENT]:
            if t[0] is tokenize.NL:
                self.print_newline()
            elif t[0] is tokenize.COMMENT:
                self.print_token(t)
                if t[1][-1] == '\n': self.print_newline()
            t = self.lexer.next()

        if item is not None and t[1] != item:
            raise 'Internal error in line %d: expected "%s", got "%s" (%d)'%(self._lineno, item, t[1], t[0])
        else:
            self.print_token(t)
  

    def handle_tokens(self, ptree):

        tokens = num_tokens(ptree)
        for i in xrange(tokens):
            self.handle_token()
  

    def handle_end_marker(self, nodes): pass
    def handle_newline(self, nodes):

        self.handle_token()


    def handle_indent(self, indent):

        self.handle_token()
        
        
    def handle_dedent(self, dedent):

        self.handle_token()
        
        
    def handle_string(self, content):

        self.handle_token()

        
    def handle_function(self, nodes):

        if HAVE_DECORATOR:
            if nodes[0][0] == symbol.decorators:
                offset = 1
                # FIXME
                self.handle(nodes[0])
            else:
                offset = 0
        else:
            offset = 0
            
        def_token = nodes[0 + offset]
        self.handle_token(def_token[1])
        name_token = nodes[1 + offset]
        self.handle_token(name_token[1])
        # Handle the parameters.
        self.handle(nodes[2 + offset])

        name = tuple(self._scopes[-1].name() + (name_token[1],))
        if type(self._scopes[-1]) == AST.Class:
            function = AST.Operation(self._sourcefile, self._lineno, 'operation', '',
                                     self._any_type, '', name, name[-1])
        else:
            function = AST.Function(self._sourcefile, self._lineno, 'function', '',
                                    self._any_type, '', name, name[-1])
        function.parameters().extend(self._parameters)

        colon_token = nodes[3 + offset]
        self.handle_token(colon_token[1])
        body = nodes[4 + offset]
        self.handle_tokens(body)
        docstring = self.extract_docstring(body)
        if docstring:
            function.annotations['doc'] = docstring

        self._scopes[-1].declarations().append(function)

        # Don't traverse the function body, since the AST doesn't handle
        # local declarations anyways.


    def handle_parameters(self, nodes):

        self.handle_token(nodes[0][1])
	self._parameters = []
        if nodes[1][0] == symbol.varargslist:
            args = list(nodes[1][1:])
            while args:
                if args[0][0] == token.COMMA:
                    self.handle_token(args[0][1])
                    pass
                elif args[0][0] == symbol.fpdef:
                    self.handle_tokens(args[0])
                    parameter = AST.Parameter('', self._any_type, '',
                                              stringify(args[0]),
                                              '')
                    self._parameters.append(parameter)
                elif args[0][0] == token.EQUAL:
                    self.handle_token(args[0][1])
                    del args[0]
                    self.handle_tokens(args[0])
                    # HACK: replace the parameter as the current API doesn't allow
                    #       to set its value.
                    old = self._parameters[-1]
                    parameter = AST.Parameter('', self._any_type, '',
                                              old.identifier(),
                                              stringify(args[0]))
                    self._parameters[-1] = parameter
                elif args[0][0] == token.DOUBLESTAR:
                    self.handle_token(args[0][1])
                    del args[0]
                    self.handle_token(args[0][1])
                    parameter = AST.Parameter('', self._any_type, '',
                                              '**'+stringify(args[0]),
                                              stringify(args[0]))
                    self._parameters.append(parameter)
                elif args[0][0] == token.STAR:
                    self.handle_token(args[0][1])
                    del args[0]
                    self.handle_token(args[0][1])
                    parameter = AST.Parameter('', self._any_type, '',
                                              '*'+stringify(args[0]),
                                              stringify(args[0]))
                    self._parameters.append(parameter)
                else:
                    print "Unknown symbol:",args[0]
                del args[0]
        self.handle_token(nodes[-1][1])


    def handle_class(self, nodes):

        class_token = nodes[0]
        self.handle_token(class_token[1])
        name_token = nodes[1]
        self.handle_token(name_token[1])
        base_clause = nodes[2][0] == token.LPAR and nodes[3] or None
        self.handle_tokens(nodes[2])
        bases = []
        if base_clause:
            for test in base_clause[1:]:
                found, vars = pattern.match(pattern.TEST_NAME_PATTERN, test)
                if found and vars.has_key('power'):
                    power = vars['power']
                    if power[0] != symbol.power: continue
                    atom = power[1]
                    if atom[0] != symbol.atom or atom[1][0] != token.NAME: continue
                    name = [atom[1][1]]
                    for trailer in power[2:]:
                        if trailer[2][0] == token.NAME: name.append(trailer[2][1])

                    # FIXME: This logic is broken !
                    #        It assumes that names are either local or fully qualified.
                    if len(name) == 1:
                        # Name is unqualified. Qualify it.
                        name = self._scopes[-1].name() + tuple(name)
                    if self._types.has_key(name):
                        base = self._types[name]
                    else:
                        base = Type.Unknown('Python', name)
                    bases.append(AST.Inheritance('', base, ''))
            self.handle_tokens(base_clause)
            self.handle_token(')')
            self.handle_token(':')

            body = nodes[6]
        else:
            body = nodes[3]

        name = tuple(self._scopes[-1].name() + (name_token[1],))
        class_ = AST.Class(self._sourcefile, self._lineno, 'class', name)
        class_.parents().extend(bases)
        docstring = self.extract_docstring(nodes[-1])
        if docstring:
            class_.annotations['doc'] = docstring
        self._scopes[-1].declarations().append(class_)
        self._types[class_.name()] = Type.Declared('Python', class_.name(), class_)

        self._scopes.append(class_)
        self.handle(body)
        self._scopes.pop()
        

    def handle_name(self, content):

        self.handle_token(content[0])


    def handle_dotted_name(self, dname, rest):

        self.handle_token(dname[0])    
        for name in dname[1:]:
            self.handle_token('.')
            self.handle_token(name)
        map(self.handle, rest)
        

    def handle_op(self, nodes): pass


    def handle_power(self, content):

        def get_dotted_name(content):
            if content[0][0] != symbol.atom or content[0][1][0] != token.NAME:
                return None
            dotted_name = [content[0][1][1]]
            i = 1
            for param in content[1:]:
                if param[0] != symbol.trailer: break
                if param[1][0] != token.DOT: break
                if param[2][0] != token.NAME: break
                dotted_name.append(param[2][1])
                i += 1
            if i < len(content): return dotted_name, content[i:]
            else: return dotted_name, []

        name = get_dotted_name(content)
        if name: self.handle_dotted_name(*name)
        else: map(self.handle, content)


    def handle_encoding_decl(self, nodes): pass
    def handle_import_as_names(self, nodes):

        for n in nodes: self.handle(n)

        
    def handle_dotted_as_names(self, nodes):

        for n in nodes: self.handle(n)


    def handle_import_from(self, nodes):

        self.handle_token('from')
        self.handle(nodes[1])
        self.handle_token('import')
        self.handle(nodes[3])

    def handle_import_name(self, nodes):

        self.handle_token('import')
        self.handle_dotted_as_names(nodes[1][1:])

        
    def handle_import(self, nodes): pass
    def handle_decorator(self, nodes): pass

    def extract_docstring(self, ptree):

        if len(ptree) == 2:
            found, vars = pattern.match(pattern.DOCSTRING_STMT_PATTERN[1], ptree[1])
        else:
            found, vars = pattern.match(pattern.DOCSTRING_STMT_PATTERN, ptree[3])
        if found:
            #TODO figure out markup from __doc_format__ spec
            return DocString(eval(vars['docstring']), '')


    def print_token(self, t):

        kind, value, (srow, scol), (erow, ecol), line = t
        if kind == token.NEWLINE:
            self.print_newline()
        else:
            if self._col != scol:
                self.xref.write(' ' * (scol - self._col))
            if keyword.iskeyword(value):
                format = '<span class="py-keyword">%s</span>'
            elif kind == token.STRING:
                format = '<span class="py-string">%s</span>'
                chunks = value.split('\n')
                for c in chunks[:-1]:
                    self.xref.write(format % c)
                    self.print_newline()
                value = chunks[-1]
                    
            elif kind == tokenize.COMMENT:
                format = '<span class="py-comment">%s</span>'
                if value[-1] == '\n': value = value[:-1]
            else:
                format = '%s'

            self.xref.write(format % value)
            self._col = ecol


    def print_newline(self):

        self._col = 0
        self._lineno += 1
        self.xref.write('</span>\n')
        lineno_template = '%%%ds' % self._lines
        lineno = lineno_template % self._lineno
        self.xref.write('<span class="lineno">%s</span>' % lineno)
        self.xref.write('<span class="py-line">')
