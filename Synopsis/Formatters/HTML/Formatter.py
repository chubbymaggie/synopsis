#
# Copyright (C) 2003 Stefan Seefeld
# All rights reserved.
# Licensed to the public under the terms of the GNU LGPL (>= 2),
# see the file COPYING for details.
#

from Synopsis import config
from Synopsis.Processor import Processor, Parameter
from Synopsis import AST
from Synopsis.DocString import DocString
from Synopsis.FileTree import FileTree
from Synopsis.Formatters.TOC import TOC
from Synopsis.Formatters.ClassTree import ClassTree
from Synopsis.Formatters.XRef import CrossReferencer
from FileLayout import *
from TreeFormatter import *
from Views import *
from Synopsis.Formatters.HTML.Markup.Javadoc import Javadoc
try:
   from Synopsis.Formatters.HTML.Markup.RST import RST
except ImportError:
   from Synopsis.Formatters.HTML.Markup import Formatter as RST
import Markup
import Tags

import time

class Struct:
   "Dummy class. Initialise with keyword args."
   def __init__(self, **keys):
      for name, value in keys.items(): setattr(self, name, value)

class DocCache:
   """"""

   def __init__(self, processor, markup_formatters):

      self._processor = processor
      self._markup_formatters = markup_formatters
      # Make sure we have a default markup formatter.
      if '' not in self._markup_formatters:
         self._markup_formatters[''] = Markup.Formatter()
      for f in self._markup_formatters.values():
         f.init(self._processor)
      self._doc_cache = {}


   def _process(self, decl, view):
      """Return the documentation for the given declaration."""

      key = id(decl)
      if key not in self._doc_cache:
         doc = decl.annotations.get('doc')
         if doc:
            formatter = self._markup_formatters.get(doc.markup,
                                                    self._markup_formatters[''])
            doc = formatter.format(decl, view)
         else:
            doc = Markup.Struct()
         # FIXME: Unfortunately we can't easily cache these, as they may
         #        contain relative URLs that aren't valid across views.
         #self._doc_cache[key] = doc
         return doc
      else:
         return self._doc_cache[key]


   def summary(self, decl, view):
      """"""

      doc = self._process(decl, view)
      return doc.summary


   def details(self, decl, view):
      """"""

      doc = self._process(decl, view)
      return doc.details


