//
// Copyright (C) 2004 Stefan Seefeld
// All rights reserved.
// Licensed to the public under the terms of the GNU LGPL (>= 2),
// see the file COPYING for details.
//
#include <PTree/Display.hh>
#include <PTree/Writer.hh>
#include <SymbolLookup/Table.hh>
#include <SymbolLookup/Scopes.hh>
#include <SymbolLookup/ConstEvaluator.hh>
#include <Synopsis/Trace.hh>
#include <cassert>

using Synopsis::Trace;

using namespace PTree;
using namespace SymbolLookup;

Table::Table(Language l)
  : my_language(l)
{
  // define the global scope
  my_scopes.push(new Namespace(0, 0));
}

Table &Table::enter_namespace(PTree::NamespaceSpec const *spec)
{
  Trace trace("Table::enter_namespace");
  if (my_language == NONE) return *this;
  Scope *scope = my_scopes.top()->find_scope(spec);
  if (!scope)
  {
    // If the namespace was already opened before, we should add a reference
    // to it under the current NamespaceSpec, too.
    // However, namespaces are only valid within namespaces (and the global scope).
    Namespace *ns = dynamic_cast<Namespace *>(my_scopes.top());
    if (ns)
    {
      PTree::Node const *name = PTree::second(spec);
      scope = ns->find_namespace(std::string(name->position(), name->length()));
      if (scope)
	ns->declare_scope(spec, scope);
    }
  }
  if (!scope)
  {
    // This is a new namespace. Declare it.
    scope = new Namespace(spec, my_scopes.top());
    my_scopes.top()->declare_scope(spec, scope);
  }
  else scope->ref();
  my_scopes.push(scope);
  return *this;
}

Table &Table::enter_class(PTree::ClassSpec const *spec)
{
  Trace trace("Table::enter_class");
  if (my_language == NONE) return *this;
  Scope *scope = my_scopes.top()->find_scope(spec);
  if (!scope)
  {
    scope = new Class(spec, my_scopes.top());
    my_scopes.top()->declare_scope(spec, scope);
  }
  else scope->ref();
  my_scopes.push(scope);
  return *this;
}

Table &Table::enter_function(PTree::Declaration const *decl)
{
  Trace trace("Table::enter_function");
  if (my_language == NONE) return *this;
  Scope *scope = my_scopes.top()->find_scope(decl);
  if (!scope)
  {
    scope = new FunctionScope(decl, my_scopes.top());
    my_scopes.top()->declare_scope(decl, scope);
  }
  else scope->ref();
  my_scopes.push(scope);
  return *this;
}

Table &Table::enter_block(PTree::List const *block)
{
  Trace trace("Table::enter_block");
  if (my_language == NONE) return *this;
  Scope *scope = my_scopes.top()->find_scope(block);
  if (!scope)
  {
    scope = new LocalScope(block, my_scopes.top());
    my_scopes.top()->declare_scope(block, scope);
  }
  else scope->ref();
  my_scopes.push(scope);
  return *this;
}

void Table::leave_scope()
{
  Trace trace("Table::leave_scope");
  if (my_language == NONE) return;
  Scope *top = my_scopes.top();
  my_scopes.pop();
  top->unref();
}

Scope &Table::current_scope()
{
  return *my_scopes.top();
}

void Table::declare(Declaration *d)
{
  Trace trace("Table::declare(Declaration *)");
  if (my_language == NONE) return;
  Node *decls = third(d);
  if(is_a(decls, Token::ntDeclarator))
  {
    // function definition,
    // declare it only once (but allow overloading)

    PTree::Encoding name = decls->encoded_name();
    // see whether it was previously declared
    FunctionNameSet fs = my_scopes.top()->lookup_function(name);
    // If name is qualified the function has to be declared already
    // so we only need to find it to report an error if it was not.
    

    PTree::Encoding type = decls->encoded_type();

    // if the name is qualified, it has to be
    // declared already. If it hasn't, raise an error
    if (name.is_qualified())
    {
      SymbolSet symbols = lookup(name);
      if (symbols.empty()) throw Undefined(name);
      return;
    }
    
    // FIXME: raise an error if this function was already defined
    Scope *scope = my_scopes.top();
    scope->declare(name, new FunctionName(type, decls, scope));
  }
  else
  {
    // function or variable declaration
    PTree::Node *storage_spec = PTree::first(d);
    PTree::Node *type_spec = PTree::second(d);
    if (decls->is_atom()) ; // it is a ';'
    else
    {
      for (; decls; decls = decls->cdr())
      {
	PTree::Node *decl = decls->car();
	if (PTree::is_a(decl, Token::ntDeclarator))
	{
	  PTree::Encoding name = decl->encoded_name();
	  PTree::Encoding type = decl->encoded_type();
	  Scope *scope = my_scopes.top();
	  if (type.is_function())
	    scope->declare(name, new FunctionName(type, decl, scope));
	  else
	    scope->declare(name, new VariableName(type, decl, scope));
	}
      }
    }
  }
}

