#
# Copyright (C) 2006 Stefan Seefeld
# All rights reserved.
# Licensed to the public under the terms of the GNU GPL (>= 2),
# see the file COPYING for details.
#

from Synopsis.Processor import *
from Synopsis import AST, Type
from Synopsis.SourceFile import SourceFile
from Synopsis.DocString import DocString
from ASTTranslator import ASTTranslator
import os

__all__ = ['Parser']

class Parser(Processor):
    """Python Parser. See http://www.python.org/dev/peps/pep-0258 for additional
    info."""

    base_path = Parameter('', 'Path prefix to strip off of input file names.')
    syntax_prefix = Parameter(None, 'Path prefix (directory) to contain syntax info.')
    
    def process(self, ast, **kwds):

        self.set_parameters(kwds)
        self.ast = ast
        self.scopes = []
      
        # Create return type for Python functions:
        self.return_type = Type.Base('Python',('',))

        # Validate base_path.
        if self.base_path:
            if not os.path.isdir(self.base_path):
                raise InvalidArgument('base_path: "%s" not a directory.'
                                      %self.base_path)
            if self.base_path[-1] != os.sep:
                self.base_path += os.sep
            
        for file in self.input:
            self.process_file(file)

        return self.output_and_return_ast()


    def process_file(self, filename):
        """Parse an individual python file."""

        short_filename = filename
        if filename[:len(self.base_path)] != self.base_path:
            raise InvalidArguent('invalid input filename:\n'
                                 '"%" does not match base_path "%s"'
                                 %(filename, self.base_path))

        short_filename = filename[len(self.base_path):]
        sourcefile = SourceFile(short_filename, filename, 'Python')
        sourcefile.annotations['primary'] = True
        self.ast.files()[short_filename] = sourcefile

        package = None
        package_name = []
        package_path = self.base_path
        # Only attempt to set up enclosing packages if a base_path was given.
        if package_path:
            components = short_filename.split(os.sep)
            if components[0] == '':
                package_path += os.sep
                components = components[1:]
            for c in components[:-1]:
                package_name.append(c)
                package_path = os.path.join(package_path, c)
                if not os.path.isfile(os.path.join(package_path, '__init__.py')):
                    raise InvalidArgument('"%s" is not a package'
                                          %''.join(package_name))
                module = AST.Module(sourcefile, -1, 'package', package_name)
                if package:
                    package.declarations().append(module)
                else:
                    self.ast.declarations().append(module)

                package = module

        basename = os.path.basename(filename)
        if basename == '__init__.py':
            if package:
                module = package
            else:
                dirname = os.path.dirname(filename)
                module_name = os.path.splitext(os.path.basename(dirname))[0]
                module = AST.Module(sourcefile, -1, 'package', [module_name])
                self.ast.declarations().append(module)
        else:
            module_name = os.path.splitext(basename)[0]
            if package:
                module = AST.Module(sourcefile, -1, 'module',
                                    package_name + [module_name])
                package.declarations().append(module)
            else:
                module = AST.Module(sourcefile, -1, 'module', [module_name])
                self.ast.declarations().append(module)

        translator = ASTTranslator(module, self.ast.types())
        if self.syntax_prefix is None:
            xref = None
        else:
            xref = os.path.join(self.syntax_prefix, short_filename + '.sxr')
            dirname = os.path.dirname(xref)
            if not os.path.exists(dirname):
                os.makedirs(dirname, 0755)
        translator.process_file(filename, xref)
        sourcefile.declarations.extend(module.declarations())
