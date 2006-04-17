#
# Copyright (C) 2000 Stephen Davies
# Copyright (C) 2000 Stefan Seefeld
# All rights reserved.
# Licensed to the public under the terms of the GNU LGPL (>= 2),
# see the file COPYING for details.
#

from Synopsis.Processor import Parameter
from Synopsis import AST, Util
from Synopsis.Formatters.HTML.View import View
from Synopsis.Formatters.HTML.Tags import *

import os

class FileIndexer(View):
   """A view that creates an index of files, and an index for each file.
   First the index of files is created, intended for the top-left frame.
   Second a view is created for each file, listing the major declarations for
   that file, eg: classes, global functions, namespaces, etc."""

   def register(self, processor):

      View.register(self, processor)
      self.__filename = ''
      self.__title = ''
      self.__link_source = processor.has_view('Source')
      self.__link_details = processor.has_view('FileDetails')

   def filename(self):
      """since FileTree generates a whole file hierarchy, this method returns the current filename,
      which may change over the lifetime of this object"""

      return self.__filename

   def title(self):
      """since FileTree generates a while file hierarchy, this method returns the current title,
      which may change over the lifetime of this object"""

      return self.__title
   
   def register_filenames(self, start):
      """Registers a view for each file indexed"""

      for filename, file in self.processor.ast.files().items():
         if file.annotations['primary']:
            filename = self.processor.file_layout.file_index(filename)
            self.processor.register_filename(filename, self, file)
    
   def process(self, start):
      """Creates a view for each file using process_scope"""

      for filename, file in self.processor.ast.files().items():
         if file.annotations['primary']:
            self.process_scope(filename, file)

   def process_scope(self, filename, file):
      """Creates a view for the given file. The view is just an index,
      containing a list of declarations."""

      # set up filename and title for the current view
      self.__filename = self.processor.file_layout.file_index(filename)
      # (get rid of ../'s in the filename)
      name = string.split(filename, os.sep)
      while len(name) and name[0] == '..': del name[0]
      self.__title = string.join(name, os.sep)

      self.start_file()
      self.write(entity('b', string.join(name, os.sep))+'<br/>')
      if self.__link_source:
         link = rel(self.filename(),
                    self.processor.file_layout.file_source(filename))
         self.write(href(link, '[File Source]', target="main")+'<br/>')
      if self.__link_details:
         link = rel(self.filename(),
                    self.processor.file_layout.file_details(filename))
         self.write(href(link, '[File Details]', target="main")+'<br/>')
      doc = self.processor.documentation

      self.write('<b>Declarations:</b><br/>')
      # Sort items (by name)
      items = [(d.name(), d) for d in file.declarations]
      items.sort()
      scope, last = [], []
      for name, decl in items:
         # TODO make this nicer :)
         entry = self.processor.toc[name]
         if not entry: continue
         summary = string.strip("(%s) %s"%(decl.type(), doc.summary(decl, self)))
         # Print link to declaration's view
         link = rel(self.filename(), entry.link)
         if isinstance(decl, AST.Function): print_name = decl.realname()
         else: print_name = name
         # Increase scope
         i = 0
         while i < len(print_name)-1 and i < len(scope) and print_name[i] == scope[i]:
            i = i + 1
         # Remove unneeded indentation
         j = i
         while j < len(scope):
            self.write("</div>")
            j = j + 1
         # Add new indentation
         scope[i:j] = []
         while i < len(print_name)-1:
            scope.append(print_name[i])
            if len(last) >= len(scope) and last[:len(scope)] == scope: div_bit = ""
            else: div_bit = print_name[i]+"<br/>"
            self.write('%s<div class="fileview-scope">'%div_bit)
            i = i + 1

         # Now print the actual item
         label = escape(Util.ccolonName(print_name, scope))
         label = replace_spaces(label)
         self.write(div('href',href(link, label, target='main', title=summary)))
         # Store this name incase, f.ex, its a class and the next item is
         # in that class scope
         last = list(name)
      # Close open DIVs
      for i in scope:
         self.write("</div>")
      self.end_file()
