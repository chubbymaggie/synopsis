# $Id: Summary.py,v 1.1 2003/11/15 19:54:05 stefan Exp $
#
# Copyright (C) 2000 Stephen Davies
# Copyright (C) 2000 Stefan Seefeld
# All rights reserved.
# Licensed to the public under the terms of the GNU LGPL (>= 2),
# see the file COPYING for details.
#

from Synopsis.Formatters.HTML.Part import Part

from Synopsis.Formatters.HTML import FormatStrategy
from from Synopsis.Formatters.HTML.Tags import *

class Summary(Part):
   """Formatting summary visitor. This formatter displays a summary for each
   declaration, with links to the details if there is one. All of this is
   controlled by the ASTFormatters."""

   def register(self, page):

      Part.register(self, page)
      self.__link_detail = 0
      self._init_formatters('summary_formatters', 'summary')

   def _init_default_formatters(self):

      self.addFormatter( FormatStrategy.SummaryAST )
      self.addFormatter( FormatStrategy.SummaryCommenter )

   def set_link_detail(self, boolean):
      """Sets link_detail flag to given value.
      @see label()"""

      self.__link_detail = boolean
      config.link_detail = boolean

   def label(self, ref, label=None):
      """Override to check link_detail flag. If it's set, returns a reference
      instead - which will be to the detailed info"""

      if label is None: label = ref
      if self.__link_detail:
         # Insert a reference instead
         return span('name',self.reference(ref, Util.ccolonName(label, self.scope())))
      return Part.label(self, ref, label)
	
   def writeSectionStart(self, heading):
      """Starts a table entity. The heading is placed in a row in a td with
      the class 'heading'."""

      self.write('<table width="100%%" summary="%s">\n'%heading)
      self.write('<col><col width="100%%">')
      self.write('<tr><td class="heading" colspan="2">' + heading + '</td></tr>\n')

   def writeSectionEnd(self, heading):
      """Closes the table entity and adds a break."""

      self.write('</table>\n<br>\n')

   def writeSectionItem(self, text):
      """Adds a table row"""

      if text[:22] == '<td class="summ-start"':
         # text provided its own TD element
         self.write('<tr>' + text + '</td></tr>\n')
      else:
         self.write('<tr><td class="summ-start">' + text + '</td></tr>\n')

   def process(self, decl):
      "Print out the summaries from the given decl"

      decl_style = config.decl_style
      SUMMARY = DeclStyle.SUMMARY
      config.link_detail = 0
	
      config.sorter.set_scope(decl)
      config.sorter.sort_section_names()

      self.write_start()
      for section in config.sorter.sections():
         # Write a header for this section
         if section[-1] == 's': heading = section+'es Summary:'
         else: heading = section+'s Summary:'
         self.writeSectionStart(heading)
         # Iterate through the children in this section
         for child in config.sorter.children(section):
            # Check if need to add to detail list
            if decl_style[child] != SUMMARY:
               # Setup the linking stuff
               self.set_link_detail(1)
               child.accept(self)
               self.set_link_detail(0)
            else:
               # Just do it
               child.accept(self)
         # Finish off this section
         self.writeSectionEnd(heading)
      self.write_end()

