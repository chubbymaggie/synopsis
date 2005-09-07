#
# Copyright (C) 2003 Stefan Seefeld
# All rights reserved.
# Licensed to the public under the terms of the GNU LGPL (>= 2),
# see the file COPYING for details.
#

"""Preprocessor for C, C++, IDL
"""

from Synopsis.Processor import Processor, Parameter
from Synopsis import AST
from Emulator import get_compiler_info
import ucpp

import os.path

class Parser(Processor):

   emulate_compiler = Parameter('', 'a compiler to emulate')
   flags = Parameter([], 'list of preprocessor flags such as -I or -D')
   main_file_only = Parameter(True, 'should only main file be processed')
   cpp_output = Parameter(None, 'filename for preprocessed file')
   base_path = Parameter(None, 'path prefix to strip off of the filenames')
   language = Parameter('C++', 'source code programming language of the given input file')
   experimental = Parameter(False, 'True if the new (and experimental) wave backend is to be used.')

   def process(self, ast, **kwds):
      global ucpp

      self.set_parameters(kwds)
      self.ast = ast

      parse = ucpp.parse
      if self.experimental:
         # replace the already loaded backend by wave
         try:
            import ParserImpl
            parse = ParserImpl.parse
         except:
            print 'Warning: unable to load wave backend !'
      
      flags = self.flags
      base_path = self.base_path and os.path.abspath(self.base_path) + os.sep or ''
      info = get_compiler_info(self.language, self.emulate_compiler)
      flags += map(lambda x:'-I%s'%x, info.include_paths)
      flags += map(lambda x:'-D%s=%s'%(x[0], x[1]), info.macros)
      for file in self.input:
         self.ast = parse(self.ast,
                          os.path.abspath(file),
                          base_path,
                          self.cpp_output,
                          self.language, flags, self.main_file_only,
                          self.verbose, self.debug)
      return self.output_and_return_ast()

