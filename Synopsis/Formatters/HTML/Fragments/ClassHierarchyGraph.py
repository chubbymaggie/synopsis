#
# Copyright (C) 2000 Stephen Davies
# Copyright (C) 2000 Stefan Seefeld
# All rights reserved.
# Licensed to the public under the terms of the GNU LGPL (>= 2),
# see the file COPYING for details.
#

from Synopsis import AST, Type
from ClassHierarchySimple import ClassHierarchySimple
import os, string

class ClassHierarchyGraph(ClassHierarchySimple):
   """Prints a graphical hierarchy for classes, using the Dot formatter.
   
   @see Formatters.Dot
   """
   def format_class(self, clas):
      try:
         import tempfile
         from Synopsis.Formatters import Dot
      except:
         print "HierarchyGraph: Dot not found"
         return ""
      super = self.processor.class_tree.superclasses(clas.name())
      sub = self.processor.class_tree.subclasses(clas.name())
      if len(super) == 0 and len(sub) == 0:
         # Skip classes with a boring graph
         return ''
      #label = self.processor.files.scoped_special('inheritance', clas.name())
      label = self.formatter.filename()[:-5] + '-inheritance.html'
      tmp = os.path.join(self.processor.output, label)
      ast = AST.AST({}, [clas], self.processor.ast.types())
      dot = Dot.Formatter()
      dot.toc = self.processor.toc
      dot.process(ast,
                  output=tmp,
                  format='html',
                  base_url=self.formatter.filename(),
                  type='single',
                  title=label)
      text = ''
      input = open(tmp, "r+")
      line = input.readline()
      while line:
         text = text + line
         line = input.readline()
      input.close()
      os.unlink(tmp)
      return text