void Table::declare(Typedef *td)
{
  Trace trace("Table::declare(Typedef *)");
  if (my_language == NONE) return;
  Node *declarations = third(td);
  while(declarations)
  {
    Node *d = declarations->car();
    if(type_of(d) == Token::ntDeclarator)
    {
      Encoding name = d->encoded_name();
      Encoding type = d->encoded_type();
      Scope *scope = my_scopes.top();
      scope->declare(name, new TypeName(type, d, scope));
    }
    declarations = tail(declarations, 2);
  }
}

void Table::declare(EnumSpec *spec)
{
  Trace trace("Table::declare(EnumSpec *)");
  if (my_language == NONE) return;
  Node *tag = second(spec);
  Encoding const &name = spec->encoded_name();
  Encoding const &type = spec->encoded_type();
  if(tag && tag->is_atom()) 
    my_scopes.top()->declare(name, new TypeName(type, spec, my_scopes.top()));
  // else it's an anonymous enum

  Node *body = third(spec);
  // The numeric value of an enumerator is either specified
  // by an explicit initializer or it is determined by incrementing
  // by one the value of the previous enumerator.
  // The default value for the first enumerator is 0
  long value = -1;
  for (Node *e = second(body); e; e = rest(rest(e)))
  {
    Node *enumerator = e->car();
    bool defined = true;
    if (enumerator->is_atom()) ++value;
    else  // [identifier = initializer]
    {
      Node *initializer = third(enumerator);
      defined = evaluate_const(initializer, value);
      enumerator = enumerator->car();
#ifndef NDEBUG
      if (!defined)
      {
	std::cerr << "Error in evaluating enum initializer:\n"
		  << "Expression doesn't evaluate to a constant integral value:\n"
		  << reify(initializer) << std::endl;
      }
#endif
    }
    assert(enumerator->is_atom());
    Encoding name(enumerator->position(), enumerator->length());
    Scope *scope = my_scopes.top();
    if (defined)
      scope->declare(name, new ConstName(type, value, enumerator, scope));
    else
      scope->declare(name, new ConstName(type, enumerator, scope));
  }
}

void Table::declare(NamespaceSpec *spec)
{
  Trace trace("Table::declare(NamespaceSpec *)");
  if (my_language == NONE) return;
  // Beware anonymous namespaces !
  Encoding name = (second(spec) ?
		   Encoding::simple_name(static_cast<Atom const *>(second(spec))) :
		   "<anonymous>");
  Scope *scope = my_scopes.top();
  // Namespaces can be reopened, so only declare it if it isn't already known.
  SymbolSet symbols = scope->find(name);
  if (symbols.empty())
  {
    scope->declare(name, new NamespaceName(spec->encoded_type(), spec, scope));
  }
  // FIXME: assert that the found symbol really refers to a namespace !
}

void Table::declare(ClassSpec *spec)
{
  Trace trace("Table::declare(ClassSpec *)");
  if (my_language == NONE) return;
  Encoding const &name = spec->encoded_name();
  Scope *scope = my_scopes.top();
  scope->declare(name, new TypeName(spec->encoded_type(), spec, scope));
}

void Table::declare(TemplateDecl *tdecl)
{
  Trace trace("Table::declare(TemplateDecl *)");
  if (my_language == NONE) return;
  PTree::Node *body = PTree::nth(tdecl, 4);
  PTree::ClassSpec *class_spec = Table::get_class_template_spec(body);
  Scope *scope = my_scopes.top();
  if (class_spec)
  {
    Encoding name = class_spec->encoded_name();
    scope->declare(name, new ClassTemplateName(Encoding(), tdecl, scope));
  }
  else
  {
    PTree::Node *decl = PTree::third(body);
    PTree::Encoding name = decl->encoded_name();
    scope->declare(name, new FunctionTemplateName(Encoding(), decl, scope));
  }
}

