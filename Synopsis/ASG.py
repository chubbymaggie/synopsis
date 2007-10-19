#
# Copyright (C) 2000 Stefan Seefeld
# Copyright (C) 2000 Stephen Davies
# All rights reserved.
# Licensed to the public under the terms of the GNU LGPL (>= 2),
# see the file COPYING for details.
#

"""Abstract Syntax Tree classes.

This file contains classes which encapsulate nodes in the ASG. The base class
is the Declaration class that encapsulates a named declaration. All names used
are scoped tuples.

Also defined in module scope are the constants DEFAULT, PUBLIC, PROTECTED and
PRIVATE.
"""

# Accessibility constants
DEFAULT = 0
PUBLIC = 1
PROTECTED = 2
PRIVATE = 3

def ccmp(a,b):
   """Compares classes of two objects"""
   return cmp(type(a),type(b)) or cmp(a.__class__,b.__class__)


class Debugger(type):
   """Wrap the object's 'accept' method, printing out the visitor's type.
   Useful for tracing visitors visiting declarations."""

   def __init__(cls, name, bases, dict):

       accept = dict['accept']
       "The original instancemethod."
       
       def accept_wrapper(self, visitor):
           "The wrapper. The original 'accept' method is part of its closure."
           print '%s accepting %s.%s'%(self.__class__.__name__,
                                       visitor.__module__,
                                       visitor.__class__.__name__)
           accept(self, visitor)

       setattr(cls, 'accept', accept_wrapper)

class Declaration(object):
   """Declaration base class. Every declaration has a name, type,
   accessibility and annotations. The default accessibility is DEFAULT except for
   C++ where the Parser always sets it to one of the other three. """
    
   #__metaclass__ = Debugger

   def __init__(self, file, line, type, name):

      self.file  = file
      self.line  = line
      self.name = name
      self.type = type
      self.accessibility = DEFAULT
      self.annotations = {}

   def _set_name(self, name): self._name = tuple(name)
   name = property(lambda self: self._name, _set_name)

   def accept(self, visitor):
      """Visit the given visitor"""
      visitor.visit_declaration(self)


class Builtin(Declaration):
   """An ast node for internal use only."""

   def __init__(self, file, line, type, name):
      """Constructor"""

      Declaration.__init__(self, file, line, type, name)

   def accept(self, visitor): visitor.visit_builtin(self)

class Macro(Declaration):
   """A preprocessor macro. Note that macros are not strictly part of the
   ASG, and as such are always in the global scope. A macro is "temporary" if
   it was #undefined in the same file it was #defined in."""

   def __init__(self, file, line, type, name, parameters, text):

      Declaration.__init__(self, file, line, type, name)
      self.parameters = parameters
      self.text = text

   def accept(self, visitor): visitor.visit_macro(self)


class Forward(Declaration):
   """Forward declaration"""

   def __init__(self, file, line, type, name):

      Declaration.__init__(self, file, line, type, name)

   def accept(self, visitor): visitor.visit_forward(self)


class Group(Declaration):
   """Base class for groups which contain declarations.
   This class doesn't correspond to any language construct.
   Rather, it may be used with comment-embedded grouping tags
   to regroup declarations that are to appear together in the
   manual."""

   def __init__(self, file, line, type, name):

      Declaration.__init__(self, file, line, type, name)
      self.declarations = []

   def accept(self, visitor):

      visitor.visit_group(self)


class Scope(Group):
   """Base class for scopes (named groups)."""

   def __init__(self, file, line, type, name):

      Group.__init__(self, file, line, type, name)

   def accept(self, visitor): visitor.visit_scope(self)


class Module(Scope):
   """Module class"""
   def __init__(self, file, line, type, name):

      Scope.__init__(self, file, line, type, name)

   def accept(self, visitor): visitor.visit_module(self)


class MetaModule(Module):
   """Module Class that references all places where this Module occurs"""

   def __init__(self, type, name):

      Scope.__init__(self, None, "", type, name)
      self.module_declarations = []

   def accept(self, visitor): visitor.visit_meta_module(self)


class Inheritance(object):
   """Inheritance class. This class encapsulates the information about an
   inheritance, such as attributes like 'virtual' and 'public' """

   def __init__(self, type, parent, attributes):
      self.type = type
      self.parent = parent
      self.attributes = attributes

   def accept(self, visitor): visitor.visit_inheritance(self)
   

class Class(Scope):
   """Class class."""

   def __init__(self, file, line, type, name):

      Scope.__init__(self, file, line, type, name)
      self.parents = []
      self.template = None

   def accept(self, visitor): visitor.visit_class(self)


