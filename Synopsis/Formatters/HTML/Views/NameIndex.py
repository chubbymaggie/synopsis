# $Id: NameIndex.py,v 1.15 2003/11/16 21:09:45 stefan Exp $
#
# Copyright (C) 2000 Stephen Davies
# Copyright (C) 2000 Stefan Seefeld
# All rights reserved.
# Licensed to the public under the terms of the GNU LGPL (>= 2),
# see the file COPYING for details.
#

from Synopsis.Processor import Parameter
from Synopsis import AST, Type
from Synopsis.Formatters.HTML import core, Tags
from Synopsis.Formatters.HTML.Page import Page
from Synopsis.Formatters.HTML.Tags import *

import os

class NameIndex(Page):
   """Creates an index of all names on one page in alphabetical order"""

   columns = Parameter(2, 'the number of columns for the listing')

   def register(self, processor):

      Page.register(self, processor)
      self.processor.add_root_page(self.filename(), 'Name Index', 'main', 1)

   def filename(self): return self.processor.file_layout.special('NameIndex')

   def title(self): return 'Synopsis - Name Index'

   def process(self, start):
      """Creates the page. It is created as a list of tables, one for each
      letter. The tables have a number of columns, which is 2 by default.
      _processItem is called for each item in the dictionary."""

      self.start_file()
      self.write(self.processor.navigation_bar(self.filename()))
      self.write(entity('h1', "Name Index"))
      self.write('<i>Hold the mouse over a link to see the scope of each name</i>')

      dict = self._makeDict()
      keys = dict.keys()
      keys.sort()
      linker = lambda key: '<a href="#%s">%s</a>'%(ord(key),key)
      self.write(div('nameindex-index', string.join(map(linker, keys))))
      for key in keys:
         self.write('<a name="%s">'%ord(key)+'</a>')
         self.write(entity('h2', key))
         self.write('<table border=0 width="100%" summary="table of names">')
         self.write('<col width="*">'*self.columns)
         self.write('<tr>')
         items = dict[key]
         numitems = len(items)
         start = 0
         for column in range(self.columns):
            end = numitems * (column + 1) / self.columns
            self.write('<td valign=top>')
            for item in items[start:end]:
               self._process_item(item)
            self.write('</td>')
            start = end
         self.write('</tr></table>')
	
      self.end_file()

   def _makeDict(self):
      """Returns a dictionary of items. The keys of the dictionary are the
      headings - the first letter of the name. The values are each a sorted
      list of items with that first letter."""

      decl_filter = lambda type: isinstance(type, Type.Declared)
      def name_cmp(a,b):
         a, b = a.name(), b.name()
         res = cmp(a[-1],b[-1])
         if res == 0: res = cmp(a,b)
         return res
      dict = {}
      def hasher(type, dict=dict):
         name = type.name()
         try: key = name[-1][0]
         except:
            print 'name:',name, 'type:',repr(type)
            raise
         if key >= 'a' and key <= 'z': key = chr(ord(key) - 32)
         if dict.has_key(key): dict[key].append(type)
         else: dict[key] = [type]
      # Fill the dict
      map(hasher, filter(decl_filter, self.processor.ast.types().values()))
      # Now sort the dict
      for items in dict.values():
         items.sort(name_cmp)
      return dict

   def _process_item(self, type):
      """Process the given name for output"""

      name = type.name()
      decl = type.declaration() # non-declared types are filtered out
      if isinstance(decl, AST.Function):
         realname = anglebrackets(decl.realname()[-1]) + '()'
      else:
         realname = anglebrackets(name[-1])
      self.write('\n')
      title = anglebrackets(string.join(name, '::'))
      type = decl.type()
      name = self.reference(name, (), realname, title=title)+' '+type
      self.write(div('nameindex-item', name))