class Formatter(Processor):

   title = Parameter('Synopsis - Generated Documentation', 'title to put into html header')
   stylesheet = Parameter(os.path.join(config.datadir, 'html.css'), 'stylesheet to be used')
   datadir = Parameter('', 'alternative data directory')
   file_layout = Parameter(NestedFileLayout(), 'how to lay out the output files')
   toc_in = Parameter([], 'list of table of content files to use for symbol lookup')
   toc_out = Parameter('', 'name of file into which to store the TOC')

   views = Parameter([FramesIndex(),
                      Scope(),
                      ModuleListing(),
                      ModuleIndexer(),
                      FileListing(),
                      FileIndexer(),
                      FileDetails(),
                      InheritanceTree(),
                      InheritanceGraph(),
                      NameIndex()],
                      '')
   
   markup_formatters = Parameter({'javadoc':Javadoc(), 'rst':RST()},
                                 'Markup-specific formatters.')
   tree_formatter = Parameter(TreeFormatter(), 'Define how to lay out tree views.')

   def process(self, ast, **kwds):

      self.set_parameters(kwds)
      self.ast = self.merge_input(ast)

      # if not set, use default...
      if not self.datadir: self.datadir = config.datadir

      self.file_layout.init(self)
      self.documentation = DocCache(self, self.markup_formatters)
      # Create the Class Tree (TODO: only if needed...)
      self.class_tree = ClassTree()
      # Create the File Tree (TODO: only if needed...)
      self.file_tree = FileTree()
      self.file_tree.set_ast(self.ast)

      self.xref = CrossReferencer()

      #if not self.sorter:
      import ScopeSorter
      self.sorter = ScopeSorter.ScopeSorter()


      Tags.using_frames = self.has_view('FramesIndex')

      self.main_view = None
      self.contents_view = None
      self.index_view = None
      self.using_module_index = False
      
      declarations = self.ast.declarations()

      # Build class tree
      for d in declarations:
         d.accept(self.class_tree)

      self.__roots = [] #views with roots, list of Structs
      self.__global = None # The global scope
      self.__files = {} # map from filename to (view,scope)

      for view in self.views:
         view.register(self)

      root = AST.Module(None,-1,"Global",())
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
   
      if self.verbose: print "HTML Formatter: Generating views..."

      # Create the views
      self.__global = root
      start = self.calculate_start(root)
      if self.verbose: print "Registering filenames...",
      for view in self.views:
         view.register_filenames(start)
      if self.verbose: print "Done."
      for view in self.views:
         if self.profile:
            print "Time for %s:"%view.__class__.__name__,
            sys.stdout.flush()
            start_time = time.time()
         view.process(start)
         if self.profile:
            print "%f seconds"%(time.time() - start_time)

      return self.ast

   def has_view(self, name):
      """test whether the given view is part of the views list."""

      return reduce(lambda x, y: x or y,
                    map(lambda x: x.__class__.__name__ == name, self.views))

   def get_toc(self, start):
      """Returns the table of content to link into from the outside"""

      ### FIXME : how should this work ?
      ### We need to point to one of the views...
      return self.views[1].get_toc(start)

   def set_main_view(self, view):
      """Call this method to set the main index.html view. First come first served
      -- whatever module the user puts first in the list that sets this is
      it."""

      if not self.main_view:
         self.main_view = view

   def set_contents_view(self, view):
      """Call this method to set the contents view. First come first served
      -- whatever module the user puts first in the list that sets this is
      it. This is the frame in the top-left if you use the default frameset."""

      if not self.contents_view: self.contents_view = view
    
   def set_index_view(self, view):
      """Call this method to set the index view. First come first served
      -- whatever module the user puts first in the list that sets this is
      it. This is the frame on the left if you use the default frameset."""

      if not self.index_view: self.index_view = view

   def set_using_module_index(self):
      """Sets the using_module_index flag. This will cause the an
      intermediate level of links intended to go in the left frame."""
      self.using_module_index = True

   def global_scope(self):
      "Return the global scope"

      return self.__global

   def calculate_start(self, root, namespace=None):
      "Calculates the start scope using the 'namespace' config var"

      scope_names = string.split(namespace or '', "::")
      #scope_names = string.split(namespace or config.namespace, "::")
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

   def add_root_view(self, file, label, target, visibility):
      """Adds a named link to the list of root views. Called from the
      constructors of View objects. The root views are displayed at the top
      of every view, depending on their visibility (higher = more visible).
      @param file	    the filename, to be used when generating the link
      @param label	    the label of the view
      @param target       target frame
      @param visibility   should be a number such as 1 or 2. Visibility 2 is
      shown on all views, 1 only on views with lots of
      room. For example, views for the top-left frame
      only show visibility 2 views."""

      self.__roots.append(Struct(file=file, label=label, target=target, visibility=visibility))

   def navigation_bar(self, origin, visibility=1):
      """Formats the list of root views to HTML. The origin specifies the
      generated view itself (which shouldn't be linked), such that the relative
      links can be generated. Only root views of 'visibility' or
      above are included."""

      # If not using frames, show all headings on all views!
      if not self.has_view('FramesIndex'):
         visibility = 1
      #filter out roots that are visible
      roots = filter(lambda x,v=visibility: x.visibility >= v, self.__roots)
      #a function generating a link
      other = lambda x: span('root-other', href(rel(origin, x.file), x.label, target=x.target))
      #a function simply printing label
      current = lambda x: span('root-current', x.label)
      # generate the header
      roots = map(lambda x: x.file==origin and current(x) or other(x), roots)
      return div('navigation', string.join(roots, '\n'))+'\n'

   def register_filename(self, filename, view, scope):
      """Registers a file for later production. The first view to register
      the filename gets to keep it."""

      filename = str(filename)
      if not self.__files.has_key(filename):
         self.__files[filename] = (view, scope)

   def filename_info(self, filename):
      """Returns information about a registered file, as a (view,scope)
      pair. Will return None if the filename isn't registered."""

      return self.__files.get(filename)

