# $Id: SourceLinker.py,v 1.2 2003/12/08 00:39:24 stefan Exp $
#
# Copyright (C) 2000 Stephen Davies
# Copyright (C) 2000 Stefan Seefeld
# All rights reserved.
# Licensed to the public under the terms of the GNU LGPL (>= 2),
# see the file COPYING for details.
#

from Synopsis.Formatters.HTML.Tags import *
from Default import Default

class SourceLinker(Default):
   """Adds a link to the decl on the file view to all declarations"""

   def format_declaration(self, decl):

      if not decl.file(): return ''
      filename = self.processor.file_layout.file_source(decl.file().filename())
      line = decl.line()
      link = filename + "#%d" % line
      return href(rel(self.formatter.filename(), link), "[Source]")
