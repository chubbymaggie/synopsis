//
// Copyright (C) 2004 Stefan Seefeld
// All rights reserved.
// Licensed to the public under the terms of the GNU LGPL (>= 2),
// see the file COPYING for details.
//
#ifndef Synopsis_SymbolTable_Scopes_hh_
#define Synopsis_SymbolTable_Scopes_hh_

#include <Synopsis/SymbolTable/Scope.hh>
#include <string>
#include <vector>
#include <list>

namespace Synopsis
{
namespace SymbolTable
{

class TemplateParameterScope;
class LocalScope;
class PrototypeScope;
class FunctionScope;
class Class;
class Namespace;

//. A Visitor for Scopes.
//. The default implementation does nothing, so
//. users only need to implement the ones they need.
class ScopeVisitor
{
public:
  virtual ~ScopeVisitor() {}

  virtual void visit(TemplateParameterScope *) {}
  virtual void visit(LocalScope *) {}
  virtual void visit(PrototypeScope *) {}
  virtual void visit(FunctionScope *) {}
  virtual void visit(Class *) {}
  virtual void visit(Namespace *) {}
};

class TemplateParameterScope : public Scope
{
public:
  TemplateParameterScope(PTree::List const *node, Scope *outer)
    : my_node(node), my_outer(outer->ref()) {}

  virtual SymbolSet
  unqualified_lookup(PTree::Encoding const &, LookupContext) const;

  virtual Scope *outer_scope() { return my_outer;}
  virtual void accept(ScopeVisitor *v) { v->visit(this);}

protected:
  ~TemplateParameterScope() { my_outer->unref();}

private:
  PTree::List const *my_node;
  Scope *            my_outer;
};

class LocalScope : public Scope
{
public:
  LocalScope(PTree::List const *node, Scope *outer)
    : my_node(node), my_outer(outer->ref()) {}

  virtual Scope *outer_scope() { return my_outer;}

  virtual SymbolSet 
  unqualified_lookup(PTree::Encoding const &, LookupContext) const;

  virtual void accept(ScopeVisitor *v) { v->visit(this);}

protected:
  ~LocalScope() { my_outer->unref();}

private:
  PTree::List const *my_node;
  Scope *            my_outer;
};

class FunctionScope : public Scope
{
public:
  FunctionScope(PTree::Declaration const *, PrototypeScope *, Scope *outer);

  virtual void use(Namespace const *);
  virtual Scope *outer_scope() { return my_outer;}
  virtual SymbolSet 
  unqualified_lookup(PTree::Encoding const &, LookupContext) const;
  virtual SymbolSet 
  qualified_lookup(PTree::Encoding const &, LookupContext) const;

  // FIXME: what is 'name' ? (template parameters...)
  std::string name() const;

  virtual void accept(ScopeVisitor *v) { v->visit(this);}

protected:
  ~FunctionScope() { my_outer->unref();}

private:
  typedef std::set<Namespace const *> Using;

  PTree::Declaration const * my_decl;
  Scope *                    my_outer;
  Class const *              my_class;
  PrototypeScope const *     my_params;
  Using                      my_using;
};

class PrototypeScope : public Scope
{
  friend class FunctionScope;
public:
  PrototypeScope(PTree::Node const *decl, Scope *outer,
		 TemplateParameterScope const *params)
    : my_decl(decl), my_outer(outer->ref()), my_params(params) {}

  virtual Scope *outer_scope() { return my_outer;}
  virtual SymbolSet 
  unqualified_lookup(PTree::Encoding const &, LookupContext) const;

  PTree::Node const *declaration() const { return my_decl;}
  TemplateParameterScope const *templ_params() const { return my_params;}

  std::string name() const;

  virtual void accept(ScopeVisitor *v) { v->visit(this);}

protected:
  ~PrototypeScope() { my_outer->unref();}

private:
  PTree::Node const *           my_decl;
  Scope *                       my_outer;
  TemplateParameterScope const *my_params;
};

class Class : public Scope
{
public:
  typedef std::vector<Class const *> Bases;

  Class(std::string const &name, PTree::ClassSpec const *spec, Scope *outer,
	Bases const &bases, TemplateParameterScope const *params);

  virtual Scope *outer_scope() { return my_outer;}
  virtual SymbolSet 
  unqualified_lookup(PTree::Encoding const &, LookupContext) const;

  // FIXME: what is 'name' ? (template parameters...)
  std::string name() const { return my_name;}

  virtual void accept(ScopeVisitor *v) { v->visit(this);}

protected:
  ~Class() { my_outer->unref();}

private:
  PTree::ClassSpec       const *my_spec;
  std::string                   my_name;
  Scope *                       my_outer;
  Bases                         my_bases;
  TemplateParameterScope const *my_parameters;
};

class Namespace : public Scope
{
public:
  Namespace(PTree::NamespaceSpec const *spec, Namespace *outer)
    : my_spec(spec),
      my_outer(outer ? static_cast<Namespace *>(outer->ref()) : 0)
  {
  }
  //. Find a nested namespace.
  Namespace *find_namespace(PTree::NamespaceSpec const *name) const;

  virtual void use(Namespace const *);
  virtual Scope *outer_scope() { return my_outer;}
  virtual SymbolSet 
  unqualified_lookup(PTree::Encoding const &, LookupContext) const;
  virtual SymbolSet 
  qualified_lookup(PTree::Encoding const &, LookupContext) const;

  // FIXME: should that really be a string ? It may be better to be conform with
  // Class::name, which, if the class is a template, can't be a string (or can it ?)
  std::string name() const;

  virtual void accept(ScopeVisitor *v) { v->visit(this);}

protected:
  ~Namespace() { if (my_outer) my_outer->unref();}

private:
  typedef std::set<Namespace const *> Using;

  SymbolSet 
  unqualified_lookup(PTree::Encoding const &, LookupContext, Using &) const;
  SymbolSet 
  qualified_lookup(PTree::Encoding const &, LookupContext, Using &) const;

  PTree::NamespaceSpec const *my_spec;
  Namespace *                 my_outer;
  Using                       my_using;
};

}
}

#endif