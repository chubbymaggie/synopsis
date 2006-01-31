//
// Copyright (C) 2004 Stefan Seefeld
// All rights reserved.
// Licensed to the public under the terms of the GNU LGPL (>= 2),
// see the file COPYING for details.
//
#ifndef Synopsis_SymbolTable_Symbol_hh_
#define Synopsis_SymbolTable_Symbol_hh_

#include <Synopsis/PTree/Encoding.hh>
#include <Synopsis/PTree/Lists.hh>

namespace Synopsis
{
namespace SymbolTable
{

class Symbol;
class VariableName;
class ConstName;
class TypeName;
class TypedefName;
class ClassName;
class EnumName;
class ClassTemplateName;
class FunctionName;
class FunctionTemplateName;
class NamespaceName;
class DependentName;

class SymbolVisitor
{
public:
  virtual ~SymbolVisitor() {}

  virtual void visit(Symbol const *) {}
  virtual void visit(VariableName const *) {}
  virtual void visit(ConstName const *) {}
  virtual void visit(TypeName const *) {}
  virtual void visit(TypedefName const *) {}
  virtual void visit(ClassName const *) {}
  virtual void visit(EnumName const *) {}
  virtual void visit(DependentName const *) {}
  virtual void visit(ClassTemplateName const *) {}
  virtual void visit(FunctionName const *) {}
  virtual void visit(FunctionTemplateName const *) {}
  virtual void visit(NamespaceName const *) {}
};

class Scope;
class Class;
class Namespace;
class FunctionScope;

class Symbol
{
public:
  Symbol(PTree::Encoding const &t, PTree::Node const *p, bool def, Scope *s)
    : my_type(t), my_ptree(p), my_definition(def), my_scope(s) {}
  virtual ~Symbol(){}
  virtual void accept(SymbolVisitor *v) const { v->visit(this);}
  PTree::Encoding const & type() const { return my_type;}
  PTree::Node const * ptree() const { return my_ptree;}
  bool is_definition() const { return my_definition;}
  Scope * scope() const { return my_scope;}
private:
  PTree::Encoding     my_type;
  PTree::Node const * my_ptree;
  bool                my_definition;
  Scope             * my_scope;
};

class VariableName : public Symbol
{
public:
  VariableName(PTree::Encoding const &type, PTree::Node const *ptree,
	       bool def, Scope *s)
    : Symbol(type, ptree, def, s) {}
  virtual void accept(SymbolVisitor *v) const { v->visit(this);}
};

class ConstName : public VariableName
{
public:
  ConstName(PTree::Encoding const &type, long v,
	    PTree::Node const *ptree, bool def, Scope *s)
    : VariableName(type, ptree, def, s), my_defined(true), my_value(v) {}
  ConstName(PTree::Encoding const &type,
	    PTree::Node const *ptree, bool def, Scope *s)
    : VariableName(type, ptree, def, s), my_defined(false) {}
  virtual void accept(SymbolVisitor *v) const { v->visit(this);}
  bool defined() const { return my_defined;}
  long value() const { return my_value;}
private:
  bool my_defined;
  long my_value;
};

class TypeName : public Symbol
{
public:
  TypeName(PTree::Encoding const &type, PTree::Node const *ptree,
	   bool def, Scope *s)
    : Symbol(type, ptree, def, s) {}
  virtual void accept(SymbolVisitor *v) const { v->visit(this);}
};

class TypedefName : public TypeName
{
public:
  TypedefName(PTree::Encoding const &type, PTree::Node const *ptree, Scope *scope,
	      TypeName const *aliased)
    : TypeName(type, ptree, false, scope), my_aliased(aliased) {}
  virtual void accept(SymbolVisitor *v) const { v->visit(this);}
  TypeName const *aliased() const { return my_aliased;}
private:
  TypeName const *my_aliased;
};

class ClassName : public TypeName
{
public:
  ClassName(PTree::Encoding const &type, PTree::Node const *ptree, bool def, Scope *s)
    : TypeName(type, ptree, def, s) {}
  virtual void accept(SymbolVisitor *v) const { v->visit(this);}

  //. Return the class scope associated with this symbol.
  //. This will return 0 if the class definition hasn't been seen yet.
  Class *as_scope() const;
};

class EnumName : public TypeName
{
public:
  EnumName(PTree::Node const *ptree, Scope *scope)
    : TypeName(PTree::Encoding(), ptree, true, scope) {}
  virtual void accept(SymbolVisitor *v) const { v->visit(this);}
};

class DependentName : public TypeName
{
public:
  DependentName(PTree::Node const *ptree, Scope *scope)
    : TypeName(PTree::Encoding(), ptree, false, scope) {}
  virtual void accept(SymbolVisitor *v) const { v->visit(this);}
};

class ClassTemplateName : public Symbol
{
public:
  ClassTemplateName(PTree::Encoding const &type, PTree::Node const *ptree, bool def,
		    Scope *s)
    : Symbol(type, ptree, def, s) {}
  virtual void accept(SymbolVisitor *v) const { v->visit(this);}

  //. Return the class scope associated with this symbol.
  //. This will return 0 if the class definition hasn't been seen yet.
  Class *as_scope() const;
};

class FunctionName : public Symbol
{
public:
  FunctionName(PTree::Encoding const &type, PTree::Node const *ptree,
	       size_t params, size_t default_args, bool def, Scope *s)
    : Symbol(type, ptree, def, s),
      my_params(params),
      my_default_args(default_args) 
  {}
  virtual void accept(SymbolVisitor *v) const { v->visit(this);}

  //. Return the function scope associated with this symbol.
  //. This will return 0 if the function definition hasn't been seen yet.
  FunctionScope *as_scope() const;

  size_t params() const { return my_params;}
  size_t default_args() const { return my_default_args;}

private:
  size_t my_params;
  size_t my_default_args;
};

class FunctionTemplateName : public Symbol
{
public:
  FunctionTemplateName(PTree::Encoding const &type, PTree::Node const *ptree,
		       size_t params, size_t default_args, bool def, Scope *s)
    : Symbol(type, ptree, def, s),
      my_params(params),
      my_default_args(default_args) {}
  virtual void accept(SymbolVisitor *v) const { v->visit(this);}

  //. Return the function scope associated with this symbol.
  //. This will return 0 if the function definition hasn't been seen yet.
  FunctionScope *as_scope() const;

  size_t params() const { return my_params;}
  size_t default_args() const { return my_default_args;}

private:
  size_t my_params;
  size_t my_default_args;
};

class NamespaceName : public Symbol
{
public:
  NamespaceName(PTree::Encoding const &type, PTree::Node const *ptree,
		bool def, Scope *s)
    : Symbol(type, ptree, def, s) {}
  virtual void accept(SymbolVisitor *v) const { v->visit(this);}

  //. Return the namespace scope associated with this symbol.
  //. This will return 0 if the namespace definition hasn't been seen yet.
  Namespace *as_scope() const;
};

extern TypeName const * const DEPENDENT;

}
}

#endif