void Table::declare(PTree::Using *ustmt)
{
  Trace trace("Table::declare(Using *)");
  if (my_language == NONE) return;
  my_scopes.top()->use(ustmt);
}

SymbolSet Table::lookup(PTree::Encoding const &name) const
{
  if (my_language == NONE) return SymbolSet();
  else return my_scopes.top()->lookup(name);
}

//. get_base_name() returns "Foo" if ENCODE is "Q[2][1]X[3]Foo",
//. for example.
//. If an error occurs, the function returns 0.
PTree::Encoding Table::get_base_name(PTree::Encoding const &enc,
				     Scope const *&scope)
{
  if(enc.empty()) return enc;
  Scope const *s = scope;
  PTree::Encoding::iterator i = enc.begin();
  if(*i == 'Q')
  {
    int n = *(i + 1) - 0x80;
    i += 2;
    while(n-- > 1)
    {
      int m = *i++;
      if(m == 'T') m = Table::get_base_name_if_template(i, s);
      else if(m < 0x80) return PTree::Encoding(); // error?
      else
      {	 // class name
	m -= 0x80;
	if(m <= 0)
	{		// if global scope (e.g. ::Foo)
	  if(s) s = s->global();
	}
	else s = lookup_typedef_name(i, m, s);
      }
      i += m;
    }
    scope = s;
  }
  if(*i == 'T')
  {		// template class
    int m = *(i + 1) - 0x80;
    int n = *(i + m + 2) - 0x80;
    return PTree::Encoding(i, i + m + n + 3);
  }
  else if(*i < 0x80) return PTree::Encoding();
  else return PTree::Encoding(i + 1, i + 1 + size_t(*i - 0x80));
}

int Table::get_base_name_if_template(Encoding::iterator i,
				     Scope const *&scope)
{
  int m = *i - 0x80;
  if(m <= 0) return *(i+1) - 0x80 + 2;

  if(scope)
  {
    SymbolSet symbols = scope->lookup(Encoding((char const *)&*(i + 1), m));
    // FIXME !! (see Environment)
    if (symbols.size()) return m + (*(i + m + 1) - 0x80) + 2;
  }
  // the template name was not found.
  scope = 0;
  return m + (*(i + m + 1) - 0x80) + 2;
}

Scope const *Table::lookup_typedef_name(Encoding::iterator i, size_t s,
					Scope const *scope)
{
//   TypeInfo tinfo;
//   Bind *bind;
//   Class *c = 0;

  if(scope)
    ;
//     if (scope->LookupType(Encoding((char const *)&*i, s), bind) && bind)
//       switch(bind->What())
//       {
//         case Bind::isClassName :
// 	  c = bind->ClassMetaobject();
// 	  break;
//         case Bind::isTypedefName :
// 	  bind->GetType(tinfo, env);
// 	  c = tinfo.class_metaobject();
// 	  /* if (c == 0) */
// 	  env = 0;
// 	  break;
//         default :
// 	  break;
//       }
//     else if (env->LookupNamespace(Encoding((char const *)&*i, s)))
//     {
//       /* For the time being, we simply ignore name spaces.
//        * For example, std::T is identical to ::T.
//        */
//       env = env->GetBottom();
//     }
//     else env = 0; // unknown typedef name

//   return c ? c->GetEnvironment() : env;
  return 0;
}

PTree::ClassSpec *Table::get_class_template_spec(PTree::Node *body)
{
  if(*PTree::third(body) == ';')
  {
    PTree::Node *spec = strip_cv_from_integral_type(PTree::second(body));
    return dynamic_cast<PTree::ClassSpec *>(spec);
  }
  return 0;
}

PTree::Node *Table::strip_cv_from_integral_type(PTree::Node *integral)
{
  if(integral == 0) return 0;

  if(!integral->is_atom())
    if(PTree::is_a(integral->car(), Token::CONST, Token::VOLATILE))
      return PTree::second(integral);
    else if(PTree::is_a(PTree::second(integral), Token::CONST, Token::VOLATILE))
      return integral->car();

  return integral;
}
