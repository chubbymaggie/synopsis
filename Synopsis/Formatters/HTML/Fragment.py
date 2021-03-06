#
# Copyright (C) 2000 Stephen Davies
# Copyright (C) 2000 Stefan Seefeld
# All rights reserved.
# Licensed to the public under the terms of the GNU LGPL (>= 2),
# see the file COPYING for details.
#

from Tags import *

class Fragment(object):
   """Generates HTML fragment for a declaration. Multiple strategies are
   combined to generate the output for a single declaration, allowing the
   user to customise the output by choosing a set of strategies. This follows
   the Strategy design pattern.
   
   The key concept of this class is the format* methods. Any
   class derived from Strategy that overrides one of the format methods
   will have that method called by the Summary and Detail parts when
   they visit that ASG type. Summary and Detail maintain a list of
   Strategies, and a list for each ASG type.
    
   For example, when Strategy.Summary visits a Function object, it calls
   the formatFunction method on all Strategys registed with
   Summary that implemented that method. Each of these format
   methods returns a string, which may contain a TD tag to create a new
   column.

   An important point to note is that only Strategies which override a
   particular format method are called - if that format method is not
   overridden then it is not called for that declaration type.
   """

   def register(self, part):
      """Store part as self.part. The part is either a
      Summary or Detail, and is used for things like
      reference() and label() calls. Local references to the part's
      reference and label methods are stored in self for more efficient use
      of them."""

      self.processor = part.processor
      self.directory_layout = self.processor.directory_layout
      self.part = part
      self.label = part.label
      self.reference = part.reference
      self.format_type = part.format_type
      self.view = part.view()

   #
   # Utility methods
   #
   def format_modifiers(self, modifiers):
      """Returns a HTML string from the given list of string modifiers. The
      modifiers are enclosed in 'keyword' spans."""

      def keyword(m):
         if m == '&': return span('&amp;', class_='keyword')
         return span(m, class_='keyword')
      return ''.join([keyword(m) for m in modifiers])


   #
   # ASG Formatters
   #
   def format_declaration(self, decl): pass
   def format_macro(self, decl): pass
   def format_forward(self, decl): pass
   def format_group(self, decl): pass
   def format_scope(self, decl): pass
   def format_module(self, decl): pass
   def format_meta_module(self, decl): pass
   def format_class(self, decl): pass
   def format_class_template(self, decl): pass
   def format_typedef(self, decl): pass
   def format_enum(self, decl): pass
   def format_variable(self, decl): pass
   def format_const(self, decl): pass
   def format_function(self, decl): pass
   def format_function_template(self, decl): pass
   def format_operation(self, decl): pass
   def format_operation_template(self, decl): pass
