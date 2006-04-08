#
# Copyright (C) 2006 Stefan Seefeld
# All rights reserved.
# Licensed to the public under the terms of the GNU LGPL (>= 2),
# see the file COPYING for details.
#

from Synopsis import AST, Type
from Synopsis.Formatters.HTML.Tags import *
from Synopsis.Formatters.HTML.Markup import *
import string, re

class Javadoc(Formatter):
    """A formatter that formats comments similar to Javadoc.
    @see <a href="http://java.sun.com/j2se/1.5.0/docs/tooldocs/solaris/javadoc.html">Javadoc Spec</a>"""

    class Block:

        def __init__(self, tag, arg, body):
            self.tag, self.arg, self.body = tag, arg, body
            

    summary = r'(\s*[\w\W]*?\.)(\s|$)'
    block_tags = r'(^\s*\@\w+[\s$])'
    link_split = r'({@link(?:plain)?\s[^}]+})'
    link = r'{@link(?:plain)?\s+([\w#.]+)(?:\([^\)]*\))?(\s+.*)?}'

    tag_name = {
    'author': ['Author', 'Authors'],
    'date': ['Date', 'Dates'],
    'deprecated': ['Deprecated', 'Deprecated'],
    'exception': ['Exception', 'Exceptions'],
    'invariant': ['Invariant', 'Invariants'],
    'keyword': ['Keyword', 'Keywords'],
    'param': ['Parameter', 'Parameters'],
    'postcondition': ['Postcondition', 'Postcondition'],
    'precondition': ['Precondition', 'Preconditions'],
    'return': ['Returns', 'Returns'],
    'see': ['See also', 'See also'],
    'throws': ['Throws', 'Throws'],
    'version': ['Version', 'Versions']}
    arg_tags = ['param', 'keyword', 'exception']


    def __init__(self):
        """Create regex objects for regexps"""

        self.summary = re.compile(Javadoc.summary)
        self.block_tags = re.compile(Javadoc.block_tags, re.M)
        self.link_split = re.compile(Javadoc.link_split)
        self.link = re.compile(Javadoc.link)


    def split(self, doc):
        """Split a javadoc comment into description and blocks."""

        chunks = self.block_tags.split(doc)
        description = chunks[0]
        blocks = []
        for i in range(1, len(chunks)):
            if i % 2 == 1:
                tag = chunks[i].strip()[1:]
            else:
                if tag in self.arg_tags:
                    arg, body = chunks[i].strip().split(None, 1)
                else:
                    arg, body = None, chunks[i]

                if tag == 'see' and body:
                    if body[0] in ['"', "'"]:
                        if body[-1] == body[0]:
                            body = body[1:-1]
                    elif body[0] == '<':
                        pass
                    else:
                        body = '{@link %s}'%body
                blocks.append(Javadoc.Block(tag, arg, body))
        
        return description, blocks


    def extract_summary(self, description):
        """Generate a summary from the given description."""

        m = self.summary.match(description)
        if m:
            return m.group(1)
        else:
            return description.split('\n', 1)[0]+'...'


    def format(self, decl, view):
        """Format using javadoc markup."""

        doc = decl.annotations.get('doc')
        doc = doc and doc.text or ''
        if not doc:
            return Struct('', '')
        description, blocks = self.split(doc)

        details = self.format_description(description, view, decl)
        summary = self.extract_summary(details)
        details += self.format_params(blocks, view, decl)
        details += self.format_tag('return', blocks, view, decl)
        details += self.format_throws(blocks, view, decl)
        details += self.format_tag('precondition', blocks, view, decl)
        details += self.format_tag('postcondition', blocks, view, decl)
        details += self.format_tag('invariant', blocks, view, decl)
        details += self.format_tag('author', blocks, view, decl)
        details += self.format_tag('date', blocks, view, decl)
        details += self.format_tag('version', blocks, view, decl)
        details += self.format_tag('see', blocks, view, decl)

        return Struct(summary, details)


    def format_description(self, text, view, decl):

        return self.format_link(view, decl, text)


    def format_link(self, view, decl, text):
        """Formats inline @see tags in the text"""

        chunks = self.link_split.split(text)
        text = ''
        for i in range(len(chunks)):
            if i % 2 == 0:
                text += chunks[i]
            else:
                m = self.link.match(chunks[i])
                if m is None:
                    continue
                target, name = m.groups()
                if target[0] == '#':
                    target = target[1:]
                target = target.replace('#', '.')
                target = re.sub(r'\(.*\)', '', target)

                if name is None:
                    name = target
                else:
                    name = name.strip()
                text += self.find_link(view, name, decl)
        return text


    def format_params(self, blocks, view, decl):
        """Formats a list of (param, description) tags"""

        content = ''
        params = [b for b in blocks if b.tag == 'param']
        if params:
            content += div('tag-heading',"Parameters:")
            dl = entity('dl', ''.join([entity('dt', p.arg) + entity('dd', p.body)
                                       for p in params]))
            content += div('tag-section', dl)
        kwds = [b for b in blocks if b.tag == 'keyword']
        if kwds:
            content += div('tag-heading',"Keywords:")
            dl = entity('dl', ''.join([entity('dt', k.arg) + entity('dd', k.body)
                                       for k in kwds]))
            content += div('tag-section', dl)
        return content


    def format_throws(self, blocks, view, decl):

        content = ''
        throws = [b for b in blocks if b.tag in ['throws', 'exception']]
        if throws:
            content += div('tag-heading',"Throws:")
            dl = entity('dl', ''.join([entity('dt', t.arg) + entity('dd', t.body)
                                       for t in throws]))
            content += div('tag-section', dl)
        return content


    def format_tag(self, tag, blocks, view, decl):

        content = ''
        items = [b for b in blocks if b.tag == tag]
        if items:
            content += div('tag-heading', self.tag_name[tag][1])
            content += div('tag-section',
                           '<br/>'.join([i.body for i in items]))
        return content
   

    def find_link(self, view, ref, decl):
        """Given a "reference" and a declaration, returns a HTML link.
        Various methods are tried to resolve the reference. First the
        parameters are taken off, then we try to split the ref using '.' or
        '::'. The params are added back, and then we try to match this scoped
        name against the current scope. If that fails, then we recursively try
        enclosing scopes.
        """

        # Remove params
        index, label = string.find(ref,'('), ref
        if index >= 0:
            params = ref[index:]
            ref = ref[:index]
        else:
            params = ''
        # Split ref
        ref = string.split(ref, '.')
        if len(ref) == 1:
            ref = string.split(ref[0], '::')
        # Add params back
        ref = ref[:-1] + [ref[-1]+params]
        # Find in all scopes
        scope = list(decl.name())
        while 1:
            entry = self._find_link_at(ref, scope)
            if entry:
                url = rel(view.filename(), entry.link)
                return href(url, label)
            if len(scope) == 0: break
            del scope[-1]
        # Not found
        return label+' '


    def _find_link_at(self, ref, scope):
        # Try scope + ref[0]
        entry = self.processor.toc.lookup(scope+ref[:1])
        if entry:
            # Found.
            if len(ref) > 1:
                # Find sub-refs
                entry = self._find_link_at(ref[1:], scope+ref[:1])
                if entry:
                    # Recursive sub-ref was okay!
                    return entry 
            else:
                # This was the last scope in ref. Done!
                return entry
        # Try a method name match:
        if len(ref) == 1:
            entry = self._find_method_entry(ref[0], scope)
            if entry: return entry
        # Not found at this scope
        return None


    def _find_method_entry(self, name, scope):
        """Tries to find a TOC entry for a method adjacent to decl. The
        enclosing scope is found using the types dictionary, and the
        realname()'s of all the functions compared to ref."""

        try:
            scope = self.processor.ast.types()[scope]
        except KeyError:
            #print "No parent scope:",decl.name()[:-1]
            return None
        if not scope: return None
        if not isinstance(scope, Type.Declared): return None
        scope = scope.declaration()
        if not isinstance(scope, AST.Scope): return None
        for decl in scope.declarations():
            if isinstance(decl, AST.Function):
                if decl.realname()[-1] == name:
                    return self.processor.toc.lookup(decl.name())
        # Failed
        return None
