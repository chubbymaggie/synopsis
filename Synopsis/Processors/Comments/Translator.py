#
# Copyright (C) 2006 Stefan Seefeld
# All rights reserved.
# Licensed to the public under the terms of the GNU LGPL (>= 2),
# see the file COPYING for details.
#

from Synopsis import AST
from Synopsis.DocString import DocString
from Synopsis.Processor import Processor, Parameter
from Filter import *

class Translator(Processor, AST.Visitor):
    """A Translator translates comments into documentation."""

    filter = Parameter(SSFilter(), 'A comment filter to apply.')
    processor = Parameter(None, 'A comment processor to run.')
    markup = Parameter('', 'The markup type for this declaration.')
    concatenate = Parameter(False, 'Whether or not to concatenate adjacent comments.')
    primary_only = Parameter(True, 'Whether or not to preserve secondary comments.')

    def process(self, ast, **kwds):
      
        self.set_parameters(kwds)
        self.ast = self.merge_input(ast)
        if self.filter:
            self.ast = self.filter.process(self.ast)
        if self.processor:
            self.ast = self.processor.process(self.ast)

        for decl in self.ast.declarations():
            decl.accept(self)

        return self.output_and_return_ast()


    def visitDeclaration(self, decl):
        """Map comments to a doc string."""

        comments = decl.annotations.get('comments')
        if comments:
            text = None
            if self.primary_only:
                text = comments[-1]
            elif self.combine:
                text = ''.join([c for c in comments if c])
            else:
                comments = comments[:]
                comments.reverse()
                for c in comments:
                    if c is not None:
                        text = c
                        break
            doc = DocString(text or '', self.markup)
            decl.annotations['doc'] = doc