#
# Copyright (C) 2000 Stephen Davies
# Copyright (C) 2000 Stefan Seefeld
# All rights reserved.
# Licensed to the public under the terms of the GNU LGPL (>= 2),
# see the file COPYING for details.
#

from Synopsis.Processor import Parameter
from Synopsis.Formatters.HTML.Part import Part
from Synopsis.Formatters.HTML.Fragments import *
from Synopsis.Formatters.HTML.Tags import *

class Detail(Part):

    fragments = Parameter([DeclarationDetailFormatter(), DetailCommenter()],
                         '')

    def write_section_start(self, heading):
        """Start a 'detail' section and write an appropriate heading."""

        self.write('<div class="detail">\n')
        self.write('<div class="heading">%s</div>\n'%heading)

    def write_section_end(self, heading):
        """Close the section."""
        
        self.write('</div><!-- detail -->\n')
        
    def write_section_item(self, text):
        """Add an item."""

        self.write('<div class="item">%s</div>\n'%text)

    def process(self, decl):
        "Print out the details for the children of the given decl"

        doc = self.processor.documentation
        sorter = self.processor.sorter
        sorter.set_scope(decl)
        sorter.sort_section_names()

        # Iterate through the sections with details
        self.write_start()
        for section in sorter.sections():
            # Write a heading
            heading = section+' Details:'
            started = 0 # Lazy section start incase no details for this section
            # Iterate through the children in this section
            for child in sorter.children(section):
                # Check if need to add to detail list
                if not doc.details(child, self.view()):
                    continue
                # Check section heading
                if not started:
                    started = 1
                    self.write_section_start(heading)
                child.accept(self)
            # Finish the section
            if started: self.write_section_end(heading)
        self.write_end()
