# $Id: Formatter.py,v 1.9 2003/11/16 21:09:45 stefan Exp $
#
# Copyright (C) 2003 Stefan Seefeld
# All rights reserved.
# Licensed to the public under the terms of the GNU LGPL (>= 2),
# see the file COPYING for details.
#

from Synopsis import config
from Synopsis.Processor import Processor, Parameter
from Synopsis import AST
from Synopsis.Formatters.TOC import TOC
from Synopsis.Formatters.ClassTree import ClassTree
from Synopsis.Formatters.XRef import CrossReferencer
from FileLayout import *
from TreeFormatter import *
from CommentFormatter import *
from DeclarationStyle import *
from Pages.FramesIndex import *
from Pages.DirBrowse import *
from Pages.Scope import *
from Pages.ModuleListing import *
from Pages.ModuleListingJS import *
from Pages.ModuleIndexer import *
from Pages.FileListing import *
from Pages.FileIndexer import *
from Pages.FileDetails import *
from Pages.InheritanceTree import *
from Pages.InheritanceGraph import *
from Pages.FileSource import *
from Pages.NameIndex import *
from Pages.XRef import *
import Tags

class Struct:
   "Dummy class. Initialise with keyword args."
   def __init__(self, **keys):
      for name, value in keys.items(): setattr(self, name, value)

