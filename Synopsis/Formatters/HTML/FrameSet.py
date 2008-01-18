#
# Copyright (C) 2006 Stefan Seefeld
# All rights reserved.
# Licensed to the public under the terms of the GNU LGPL (>= 2),
# see the file COPYING for details.
#

from Synopsis import Util
from Synopsis.Formatters.HTML.html import *
import os

class FrameSet:
    """A class that creates an index with frames"""

    def process(self, output, filename, title, index, detail, content):
        """Creates a frames index file."""

        out = Util.open(os.path.join(output, filename))
        out.write('<?xml version="1.0"?>\n')
        out.write('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Frameset//EN"\n')
        out.write('    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-frameset.dtd">\n')
        out.write('<html xmlns="http://www.w3.org/1999/xhtml" lang="en">\n')
        out.write('<head>\n')
        out.write('<meta content="text/html; charset=iso-8859-1" http-equiv="Content-Type"/>\n')
        out.write(element('title',title) + '\n')
        out.write(empty('link', type='text/css', rel='stylesheet', href='style.css') + '\n')
        out.write('</head>\n')
      
        index = rel(filename, index)
        detail = rel(filename, detail)
        content = rel(filename, content)
        frame1 = empty('frame', name='index', src=index)
        frame2 = empty('frame', name='detail', src=detail)
        frame3 = empty('frame', name='content', src=content)
        frameset = element('frameset', '%s\n%s\n'%(frame1, frame2), rows="30%,*")
        noframes = 'This document was configured to use frames.\n'
        noframes += '<ul>\n'
        noframes += element('li', href(index, 'The default Index frame')) + '\n'
        noframes += element('li', href(detail, 'The default Detail frame')) + '\n'
        noframes += element('li', href(content, 'The default Content frame')) + '\n'
        noframes += '</ul>\n'
        noframes = element('body', noframes + 'Generated by Synopsis.') + '\n'
        noframes = element('noframes', noframes)
        frameset = element('frameset', '%s\n%s\n%s\n'%(frameset, frame3, noframes), cols="200,*")
        out.write(frameset)
        out.write('\n</html>\n')
        out.close()