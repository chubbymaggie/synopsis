//
// Copyright (C) 2004 Stefan Seefeld
// All rights reserved.
// Licensed to the public under the terms of the GNU LGPL (>= 2),
// see the file COPYING for details.
//
#include <PTree/Display.hh>
#include <PTree/Writer.hh>
#include <PTree/Symbol.hh>
#include <PTree/ConstEvaluator.hh>
#include <cassert>

using namespace PTree;

Scope::~Scope()
{
}

void Scope::declare(const Encoding &name, const Symbol *s)
{
  my_symbols[name] = s;
}

void Scope::declare(Declaration *d)
{
  Node *decls = third(d);
  if(is_a(decls, Token::ntDeclarator))
  {
    // function definition
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
	  declare(name, new VariableName(type, decl));
	}
      }
    }
  }
}

void Scope::declare(Typedef *td)
{
  Node *declarations = third(td);
  while(declarations)
  {
    Node *d = declarations->car();
    if(type_of(d) == Token::ntDeclarator)
    {
      Encoding name = d->encoded_name();
      Encoding type = d->encoded_type();
      declare(name, new TypeName(type, d));
    }
    declarations = tail(declarations, 2);
  }
}

void Scope::declare(EnumSpec *spec)
{
  Node *tag = second(spec);
  const Encoding &name = spec->encoded_name();
  const Encoding &type = spec->encoded_type();
  if(tag && tag->is_atom()) declare(name, new TypeName(type, spec));
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
      defined = evaluate_const(initializer, *this, value);
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
    if (defined)
      declare(name, new ConstName(type, value, enumerator));
    else
      declare(name, new ConstName(type, enumerator));
  }
}

void Scope::declare(ClassSpec *spec)
{
  const Encoding &name = spec->encoded_name();
  declare(name, new TypeName(spec->encoded_type(), spec));
}

void Scope::declare(TemplateDecl *tdecl)
{
  PTree::Node *body = PTree::nth(tdecl, 4);
  PTree::ClassSpec *class_spec = get_class_template_spec(body);
  if (class_spec)
  {
    Encoding name = class_spec->encoded_name();
    declare(name, new ClassTemplateName(Encoding(), tdecl));
  }
  else
  {
    PTree::Node *decl = PTree::third(body);
    PTree::Encoding name = decl->encoded_name();
    declare(name, new FunctionTemplateName(Encoding(), decl));
  }
}

const Symbol *Scope::lookup(const Encoding &id) const throw()
{
  SymbolTable::const_iterator i = my_symbols.find(id);
  return i == my_symbols.end() ? 0 : i->second;
}

void Scope::dump(std::ostream &os) const
{
  os << "Scope::dump:" << std::endl;
  for (SymbolTable::const_iterator i = my_symbols.begin(); i != my_symbols.end(); ++i)
  {
    if (const VariableName *variable = dynamic_cast<const VariableName *>(i->second))
      os << "Variable: " << i->first << ' ' << variable->type() << std::endl;
    else if (const ConstName *const_ = dynamic_cast<const ConstName *>(i->second))
    {
      os << "Const:    " << i->first << ' ' << const_->type();
      if (const_->defined()) os << " (" << const_->value() << ')';
      os << std::endl;
    }
    else if (const TypeName *type = dynamic_cast<const TypeName *>(i->second))
      os << "Type: " << i->first << ' ' << type->type() << std::endl;
    else if (const ClassTemplateName *type = dynamic_cast<const ClassTemplateName *>(i->second))
      os << "Class template: " << i->first << ' ' << type->type() << std::endl;
    else if (const FunctionTemplateName *type = dynamic_cast<const FunctionTemplateName *>(i->second))
      os << "Function template: " << i->first << ' ' << type->type() << std::endl;
    else // shouldn't get here
      os << "Symbol: " << i->first << ' ' << i->second->type() << std::endl;
  }  
}

//. get_base_name() returns "Foo" if ENCODE is "Q[2][1]X[3]Foo", for example.
//. If an error occurs, the function returns 0.
Encoding Scope::get_base_name(const Encoding &enc, const Scope *&scope)
{
  if(enc.empty()) return enc;
  const Scope *s = scope;
  Encoding::iterator i = enc.begin();
  if(*i == 'Q')
  {
    int n = *(i + 1) - 0x80;
    i += 2;
    while(n-- > 1)
    {
      int m = *i++;
      if(m == 'T') m = get_base_name_if_template(i, s);
      else if(m < 0x80) return Encoding(); // error?
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
    return Encoding(i, i + m + n + 3);
  }
  else if(*i < 0x80) return Encoding();
  else return Encoding(i + 1, i + 1 + size_t(*i - 0x80));
}

int Scope::get_base_name_if_template(Encoding::iterator i, const Scope *&scope)
{
  int m = *i - 0x80;
  if(m <= 0) return *(i+1) - 0x80 + 2;

  if(scope)
  {
    const Symbol *symbol = scope->lookup(Encoding((const char*)&*(i + 1), m));
    // FIXME !! (see Environment)
    if (symbol) return m + (*(i + m + 1) - 0x80) + 2;
  }
  // the template name was not found.
  scope = 0;
  return m + (*(i + m + 1) - 0x80) + 2;
}

const Scope *Scope::lookup_typedef_name(Encoding::iterator i, size_t s,
					const Scope *scope)
{
//   TypeInfo tinfo;
//   Bind *bind;
//   Class *c = 0;

  if(scope)
    ;
//     if (scope->LookupType(Encoding((const char *)&*i, s), bind) && bind)
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
//     else if (env->LookupNamespace(Encoding((const char *)&*i, s)))
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

PTree::ClassSpec *Scope::get_class_template_spec(PTree::Node *body)
{
  if(*PTree::third(body) == ';')
  {
    PTree::Node *spec = strip_cv_from_integral_type(PTree::second(body));
    return dynamic_cast<PTree::ClassSpec *>(spec);
  }
  return 0;
}

PTree::Node *Scope::strip_cv_from_integral_type(PTree::Node *integral)
{
  if(integral == 0) return 0;

  if(!integral->is_atom())
    if(PTree::is_a(integral->car(), Token::CONST, Token::VOLATILE))
      return PTree::second(integral);
    else if(PTree::is_a(PTree::second(integral), Token::CONST, Token::VOLATILE))
      return integral->car();

  return integral;
}

const Symbol *NestedScope::lookup(const Encoding &name) const throw()
{
  const Symbol *symbol = Scope::lookup(name);
  return symbol ? symbol : my_outer->lookup(name);
}

void NestedScope::dump(std::ostream &os) const
{
  os << "NestedScope::dump:" << std::endl;
  Scope::dump(os);
  my_outer->dump(os);
}
