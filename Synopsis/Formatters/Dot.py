#
# Copyright (C) 2000 Stefan Seefeld
# Copyright (C) 2000 Stephen Davies
# All rights reserved.
# Licensed to the public under the terms of the GNU LGPL (>= 2),
# see the file COPYING for details.
#

"""
Uses 'dot' from graphviz to generate various graphs.
"""

from Synopsis.Processor import *
from Synopsis.QualifiedName import *
from Synopsis import ASG
from Synopsis.Formatters import TOC
from Synopsis.Formatters import quote_name, open_file
import sys, os

verbose = False
debug = False

class SystemError:
   """Error thrown by the system() function. Attributes are 'retval', encoded
   as per os.wait(): low-byte is killing signal number, high-byte is return
   value of command."""

   def __init__(self, retval, command):

      self.retval = retval
      self.command = command

   def __repr__(self):

      return 'SystemError: %(retval)x"%(command)s" failed.'%self.__dict__

def system(command):
   """Run the command. If the command fails, an exception SystemError is
   thrown."""

   ret = os.system(command)
   if (ret>>8) != 0:
      raise SystemError(ret, command)


def normalize(color):
   """Generate a color triplet from a color string."""

   if type(color) is str and color[0] == '#':
      return (int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16))
   elif type(color) is tuple:
      return (color[0] * 255, color[1] * 255, color[2] * 255)


def light(color):

   import colorsys
   hsv = colorsys.rgb_to_hsv(*color)
   return colorsys.hsv_to_rgb(hsv[0], hsv[1], hsv[2]/2)


class DotFileGenerator:
   """A class that encapsulates the dot file generation"""
   def __init__(self, os, direction, bgcolor):

      self.__os = os
      self.direction = direction
      self.bgcolor = bgcolor and '"#%X%X%X"'%bgcolor
      self.light_color = bgcolor and '"#%X%X%X"'%light(bgcolor) or 'gray75'
      self.nodes = {}

   def write(self, text): self.__os.write(text)

   def write_node(self, ref, name, label, **attr):
      """helper method to generate output for a given node"""

      if self.nodes.has_key(name): return
      self.nodes[name] = len(self.nodes)
      number = self.nodes[name]

      # Quote to remove characters that dot can't handle
      for p in [('<', '\<'), ('>', '\>'), ('{','\{'), ('}','\}')]:
         label = label.replace(*p)

      if self.bgcolor:
         attr['fillcolor'] = self.bgcolor
         attr['style'] = 'filled'

      self.write("Node" + str(number) + " [shape=\"record\", label=\"{" + label + "}\"")
      #self.write(", fontSize = 10, height = 0.2, width = 0.4")
      self.write(''.join([', %s=%s'%item for item in attr.items()]))
      if ref: self.write(', URL="' + ref + '"')
      self.write('];\n')

   def write_edge(self, parent, child, **attr):

      self.write("Node" + str(self.nodes[parent]) + " -> ")
      self.write("Node" + str(self.nodes[child]))
      self.write('[ color="black", fontsize=10, dir=back' + ''.join([', %s="%s"'%item for item in attr.items()]) + '];\n')

