// $Id: synopsis.hh,v 1.34 2003/12/03 06:43:43 stefan Exp $
//
// Copyright (C) 2000 Stefan Seefeld
// Copyright (C) 2000 Stephen Davies
// All rights reserved.
// Licensed to the public under the terms of the GNU LGPL (>= 2),
// see the file COPYING for details.
//

#ifndef H_SYNOPSIS_CPP_SYNOPSIS
#define H_SYNOPSIS_CPP_SYNOPSIS

#include <iostream>
#include <string>
#include <vector>
#include <list>
#include <stack>
#include <Python.h>
#include "ast.hh"
#include "type.hh"

#if DEBUG
#define DO_TRACE
class Trace
{
public:
  Trace(const std::string &s) : scope(s)
  {
    std::cout << indent() << "entering " << scope << std::endl;
    ++level;
  }
  ~Trace()
  {
    --level;
    std::cout << indent() << "leaving " << scope << std::endl;
  }
private:
  std::string indent() { return std::string(level, ' ');}
  static int level;
  std::string scope;
};
#else
class Trace
{
public:
  Trace(const std::string &) {}
  ~Trace() {}
};
#endif

class FileFilter;

//. The Synopsis class maps from C++ objects to Python objects
class Synopsis : public AST::Visitor, public Types::Visitor
{
public:

  Synopsis(FileFilter*, PyObject *ast);
  ~Synopsis();

  void translate(AST::Scope* global);
  void set_builtin_decls(const AST::Declaration::vector& builtin_decls);

  //
  // types from the Synopsis.Type module
  //
  PyObject* Base(Types::Base*);
  PyObject* Unknown(Types::Named*);
  PyObject* Declared(Types::Declared*);
  PyObject* Dependent(Types::Dependent*);
  PyObject* Template(Types::Template*);
  PyObject* Modifier(Types::Modifier*);
  PyObject* Array(Types::Array*);
  PyObject* Parameterized(Types::Parameterized*);
  PyObject* FuncPtr(Types::FuncPtr*);
  
  //
  // types from the Synopsis.AST module
  //
  PyObject* SourceFile(AST::SourceFile*);
  PyObject* Include(AST::Include*);
  PyObject* Declaration(AST::Declaration*);
  PyObject* Builtin(AST::Builtin*);
  PyObject* Macro(AST::Macro*);
  PyObject* Forward(AST::Forward*);
  PyObject* Scope(AST::Scope*);
  PyObject* Namespace(AST::Namespace*);
  PyObject* Inheritance(AST::Inheritance*);
  PyObject* Class(AST::Class*);
  PyObject* Typedef(AST::Typedef*);
  PyObject* Enumerator(AST::Enumerator*);
  PyObject* Enum(AST::Enum*);
  PyObject* Variable(AST::Variable*);
  PyObject* Const(AST::Const*);
  PyObject* Parameter(AST::Parameter*);
  PyObject* Function(AST::Function*);
  PyObject* Operation(AST::Operation*);
  PyObject* Comment(AST::Comment*);

  //
  // AST::Visitor methods
  //
  void visit_declaration(AST::Declaration*);
  void visit_builtin(AST::Builtin*);
  void visit_macro(AST::Macro*);
  void visit_scope(AST::Scope*);
  void visit_namespace(AST::Namespace*);
  void visit_class(AST::Class*);
  void visit_inheritance(AST::Inheritance*);
  void visit_forward(AST::Forward*);
  void visit_typedef(AST::Typedef*);
  void visit_variable(AST::Variable*);
  void visit_const(AST::Const*);
  void visit_enum(AST::Enum*);
  void visit_enumerator(AST::Enumerator*);
  void visit_function(AST::Function*);
  void visit_operation(AST::Operation*);
  void visit_parameter(AST::Parameter*);
  void visit_comment(AST::Comment*);
  
  //
  // Types::Visitor methods
  //
  //void visitType(Types::Type*);
  void visit_unknown(Types::Unknown*);
  void visit_modifier(Types::Modifier*);
  void visit_array(Types::Array*);
  //void visitNamed(Types::Named*);
  void visit_base(Types::Base*);
  void visit_dependent(Types::Dependent*);
  void visit_declared(Types::Declared*);
  void visit_template_type(Types::Template*);
  void visit_parameterized(Types::Parameterized*);
  void visit_func_ptr(Types::FuncPtr*);

private:
  //. Compiler Firewalled private data
  struct Private;
  friend struct Private;
  Private* m;

  //.
  //. helper methods
  //.
  void addComments(PyObject* pydecl, AST::Declaration* cdecl);

  ///////// EVERYTHING BELOW HERE SUBJECT TO REVIEW AND DELETION


  /*
    PyObject *lookupType(const std::string &, PyObject *);
    PyObject *lookupType(const std::string &);
    PyObject *lookupType(const std::vector<std::string>& qualified);
    
    static void addInheritance(PyObject *, const std::vector<PyObject *> &);
    static PyObject *N2L(const std::string &);
    static PyObject *V2L(const std::vector<std::string> &);
    static PyObject *V2L(const std::vector<PyObject *> &);
    static PyObject *V2L(const std::vector<size_t> &);
    void pushClassBases(PyObject* clas);
    PyObject* resolveDeclared(PyObject*);
    void addDeclaration(PyObject *);
  */
private:
  PyObject* m_ast_module;
  PyObject* m_type_module;
  PyObject *m_ast;
  PyObject* m_declarations;
  PyObject* m_dictionary;
  
  FileFilter* m_filter;
};

#endif
