#
# Copyright (C) 2003 Stefan Seefeld
# All rights reserved.
# Licensed to the public under the terms of the GNU LGPL (>= 2),
# see the file COPYING for details.
#

import os, sys
from stat import *
import os.path
from shutil import *
import glob

from distutils.command import build
from distutils.spawn import spawn, find_executable
from distutils.dep_util import newer, newer_group
from distutils.dir_util import copy_tree, remove_tree, mkpath
from distutils.file_util import copy_file
from distutils import sysconfig

class build_doc(build.build):
   """Defines the specific procedure to build synopsis' documentation."""

   description = "build documentation"
   user_options = [('man-page', 'm', "build the man-pages only"),
                   ('ref-manual', 'r', "build the API reference manual only"),
                   ('tutorial', 't', "build the tutorial, development guide, and examples only"),
                   ('examples', 'e', "build examples only"),
                   ('html', 'h', "build for html output only"),
                   ('printable', 'p', "build for pdf output only"),
                   ('sxr=', 'x', "build the sxr database for synopsis for the given URL (requires -m)")]
   boolean_options = ['man-page', 'ref-manual', 'tutorial', 'examples', 'html', 'printable']

   def initialize_options(self):

      build.build.initialize_options(self)
      self.man_page = False
      self.ref_manual = False
      self.tutorial = False
      self.examples = False
      self.html = False
      self.printable = False
      self.sxr = ''

   def finalize_options(self):

      # If no option was given, do all media.
      if not (self.html or self.printable or self.sxr):
         self.html = True
      if not (self.man_page or self.ref_manual or self.tutorial or self.examples):
         self.tutorial = True
      build.build.finalize_options(self)

   def run(self):
      """Run this command, i.e. do the actual document generation."""

      if not os.path.exists(self.build_temp):
         self.run_command('config')

      self.build_lib = '.'

      rmtree('share/doc/synopsis/html', 1)

      if self.man_page: self.build_man_page()
      if self.ref_manual or self.sxr: self.build_ref_manual()
      if self.tutorial: self.build_tutorial()
      elif self.examples: self.build_examples()
    
   def build_man_page(self):
      """Build man pages for all installable programs."""
        
      self.announce("building man pages")

      descriptions = {}
      descriptions['synopsis'] = """simple frontend to the Synopsis framework, a multi-language source code introspection tool that
provides a variety of representations for the parsed code, to
enable further processing such as documentation extraction,
reverse engineering, and source-to-source translation."""
      
      descriptions['sxr-server'] = """the Synopsis Cross-Reference http server. Allows users
to query and browse cross-referenced source code."""
      

      help2man = find_executable('help2man')
      if not help2man:
         self.warn("cannot build man pages")
         return
      gzip = find_executable('gzip')

      section = 1
      man_dir = 'share/man/man%d'%section
      mkpath(man_dir, 0777, self.verbose, self.dry_run)

      for s in ['synopsis', 'sxr-server']:
         command = [help2man, '-N', '-n', descriptions[s]]
         executable = os.path.join('scripts', s)
         output = '%s/%s.%d'%(man_dir, s, section)
         command += ['-o', output, executable]
         spawn(command)
         if gzip:
            spawn(['gzip', '-f', output])


   def build_ref_manual(self):
      """Build the API reference manual."""
        
      self.announce("building API reference manual")

      tmp_man_dir = os.path.abspath(os.path.join(self.build_temp,
                                                 'doc/Manual'))

      make = os.environ.get('MAKE', 'make')

      srcdir = os.path.abspath('doc/Manual/')

      cwd = os.getcwd()
      mkpath(tmp_man_dir, 0777, self.verbose, self.dry_run)

      if self.html:
         spawn([make, '-C', tmp_man_dir, 'html'])
      if self.printable:
         spawn([make, '-C', tmp_man_dir, 'latexpdf'])
      if self.sxr:
         spawn([make, '-C', tmp_man_dir, 'sxr', 'sxr=%s'%self.sxr])

      builddir = os.path.abspath(os.path.join(self.build_lib,
                                              'share/doc/synopsis/html/Manual'))
      if self.html:
         src = os.path.join(tmp_man_dir, 'html', 'python')
         dest = os.path.join(builddir, 'python')

         if newer(src, dest):
            rmtree(dest, True)
            copy_tree(src, dest)

      if self.sxr:
         src = os.path.join(tmp_man_dir, 'html', 'sxr')
         builddir = os.path.abspath(os.path.join(self.build_lib,
                                                 'share/doc/synopsis/html/'))
         dest = os.path.join(builddir, 'SXR')

         if newer(src, dest):
            rmtree(dest, True)
            copy_tree(src, dest)

      if self.printable:
         builddir = os.path.abspath(os.path.join(self.build_lib,
                                                 'share/doc/synopsis/print'))
         mkpath(builddir, 0777, self.verbose, self.dry_run)
         copy_file(os.path.join(tmp_man_dir, 'Manual.pdf'),
                   os.path.join(builddir, 'Manual.pdf'))

   def build_tutorial(self):
      """Build the tutorial."""

      self.announce("building tutorial et al.")
      srcdir = os.path.abspath('doc')
      tempdir = os.path.abspath(os.path.join(self.build_temp, 'doc'))
      cwd = os.getcwd()
      #copy_tree(srcdir, tempdir, update=True, verbose=False)

      self.build_examples()

      # Copy examples sources into build tree.
      src = []
      def visit(arg, base, files):
         if '.svn' in files: del files[files.index('.svn')]
         arg.extend([os.path.join(base, f) for f in files
                     if os.path.isfile(os.path.join(base, f)) and
                     os.path.splitext(f)[1] in ('.rst', '.html', '.css', '.js', '.png', '.svg')])

      os.path.walk('doc', visit, src)
      for s in src:
         dirname = os.path.dirname(os.path.join(self.build_temp, s))
         mkpath(dirname, 0777, self.verbose, self.dry_run)
         copy_file(s, dirname)
      

      make = os.environ.get('MAKE', 'make')

      if self.html:
         spawn([make, '-C', tempdir, 'html'])
      if self.printable:
         spawn([make, '-C', tempdir, 'pdf'])

      builddir = os.path.abspath(os.path.join(self.build_lib,
                                              'share/doc/synopsis'))

      copy_tree(os.path.join(tempdir, 'html'),
                os.path.join(builddir, 'html'),
                verbose=False)

      if self.printable:
         builddir = os.path.abspath(os.path.join(self.build_lib,
                                                 'share/doc/synopsis/print'))
         mkpath(builddir, 0777, self.verbose, self.dry_run)
         copy_file(os.path.join(tempdir, 'Tutorial.pdf'),
                   os.path.join(builddir, 'Tutorial.pdf'))
         copy_file(os.path.join(tempdir, 'DevGuide.pdf'),
                   os.path.join(builddir, 'DevGuide.pdf'))
      

   def build_examples(self):

      self.announce("building examples")
      srcdir = os.path.abspath('doc/examples')
      tempdir = os.path.abspath(os.path.join(self.build_temp, 'doc/examples'))
      cwd = os.getcwd()
      mkpath(tempdir, int('777', 8), self.verbose, self.dry_run)

      # Copy examples sources into build tree.
      examples = []
      def visit(arg, base, files):
         if '.svn' in files: del files[files.index('.svn')]
         arg.extend([os.path.join(base, f) for f in files
                     if os.path.isfile(os.path.join(base, f))])

      os.path.walk('doc/examples', visit, examples)
      for e in examples:
         dirname = os.path.dirname(os.path.join(self.build_temp, e))
         mkpath(dirname, 0777, self.verbose, self.dry_run)
         copy_file(e, dirname)
      
      make = os.environ.get('MAKE', 'make')

      if self.html:
         builddir = os.path.abspath(os.path.join(self.build_lib,
                                                 'share/doc/synopsis/html/examples'))
         spawn([make, '-C', tempdir, 'install-html', 'prefix=%s'%builddir])


         ## Copy examples output into installation directory
         #if os.path.isdir(os.path.join(builddir, 'html/examples')):
         #   rmtree(os.path.join(builddir, 'html/examples'), 1)
         #copy_tree(os.path.join(tempdir, 'html/examples'),
         #          os.path.join(builddir, 'html/examples'))

      if self.printable:
         builddir = os.path.abspath(os.path.join(self.build_lib,
                                                 'share/doc/synopsis/print/examples'))
         spawn([make, '-C', tempdir, 'install-print', 'prefix=%s'%builddir])


         ## Copy examples output into installation directory
         #if os.path.isdir(os.path.join(builddir, 'print/examples')):
         #   rmtree(os.path.join(builddir, 'print/examples'), 1)
         #copy_tree(os.path.join(tempdir, 'print/examples'),
         #          os.path.join(builddir, 'print/examples'))

      # Copy examples sources into installation directory.
      builddir = os.path.abspath(os.path.join(self.build_lib,
                                              'share/doc/synopsis/examples'))
      spawn([make, '-C', tempdir, 'install-src', 'prefix=%s'%builddir])

      