class InheritanceGenerator(DotFileGenerator, ASG.Visitor):
   """A Formatter that generates an inheritance graph. If the 'toc' argument is not None,
   it is used to generate URLs. If no reference could be found in the toc, the node will
   be grayed out."""
   def __init__(self, os, direction, operations, attributes, aggregation,
                toc, prefix, no_descend, bgcolor):
      
      DotFileGenerator.__init__(self, os, direction, bgcolor)
      if operations: self.__operations = []
      else: self.__operations = None
      if attributes: self.__attributes = []
      else: self.__attributes = None
      self.aggregation = aggregation
      self.toc = toc
      self.scope = QualifiedName()
      if prefix:
         if prefix.contains('::'):
            self.scope = QualifiedCxxName(prefix.split('::'))
         elif prefix.contains('.'):
            self.scope = QualifiedPythonName(prefix.split('.'))
         else:
            self.scope = QualifiedName((prefix,))
      self.__type_ref = None
      self.__type_label = ''
      self.__no_descend = no_descend
      self.nodes = {}

   def type_ref(self): return self.__type_ref
   def type_label(self): return self.__type_label
   def parameter(self): return self.__parameter

   def format_type(self, typeObj):
      "Returns a reference string for the given type object"

      if typeObj is None: return "(unknown)"
      typeObj.accept(self)
      return self.type_label()

   def clear_type(self):

      self.__type_ref = None
      self.__type_label = ''
      
   def get_class_name(self, node):
      """Returns the name of the given class node, relative to all its
      parents. This makes the graph simpler by making the names shorter"""

      base = node.name
      for i in node.parents:
         try:
            parent = i.parent
            pname = parent.name
            for j in range(len(base)):
               if j > len(pname) or pname[j] != base[j]:
                  # Base is longer than parent name, or found a difference
                  base[j:] = []
                  break
         except: pass # typedefs etc may cause errors here.. ignore
      if not node.parents:
         base = self.scope
      return str(self.scope.prune(node.name))

   #################### Type Visitor ##########################################

   def visit_modifier_type(self, type):

      self.format_type(type.alias)
      self.__type_label = ''.join(type.premod) + self.__type_label
      self.__type_label = self.__type_label + ''.join(type.postmod)

   def visit_unknown_type(self, type):

      self.__type_ref = self.toc and self.toc[type.link] or None
      self.__type_label = str(self.scope.prune(type.name))
        
   def visit_builtin_type_id(self, type):

      self.__type_ref = None
      self.__type_label = type.name[-1]

   def visit_dependent_type_id(self, type):

      self.__type_ref = None
      self.__type_label = type.name[-1]
        
   def visit_declared_type_id(self, type):

      self.__type_ref = self.toc and self.toc[type.declaration.name] or None
      if isinstance(type.declaration, ASG.Class):
         self.__type_label = self.get_class_name(type.declaration)
      else:
         self.__type_label = str(self.scope.prune(type.declaration.name))

   def visit_parametrized_type_id(self, type):

      if type.template:
         type_ref = self.toc and self.toc[type.template.name] or None
         type_label = str(self.scope.prune(type.template.name))
      else:
         type_ref = None
         type_label = "(unknown)"
      parameters_label = []
      for p in type.parameters:
         parameters_label.append(self.format_type(p))
      self.__type_ref = type_ref
      self.__type_label = type_label + "<" + ','.join(parameters_label) + ">"

   def visit_template_id(self, type):
      self.__type_ref = None
      def clip(x, max=20):
         if len(x) > max: return '...'
         return x
      self.__type_label = "template<%s>"%(clip(','.join([clip(self.format_type(p)) for p in type.parameters]), 40))

   #################### ASG Visitor ###########################################

   def visit_inheritance(self, node):

      self.format_type(node.parent)
      if self.type_ref():
         self.write_node(self.type_ref().link, self.type_label(), self.type_label())
      elif self.toc:
         self.write_node('', self.type_label(), self.type_label(), color=self.light_color, fontcolor=self.light_color)
      else:
         self.write_node('', self.type_label(), self.type_label())
        
   def visit_class(self, node):

      if self.__operations is not None: self.__operations.append([])
      if self.__attributes is not None: self.__attributes.append([])
      name = self.get_class_name(node)
      ref = self.toc and self.toc[node.name] or None
      for d in node.declarations: d.accept(self)
      # NB: old version of dot needed the label surrounded in {}'s (?)
      label = name
      if type(node) is ASG.ClassTemplate and node.template:
         if self.direction == 'vertical':
            label = self.format_type(node.template) + '\\n' + label
         else:
            label = self.format_type(node.template) + ' ' + label
      if self.__operations or self.__attributes:
         label = label + '\\n'
         if self.__operations:
            label += '|' + ''.join([x[-1] + '()\\l' for x in self.__operations[-1]])
         if self.__attributes:
            label += '|' + ''.join([x[-1] + '\\l' for x in self.__attributes[-1]])
      if ref:
         self.write_node(ref.link, name, label)
      elif self.toc:
         self.write_node('', name, label, color=self.light_color, fontcolor=self.light_color)
      else:
         self.write_node('', name, label)

      if self.aggregation:
         #FIXME: we shouldn't only be looking for variables of the exact type,
         #       but also derived types such as pointers, references, STL containers, etc.
         #
         # find attributes of type 'Class' so we can link to it
         for a in filter(lambda a:isinstance(a, ASG.Variable), node.declarations):
            if isinstance(a.vtype, ASG.DeclaredTypeId):
               d = a.vtype.declaration
               if isinstance(d, ASG.Class) and self.nodes.has_key(self.get_class_name(d)):
                  self.write_edge(self.get_class_name(node), self.get_class_name(d),
                                  arrowtail='ediamond')

      for p in node.parents:
         p.accept(self)
         self.write_edge(self.type_label(), name, arrowtail='empty')
      if self.__no_descend: return
      if self.__operations: self.__operations.pop()
      if self.__attributes: self.__attributes.pop()

   def visit_operation(self, operation):

      if self.__operations:
         self.__operations[-1].append(operation.real_name)

   def visit_variable(self, variable):

      if self.__attributes:
         self.__attributes[-1].append(variable.name)

