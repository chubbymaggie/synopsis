//
// Copyright (C) 2004 Stefan Seefeld
// All rights reserved.
// Licensed to the public under the terms of the GNU LGPL (>= 2),
// see the file COPYING for details.
//
#ifndef _SymbolLookup_Table_hh
#define _SymbolLookup_Table_hh

#include <SymbolLookup/Scope.hh>
#include <SymbolLookup/ConstEvaluator.hh>
#include <stack>

namespace SymbolLookup
{

//. Table provides a facade to the SymbolLookup module...
class Table
{
public:
  //.
  enum Language { NONE = 0x00, C99 = 0x01, CXX = 0x02};

  //. A Guard provides RAII - like protection for the scope stack
  struct Guard
  {
    //. Construct a guard for the given table.
    //. If the pointer is 0 there is no cleanup to do
    Guard(Table *t) : table(t) {}
    ~Guard();
    Table *table;
  };

  //. Create a symbol lookup table for the given language.
  //. Right now only CXX is supported.
  Table(Language = CXX);

  Table &enter_scope();
  Table &enter_namespace(const PTree::NamespaceSpec *);
  Table &enter_class(const PTree::ClassSpec *);
  Table &enter_function(const PTree::Declaration *);
  Table &enter_block(const PTree::List *);
  void leave_scope();

  Scope &current_scope();

  bool evaluate_const(const PTree::Node *node, long &value);

  void declare(PTree::Declaration *);
  void declare(PTree::Typedef *);
  //. declare the enumeration as a new TYPE as well as all the enumerators as CONST
  void declare(PTree::EnumSpec *);
  //. declare the namespace as a new NAMESPACE
  void declare(PTree::NamespaceSpec *);
  //. declare the class as a new TYPE
  void declare(PTree::ClassSpec *);
  void declare(PTree::TemplateDecl *);

  //. look up the encoded name and return a set of matching symbols.
  virtual std::set<Symbol const *> lookup(const PTree::Encoding &) const;

private:
  typedef std::stack<Scope *> Scopes;

  static PTree::Encoding get_base_name(const PTree::Encoding &enc, const Scope *&scope);
  static int get_base_name_if_template(PTree::Encoding::iterator i, const Scope *&);
  static const Scope *lookup_typedef_name(PTree::Encoding::iterator, size_t, const Scope *);
  static PTree::ClassSpec *get_class_template_spec(PTree::Node *);
  static PTree::Node *strip_cv_from_integral_type(PTree::Node *);

  Language my_language;
  Scopes   my_scopes;
};

inline Table::Guard::~Guard() { if (table) table->leave_scope();}

inline bool Table::evaluate_const(const PTree::Node *node, long &value)
{
  if (my_language == NONE) return false;
  if (!node) return false;
  ConstEvaluator e(*my_scopes.top());
  return e.evaluate(const_cast<PTree::Node *>(node), value);
}

}

#endif
