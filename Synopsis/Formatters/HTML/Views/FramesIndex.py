# $Id: FramesIndex.py,v 1.10 2003/11/14 14:51:09 stefan Exp $
#
# Copyright (C) 2000 Stephen Davies
# Copyright (C) 2000 Stefan Seefeld
# All rights reserved.
# Licensed to the public under the terms of the GNU LGPL (>= 2),
# see the file COPYING for details.
#

from Synopsis.Formatters.HTML.Page import Page
from Synopsis.Formatters.HTML.core import config
from Synopsis.Formatters.HTML.Tags import *

import os

class FramesIndex(Page):
   """A class that creates an index with frames"""

   def register(self, processor):

      Page.register(self, processor)
      config.set_main_page(self.filename())

   def filename(self): return self.processor.file_layout.nameOfIndex()

   def title(self): return 'Synopsis - Generated Documentation'

   def process(self, start):
      """Creates a frames index file"""

      me = self.filename()
      # TODO use project name..
      self.start_file(body='')
      fcontents = rel(me, config.page_contents)
      findex = rel(me, config.page_index)
      # Find something to link to
      fglobal = findex
      decls = [start]
      while decls:
         decl = decls.pop(0)
         entry = self.processor.toc[decl.name()]
         if entry:
            fglobal = rel(me, entry.link)
            break
         if hasattr(decl, 'declarations'):
            # Depth-first search
            decls = decl.declarations() + decls
      frame1 = solotag('frame', name='contents', src=fcontents)
      frame2 = solotag('frame', name='index', src=findex)
      frame3 = solotag('frame', name='main', src=fglobal)
      frameset1 = entity('frameset', frame1+frame2, rows="30%,*")
      frameset2 = entity('frameset', frameset1+frame3, cols="200,*")
      self.write(frameset2)
      noframes = 'This document was configured to use frames.'
      noframes = noframes + '<ul>'
      noframes = noframes + entity('li', href(fcontents, 'The default Contents frame'))
      noframes = noframes + entity('li', href(findex, 'The default Index frame'))
      noframes = noframes + entity('li', href(fglobal, 'The default Main frame'))
      noframes = noframes + '</ul>'
      noframes = noframes + 'Generated by Synopsis.'
      self.write(entity('noframes', noframes))
      self.end_file(body='')