class SingleInheritanceGenerator(InheritanceGenerator):
   """A Formatter that generates an inheritance graph for a specific class.
   This Visitor visits the ASG upwards, i.e. following the inheritance links, instead of
   the declarations contained in a given scope."""

   def __init__(self, os, direction, operations, attributes, levels, types,
                toc, prefix, no_descend, bgcolor):
      InheritanceGenerator.__init__(self, os, direction, operations, attributes, False,
                                    toc, prefix, no_descend, bgcolor)
      self.__levels = levels
      self.__types = types
      self.__current = 1
      self.__visited_classes = {} # classes already visited, to prevent recursion

   #################### Type Visitor ##########################################

   def visit_declared_type_id(self, type):
      if self.__current < self.__levels or self.__levels == -1:
         self.__current = self.__current + 1
         type.declaration.accept(self)
         self.__current = self.__current - 1
      # to restore the ref/label...
      InheritanceGenerator.visit_declared_type_id(self, type)

   #################### ASG Visitor ###########################################
        
   def visit_inheritance(self, node):

      node.parent.accept(self)
      if self.type_label():
         if self.type_ref():
            self.write_node(self.type_ref().link, self.type_label(), self.type_label())
         elif self.toc:
            self.write_node('', self.type_label(), self.type_label(), color=self.light_color, fontcolor=self.light_color)
         else:
            self.write_node('', self.type_label(), self.type_label())
        
   def visit_class(self, node):

      # Prevent recursion
      if self.__visited_classes.has_key(id(node)): return
      self.__visited_classes[id(node)] = None

      name = self.get_class_name(node)
      if self.__current == 1:
         self.write_node('', name, name, style='filled', color=self.light_color, fontcolor=self.light_color)
      else:
         ref = self.toc and self.toc[node.name] or None
         if ref:
            self.write_node(ref.link, name, name)
         elif self.toc:
            self.write_node('', name, name, color=self.light_color, fontcolor=self.light_color)
         else:
            self.write_node('', name, name)

      for p in node.parents:
         p.accept(self)
         if self.nodes.has_key(self.type_label()):
            self.write_edge(self.type_label(), name, arrowtail='empty')
      # if this is the main class and if there is a type dictionary,
      # look for classes that are derived from this class

      # if this is the main class
      if self.__current == 1 and self.__types:
         # fool the visit_declared_type_id method to stop walking upwards
         self.__levels = 0
         for t in self.__types.values():
            if isinstance(t, ASG.DeclaredTypeId):
               child = t.declaration
               if isinstance(child, ASG.Class):
                  for i in child.parents:
                     type = i.parent
                     type.accept(self)
                     if self.type_ref():
                        if self.type_ref().name == node.name:
                           child_label = self.get_class_name(child)
                           ref = self.toc and self.toc[child.name] or None
                           if ref:
                              self.write_node(ref.link, child_label, child_label)
                           elif self.toc:
                              self.write_node('', child_label, child_label, color=self.light_color, fontcolor=self.light_color)
                           else:
                              self.write_node('', child_label, child_label)

                           self.write_edge(name, child_label, arrowtail='empty')

class FileDependencyGenerator(DotFileGenerator, ASG.Visitor):
   """A Formatter that generates a file dependency graph"""

   def visit_file(self, file):
      if file.annotations['primary']:
         self.write_node('', file.name, file.name)
      for i in file.includes:
         target = i.target
         if target.annotations['primary']:
            self.write_node('', target.name, target.name)
            name = i.name
            name = name.replace('"', '\\"')
            self.write_edge(target.name, file.name, label=name, style='dashed')

def _rel(frm, to):
   "Find link to to relative to frm"

   frm = frm.split('/'); to = to.split('/')
   for l in range((len(frm)<len(to)) and len(frm)-1 or len(to)-1):
      if to[0] == frm[0]: del to[0]; del frm[0]
      else: break
   if frm: to = ['..'] * (len(frm) - 1) + to
   return '/'.join(to)

def _convert_map(input, output, base_url):
   """convert map generated from Dot to a html region map.
   input and output are (open) streams"""

   line = input.readline()
   while line:
      line = line[:-1]
      if line[0:4] == "rect":
         url, x1y1, x2y2 = line[4:].split()
         x1, y1 = x1y1.split(',')
         x2, y2 = x2y2.split(',')
         output.write('<area alt="'+url+'" href="' + _rel(base_url, url) + '" shape="rect" coords="')
         output.write(str(x1) + ", " + str(y1) + ", " + str(x2) + ", " + str(y2) + '" />\n')
      line = input.readline()

def _format(input, output, format):

   command = 'dot -T%s -o "%s" "%s"'%(format, output, input)
   if verbose: print "Dot Formatter: running command '" + command + "'"
   try:
      system(command)
   except SystemError, e:
      if debug:
         print 'failed to execute "%s"'%command
      raise InvalidCommand, "could not execute 'dot'"

