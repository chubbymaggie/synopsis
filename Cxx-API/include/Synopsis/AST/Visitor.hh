// $Id: Visitor.hh,v 1.1 2004/01/25 21:21:54 stefan Exp $
//
// Copyright (C) 2004 Stefan Seefeld
// All rights reserved.
// Licensed to the public under the terms of the GNU LGPL (>= 2),
// see the file COPYING for details.
//

#ifndef _Synopsis_AST_Visitor_hh
#define _Synopsis_AST_Visitor_hh

namespace Synopsis
{
namespace AST
{

class Declaration;
class Builtin;
class Macro;
class Scope;
class Module;
class Class;
class Inheritance;
class Forward;
class Typedef;
class Variable;
class Const;
class Enumerator;
class Enum;
class Parameter;
class Function;
class Operation;

//. The Visitor for the AST hierarchy. This class is just an interface
//. really. It is abstract, and you must reimplement any methods you want.
//. The default implementations of the methods call the visit methods for
//. the subclasses of the visited type, eg visit_namespace calls visit_scope
//. which calls visit_declaration.
class Visitor
{
public:
  // Abstract destructor makes the class abstract
  virtual ~Visitor() {}
  virtual void visit_declaration(const Declaration*) = 0;
  virtual void visit_builtin(const Builtin*) = 0;
  virtual void visit_macro(const Macro*) = 0;
  virtual void visit_scope(const Scope*) = 0;
  virtual void visit_module(const Module*) = 0;
  virtual void visit_class(const Class*) = 0;
  virtual void visit_inheritance(const Inheritance*) = 0;
  virtual void visit_forward(const Forward*) = 0;
  virtual void visit_typedef(const Typedef*) = 0;
  virtual void visit_variable(const Variable*) = 0;
  virtual void visit_const(const Const*) = 0;
  virtual void visit_enum(const Enum*) = 0;
  virtual void visit_enumerator(const Enumerator*) = 0;
  virtual void visit_parameter(const Parameter*) = 0;
  virtual void visit_function(const Function*) = 0;
  virtual void visit_operation(const Operation*) = 0;
};

class Type;
class Unknown;
class Modifier;
class Array;
class Named;
class Base;
class Dependent;
class Declared;
class Template;
class Parametrized;
class FunctionPtr;

//. The Type Visitor base class
class TypeVisitor
{
public:
  // Virtual destructor makes abstract
  virtual ~TypeVisitor() {}
  virtual void visit_type(const Type*) = 0;
  virtual void visit_named(const Named*) = 0;
  virtual void visit_base(const Base*) = 0;
  virtual void visit_dependent(const Dependent*) = 0;
  virtual void visit_unknown(const Unknown*) = 0;
  virtual void visit_modifier(const Modifier*) = 0;
  virtual void visit_array(const Array*) = 0;
  virtual void visit_declared(const Declared*) = 0;
  virtual void visit_template(const Template*) = 0;
  virtual void visit_parametrized(const Parametrized*) = 0;
  virtual void visit_function_ptr(const FunctionPtr*) = 0;
};

}
}

#endif
