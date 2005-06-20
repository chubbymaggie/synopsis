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

import os, os.path, tempfile

class Parser(Processor):

   preprocess = Parameter(True, 'whether or not to preprocess the input')
   emulate_compiler = Parameter('', 'a compiler to emulate')
   cppflags = Parameter([], 'list of preprocessor flags such as -I or -D')
   main_file_only = Parameter(True, 'should only main file be processed')
   base_path = Parameter('', 'path prefix to strip off of the file names')
   syntax_prefix = Parameter(None, 'path prefix (directory) to contain syntax info')
   xref_prefix = Parameter(None, 'path prefix (directory) to contain xref info')

   def process(self, ast, **kwds):

      self.set_parameters(kwds)
      self.ast = ast

      if self.preprocess:

         from Synopsis.Parsers import Cpp
         cpp = Cpp.Parser(base_path = self.base_path,
                          language = 'C++',
                          flags = self.cppflags,
                          emulate_compiler = self.emulate_compiler)




      for file in self.input:

         ii_file = file
         if self.preprocess:

            if self.output:
               ii_file = os.path.splitext(self.output)[0] + '.ii'
            else:
               ii_file = os.path.join(tempfile.gettempdir(),
                                      'synopsis-%s.ii'%os.getpid())
            self.ast = cpp.process(self.ast,
                                   cpp_output = ii_file,
                                   input = [file],
                                   main_file_only = self.main_file_only,
                                   verbose = self.verbose,
                                   debug = self.debug,
                                   profile = self.profile)

         self.ast = occ.parse(self.ast, ii_file,
                              os.path.abspath(file),
                              self.main_file_only,
                              os.path.abspath(self.base_path) + os.sep,
                              self.syntax_prefix,
                              self.xref_prefix,
                              self.verbose,
                              self.debug,
                              self.profile)

         if self.preprocess: os.remove(ii_file)

      return self.output_and_return_ast()

   def dump(self, **kwds):
      """Run the occ directly without ast intervention."""

      input = kwds.get('input', self.input)
      verbose = kwds.get('verbose', self.verbose)
      debug = kwds.get('debug', self.debug)

      for file in input:
         occ.dump(file, verbose, debug)