def _format_png(input, output): _format(input, output, "png")

def _format_html(input, output, base_url):
   """generate (active) image for html.
   input and output are file names. If output ends
   in '.html', its stem is used with an '.png' suffix for the
   actual image."""

   if output[-5:] == ".html": output = output[:-5]
   _format_png(input, output + ".png")
   _format(input, output + ".map", "imap")
   prefix, name = os.path.split(output)
   reference = name + ".png"
   html = open_file(output + ".html")
   html.write('<img alt="'+name+'" src="' + reference + '" hspace="8" vspace="8" border="0" usemap="#')
   html.write(name + "_map\" />\n")
   html.write("<map name=\"" + name + "_map\">")
   dotmap = open(output + ".map", "r+")
   _convert_map(dotmap, html, base_url)
   dotmap.close()
   os.remove(output + ".map")
   html.write("</map>\n")

class Formatter(Processor):
   """The Formatter class acts merely as a frontend to
   the various InheritanceGenerators"""

   title = Parameter('Inheritance Graph', 'the title of the graph')
   type = Parameter('class', 'type of graph (one of "file", "class", "single"')
   hide_operations = Parameter(True, 'hide operations')
   hide_attributes = Parameter(True, 'hide attributes')
   show_aggregation = Parameter(False, 'show aggregation')
   bgcolor = Parameter(None, 'background color for nodes')
   format = Parameter('ps', 'Generate output in format "dot", "ps", "png", "svg", "gif", "map", "html"')
   layout = Parameter('vertical', 'Direction of graph')
   prefix = Parameter(None, 'Prefix to strip from all class names')
   toc_in = Parameter([], 'list of table of content files to use for symbol lookup')
   base_url = Parameter(None, 'base url to use for generated links')

   def process(self, ir, **kwds):
      global verbose, debug
      
      self.set_parameters(kwds)
      if self.bgcolor:
         bgcolor = normalize(self.bgcolor)
         if not bgcolor:
            raise InvalidArgument('bgcolor=%s'%repr(self.bgcolor))
         else:
            self.bgcolor = bgcolor

      self.ir = self.merge_input(ir)
      verbose = self.verbose
      debug = self.debug

      formats = {'dot' : 'dot',
                 'ps' : 'ps',
                 'png' : 'png',
                 'gif' : 'gif',
                 'svg' : 'svg',
                 'map' : 'imap',
                 'html' : 'html'}

      if formats.has_key(self.format): format = formats[self.format]
      else:
         print "Error: Unknown format. Available formats are:",
         print ', '.join(formats.keys())
         return self.ir

      # we only need the toc if format=='html'
      if format == 'html':
         # beware: HTML.Fragments.ClassHierarchyGraph sets self.toc !!
         toc = getattr(self, 'toc', TOC.TOC(TOC.Linker()))
         for t in self.toc_in: toc.load(t)
      else:
         toc = None

      head, tail = os.path.split(self.output)
      tmpfile = os.path.join(head, quote_name(tail)) + ".dot"
      if self.verbose: print "Dot Formatter: Writing dot file..."
      dotfile = open_file(tmpfile)
      dotfile.write("digraph \"%s\" {\n"%(self.title))
      if self.layout == 'horizontal':
         dotfile.write('rankdir="LR";\n')
         dotfile.write('ranksep="1.0";\n')
      dotfile.write("node[shape=record, fontsize=10, height=0.2, width=0.4, color=black]\n")
      if self.type == 'single':
         generator = SingleInheritanceGenerator(dotfile, self.layout,
                                                not self.hide_operations,
                                                not self.hide_attributes,
                                                -1, self.ir.asg.types,
                                                toc, self.prefix, False,
                                                self.bgcolor)
      elif self.type == 'class':
         generator = InheritanceGenerator(dotfile, self.layout,
                                          not self.hide_operations,
                                          not self.hide_attributes,
                                          self.show_aggregation,
                                          toc, self.prefix, False,
                                          self.bgcolor)
      elif self.type == 'file':
         generator = FileDependencyGenerator(dotfile, self.layout, self.bgcolor)
      else:
         sys.stderr.write("Dot: unknown type\n");
         

      if self.type == 'file':
         for f in self.ir.files.values():
            generator.visit_file(f)
      else:
         for d in self.ir.asg.declarations:
            d.accept(generator)
      dotfile.write("}\n")
      dotfile.close()
      if format == "dot":
         os.rename(tmpfile, self.output)
      elif format == "png":
         _format_png(tmpfile, self.output)
         os.remove(tmpfile)
      elif format == "html":
         _format_html(tmpfile, self.output, self.base_url)
         os.remove(tmpfile)
      else:
         _format(tmpfile, self.output, format)
         os.remove(tmpfile)

      return self.ir