class Formatter(Processor):

   stylesheet = Parameter('style.css', '')
   stylesheet_file = Parameter('../html.css', '')
   datadir = Parameter('', 'alternative data directory')
   file_layout = Parameter(FileLayout(), 'how to lay out the output files')
   toc_in = Parameter([], 'list of table of content files to use for symbol lookup')
   toc_out = Parameter('', 'name of file into which to store the TOC')

   pages = Parameter([FramesIndex(),#FramesIndex(), #DirBrowse()
                      Scope(),
                      ModuleListing(),
                      ModuleIndexer(),
                      FileListing(),
                      FileIndexer(),
                      FileDetails(),
                      InheritanceTree(),
                      InheritanceGraph(),
                      FileSource(),
                      NameIndex(),
                      XRef()],
                      '')
   
   #comment_formatters = ['javadoc', 'section']
   comment_formatters = Parameter([QuoteHTML(),
                                   SectionFormatter()],
                                  '')
   
   tree_formatter = Parameter(TreeFormatter(), 'define how to lay out tree views')
   structs_as_classes = Parameter(True, '')

   def process(self, ast, **kwds):

      self.set_parameters(kwds)
      self.ast = self.merge_input(ast)

      # if not set, use default...
      if not self.datadir: self.datadir = config.datadir

      self.file_layout.init(self)
      self.decl_style = Style()
      for f in self.comment_formatters:
         f.init(self)
      self.comments = CommentFormatter(self)
      # Create the Class Tree (TODO: only if needed...)
      self.class_tree = ClassTree()
      # Create the File Tree (TODO: only if needed...)
      self.file_tree = FileTree()
      self.file_tree.set_ast(ast)

      self.xref = CrossReferencer()

      #if not self.sorter:
      import ScopeSorter
      self.sorter = ScopeSorter.ScopeSorter()


      Tags.using_frames = self.has_page('FramesIndex')

      self.main_page = None
      self.contents_page = None
      self.index_page = None
      self.using_module_index = False
      
      declarations = ast.declarations()

      # Build class tree
      for d in declarations:
         d.accept(self.class_tree)

      self.__roots = [] #pages with roots, list of Structs
      self.__global = None # The global scope
      self.__files = {} # map from filename to (page,scope)

      for p in self.pages:
         p.register(self)

      root = AST.Module(None,-1,"C++","Global",())
      root.declarations()[:] = declarations

      # Create table of contents index
      start = self.calculate_start(root)
      self.toc = self.get_toc(start)
      if self.verbose: print "HTML Formatter: Initialising TOC"

      # Add all declarations to the namespace tree
      # for d in declarations:
      #	d.accept(self.toc)
	
      if self.verbose: print "TOC size:",self.toc.size()
      if self.toc_out: self.toc.store(self.toc_out)
    
      # load external references from toc files, if any
      for t in self.toc_in: self.toc.load(t)
   
      if self.verbose: print "HTML Formatter: Writing Pages..."

      # Create the pages
      self.__global = root
      start = self.calculate_start(root)
      if self.verbose: print "Registering filenames...",
      for page in self.pages:
         page.register_filenames(start)
      if self.verbose: print "Done."
      for page in self.pages:
         if self.verbose:
            print "Time for %s:"%page.__class__.__name__,
            sys.stdout.flush()
            start_time = time.time()
         page.process(start)
         if self.verbose:
            print "%f"%(time.time() - start_time)

      return self.ast

   def has_page(self, page_name):
      """test whether the given page is part of the pages list."""

      return reduce(lambda x, y: x or y,
                    map(lambda x: x.__class__.__name__ == page_name,
                        self.pages))

   def get_toc(self, start):
      """Returns the table of content to link into from the outside"""

      ### FIXME : how should this work ?
      ### We need to point to one of the pages...
      return self.pages[1].get_toc(start)

   def set_main_page(self, page):
      """Call this method to set the main index.html page. First come first served
      -- whatever module the user puts first in the list that sets this is
      it."""

      if not self.main_page:
         self.main_page = page

   def set_contents_page(self, page):
      """Call this method to set the contents page. First come first served
      -- whatever module the user puts first in the list that sets this is
      it. This is the frame in the top-left if you use the default frameset."""

      if not self.contents_page: self.contents_page = page
    
   def set_index_page(self, page):
      """Call this method to set the index page. First come first served
      -- whatever module the user puts first in the list that sets this is
      it. This is the frame on the left if you use the default frameset."""

      if not self.index_page: self.index_page = page

   def set_using_module_index(self):
      """Sets the using_module_index flag. This will cause the an
      intermediate level of links intended to go in the left frame."""
      self.using_module_index = True

   def global_scope(self):
      "Return the global scope"

      return self.__global

   def calculate_start(self, root, namespace=None):
      "Calculates the start scope using the 'namespace' config var"

      scope_names = string.split(namespace or config.namespace, "::")
      start = root # The running result
      self.sorter.set_scope(root)
      scope = [] # The running name of the start
      for scope_name in scope_names:
         if not scope_name: break
         scope.append(scope_name)
         try:
            child = self.sorter.child(tuple(scope))
            if isinstance(child, AST.Scope):
               start = child
               self.sorter.set_scope(start)
            else:
               raise TypeError, 'calculate_start: Not a Scope'
         except:
            # Don't continue if scope traversal failed!
            import traceback
            traceback.print_exc()
            print "Fatal: Couldn't find child scope",scope
            print "Children:",map(lambda x:x.name(), self.sorter.children())
            sys.exit(3)
      return start

   def add_root_page(self, file, label, target, visibility):
      """Adds a named link to the list of root pages. Called from the
      constructors of Page objects. The root pages are displayed at the top
      of every page, depending on their visibility (higher = more visible).
      @param file	    the filename, to be used when generating the link
      @param label	    the label of the page
      @param target       target frame
      @param visibility   should be a number such as 1 or 2. Visibility 2 is
      shown on all pages, 1 only on pages with lots of
      room. For example, pages for the top-left frame
      only show visibility 2 pages."""

      self.__roots.append(Struct(file=file, label=label, target=target, visibility=visibility))

   def navigation_bar(self, origin, visibility=1):
      """Formats the list of root pages to HTML. The origin specifies the
      generated page itself (which shouldn't be linked), such that the relative
      links can be generated. Only root pages of 'visibility' or
      above are included."""

      # If not using frames, show all headings on all pages!
      if not self.has_page('FramesIndex'):
         visibility = 1
      #filter out roots that are visible
      roots = filter(lambda x,v=visibility: x.visibility >= v, self.__roots)
      #a function generating a link
      other = lambda x, o=origin, span=span: span('root-other', href(rel(o, x.file), x.label, target=x.target))
      #a function simply printing label
      current = lambda x, span=span: span('root-current', x.label)
      # generate the header
      roots = map(lambda x, o=origin, other=other, current=current: x.file==o and current(x) or other(x), roots)
      return string.join(roots, ' | \n')+'\n<hr>\n'

   def register_filename(self, filename, page, scope):
      """Registers a file for later production. The first page to register
      the filename gets to keep it."""

      filename = str(filename)
      if not self.__files.has_key(filename):
         self.__files[filename] = (page, scope)

   def filename_info(self, filename):
      """Returns information about a registered file, as a (page,scope)
      pair. Will return None if the filename isn't registered."""

      filename = str(filename)
      if not self.__files.has_key(filename): return None
      return self.__files[filename]