class Typedef(Declaration):

   def __init__(self, file, line, type, name, alias, constr):
      Declaration.__init__(self, file, line, type, name)
      self.alias = alias
      self.constr = constr

   def accept(self, visitor): visitor.visit_typedef(self)


class Enumerator(Declaration):
   """Enumerator of an Enum. Enumerators represent the individual names and
   values in an enum."""
   
   def __init__(self, file, line, name, value):
      Declaration.__init__(self, file, line, "enumerator", name)
      self.value = value

   def accept(self, visitor): visitor.visit_enumerator(self)

class Enum(Declaration):
   """Enum declaration. The actual names and values are encapsulated by
   Enumerator objects."""

   def __init__(self, file, line, name, enumerators):

      Declaration.__init__(self, file, line, "enum", name)
      self.enumerators = enumerators[:]
      #FIXME: the Cxx parser will append a Builtin('eos') to the
      #list of enumerators which we need to extract here.
      self.eos = None
      if self.enumerators and isinstance(self.enumerators[-1], Builtin):
         self.eos = self.enumerators.pop()

   def accept(self, visitor): visitor.visit_enum(self)


class Variable(Declaration):
   """Variable definition"""

   def __init__(self, file, line, type, name, vtype, constr):
      Declaration.__init__(self, file, line, type, name)
      self.vtype  = vtype
      self.constr  = constr

   def accept(self, visitor): visitor.visit_variable(self)
    

class Const(Declaration):
   """Constant declaration. A constant is a name with a type and value."""

   def __init__(self, file, line, type, ctype, name, value):
      Declaration.__init__(self, file, line, type, name)
      self.ctype  = ctype
      self.value = value

   def accept(self, visitor): visitor.visit_const(self)
       

class Parameter(object):
   """Function Parameter"""
   
   def __init__(self, premod, type, postmod, name='', value=''):
      self.premodifier = premod
      self.type = type
      self.postmodifier = postmod
      self.name = name
      self.value = value

   def accept(self, visitor): visitor.visit_parameter(self)
   
   def __cmp__(self, other):
      "Comparison operator"
      #print "Parameter.__cmp__"
      return cmp(self.type,other.type)
   def __str__(self):
      return "%s%s%s"%(self.premodifier,str(self.type),self.postmodifier)

class Function(Declaration):
   """Function declaration.
   Note that function names are stored in mangled form to allow overriding.
   Formatters should use the real_name to extract the unmangled name."""

   def __init__(self, file, line, type, premod, return_type, postmod, name, real_name):
      Declaration.__init__(self, file, line, type, name)
      self._real_name = real_name
      self.premodifier = premod
      self.return_type = return_type
      self.parameters = []
      self.postmodifier = postmod
      self.exceptions = []
      self.template = None

   real_name = property(lambda self: self.name[:-1] + (self._real_name,))

   def accept(self, visitor): visitor.visit_function(self)

   def __cmp__(self, other):
      "Recursively compares the typespec of the function"
      return ccmp(self,other) or cmp(self.parameters, other.parameters)

class Operation(Function):
   """Operation class. An operation is related to a Function and is currently
   identical.
   """
   def __init__(self, file, line, type, premod, return_type, postmod, name, real_name):
      Function.__init__(self, file, line, type, premod, return_type, postmod, name, real_name)
   def accept(self, visitor): visitor.visit_operation(self)

class Visitor :
   """Visitor for ASG nodes"""

   def visit_declaration(self, node): return
   def visit_builtin(self, node):
      """Visit a Builtin instance. By default do nothing. Processors who
      operate on Builtin nodes have to provide an appropriate implementation."""
      pass
   def visit_macro(self, node): self.visit_declaration(node)
   def visit_forward(self, node): self.visit_declaration(node)
   def visit_group(self, node):
      self.visit_declaration(node)
      for d in node.declarations: d.accept(self)
   def visit_scope(self, node): self.visit_group(node)
   def visit_module(self, node): self.visit_scope(node)
   def visit_meta_module(self, node): self.visit_module(node)
   def visit_class(self, node): self.visit_scope(node)
   def visit_typedef(self, node): self.visit_declaration(node)
   def visit_enumerator(self, node): self.visit_declaration(node)
   def visit_enum(self, node):
      self.visit_declaration(node)
      for e in node.enumerators:
         e.accept(self)
      if node.eos:
         node.eos.accept(self)
   def visit_variable(self, node): self.visit_declaration(node)
   def visit_const(self, node): self.visit_declaration(node)
   def visit_function(self, node):
      self.visit_declaration(node)
      for parameter in node.parameters: parameter.accept(self)
   def visit_operation(self, node): self.visit_function(node)
   def visit_parameter(self, node): return
   def visit_inheritance(self, node): return
