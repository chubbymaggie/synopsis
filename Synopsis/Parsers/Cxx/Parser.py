# $Id: Parser.py,v 1.6 2003/12/03 03:43:26 stefan Exp $
#
# Copyright (C) 2003 Stefan Seefeld
# All rights reserved.
# Licensed to the public under the terms of the GNU LGPL (>= 2),
# see the file COPYING for details.
#

"""Parser for C++ using OpenC++ for low-level parsing.
This parser is written entirely in C++, and compiled into shared libraries for
use by python.
@see C++/Synopsis
@see C++/SWalker
"""

from Synopsis.Processor import Processor, Parameter
from Synopsis import AST
import occ

class Parser(Processor):

   preprocessor = Parameter(None, 'the preprocessor to use (defaults to internal)')
   emulate_compiler = Parameter('c++', 'a compiler to emulate (defaults to \'c++\')')
   cppflags = Parameter([], 'list of preprocessor flags such as -I or -D')
   main_file_only = Parameter(True, 'should only main file be processed')
   base_path = Parameter('', 'path prefix to strip off of the file names')
   syntax_prefix = Parameter(None, 'path prefix (directory) to contain syntax info')
   xref_prefix = Parameter(None, 'path prefix (directory) to contain xref info')

   extra_files = Parameter([], 'extra files for which to keep info. Highly Deprecated !!!')
   
   def process(self, ast, **kwds):

      input = kwds.get('input')
      self.set_parameters(kwds)
      self.ast = ast
      for file in input:
         self.ast = occ.parse(self.ast, file,
                              self.extra_files,
                              self.verbose,
                              self.main_file_only,
                              self.base_path,
                              self.preprocessor,
                              self.cppflags,
                              self.syntax_prefix,
                              self.xref_prefix,
                              self.emulate_compiler)

      return self.output_and_return_ast()
