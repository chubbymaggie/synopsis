//
// Copyright (C) 2000 Stefan Seefeld
// Copyright (C) 2000 Stephen Davies
// All rights reserved.
// Licensed to the public under the terms of the GNU LGPL (>= 2),
// see the file COPYING for details.
//

#include <Synopsis/Python/Module.hh>
#include <Synopsis/Trace.hh>
#include <Support/ErrorHandler.hh>
#include "Translator.hh"
#include "SXRGenerator.hh"
#include "swalker.hh"
#include "builder.hh"
#include "filter.hh"

#include <Synopsis/PTree.hh>
#include <Synopsis/PTree/Display.hh>
#include <Synopsis/SymbolLookup.hh>
#include <Synopsis/Buffer.hh>
#include <Synopsis/Lexer.hh>
#include <Synopsis/SymbolFactory.hh>
#include <Synopsis/Parser.hh>
#include <occ/MetaClass.hh>
#include <occ/Environment.hh>

#include <cstdio>
#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <cstring>
#include <cstdio>
#include <stdexcept>
#include <memory>

using namespace Synopsis;

//
// for now occ remains the 'C++ parser backend' for synopsis,
// and GCC extension and MSVC tokens are activated in compatibility
// mode.
// Later this may become an option for the python frontend, too.
//
#if defined(__GNUG__) || defined(_GNUG_SYNTAX)
# if defined(PARSE_MSVC)
const int tokenset = Lexer::CXX | Lexer::GCC | Lexer::MSVC;
const int ruleset = Parser::CXX | Parser::GCC | Parser::MSVC;
# else
const int tokenset = Lexer::CXX | Lexer::GCC;
const int ruleset = Parser::CXX | Parser::GCC;
# endif
#else
# if defined(PARSE_MSVC)
const int tokenset = Lexer::CXX | Lexer::MSVC;
const int ruleset = Parser::CXX | Parser::MSVC;
# else
const int tokenset = Lexer::CXX;
const int ruleset = Parser::CXX;
# endif
#endif


/* The following aren't used anywhere. Though it has to be defined and initialized to some dummy default
 * values since it is required by the opencxx.a module, which I don't want to modify...
 */
bool showProgram = false;
bool doCompile = false;
bool makeExecutable = false;
bool doPreprocess = true;
bool doTranslate = false;
bool verboseMode = false;
bool regularCpp = false;
bool makeSharedLibrary = false;
bool preprocessTwice = false;
char* sharedLibraryName = 0;

/* These also are just dummies needed by the opencxx module */
void RunSoCompiler(const char *) {}
void *LoadSoLib(char *) { return 0;}
void *LookupSymbol(void *, char *) { return 0;}
/* This implements the static var and method from fakegc.h */
cleanup* FakeGC::head = 0;
void FakeGC::delete_all()
{
  cleanup* node = FakeGC::head;
  cleanup* next;
  size_t count = 0;
  while (node)
  {
    next = node->cleanup_next;
    delete node;
    node = next;
    count++;
  }
  FakeGC::head = 0;
  //std::cout << "FakeGC::delete_all(): deleted " << count << " objects." << std::endl;
}

bool verbose;

// If true then everything but what's in the primary file will be stripped
bool syn_primary_only;
bool syn_fake_std;
bool syn_multi_files;

// If set then this is stripped from the start of all filenames
const char* syn_base_path = "";

// If set then this is the prefix for the filename to store links to
const char* syn_sxr_prefix = 0;

PyObject *py_error;

namespace
{

//. Override unexpected() to print a message before we abort
void unexpected()
{
  std::cout << "Warning: Aborting due to unexpected exception." << std::endl;
  throw std::bad_exception();
}

const char *strip_prefix(const char *filename, const char *prefix)
{
  if (!prefix) return filename;
  size_t length = strlen(prefix);
  if (strncmp(filename, prefix, length) == 0)
    return filename + length;
  return filename;
}

void error()
{
  SWalker *instance = SWalker::instance();
  std::cerr << "processing " << instance->current_file()->name()
            << " at line " << instance->current_lineno()
            << std::endl;
}

PyObject *parse(PyObject * /* self */, PyObject *args)
{
  Class::do_init_static();
  Metaclass::do_init_static();
  Environment::do_init_static();
  PTree::Encoding::do_init_static();

  PyObject *ir;
  const char *src, *cppfile;
  int primary_file_only, verbose, debug;
  if (!PyArg_ParseTuple(args, "Ossizzii",
                        &ir, &cppfile, &src,
                        &primary_file_only,
                        &syn_base_path,
                        &syn_sxr_prefix,
                        &verbose,
                        &debug))
    return 0;

  Py_INCREF(py_error);
  std::auto_ptr<Python::Object> error_type(new Python::Object(py_error));
  Py_INCREF(ir);

  if (verbose) ::verbose = true;
  if (debug) Trace::enable(Trace::ALL);
  if (primary_file_only) syn_primary_only = true;

  if (!src || *src == '\0')
  {
    PyErr_SetString(PyExc_RuntimeError, "no input file");
    return 0;
  }
  std::ifstream ifs(cppfile);
  if(!ifs)
  {
    PyErr_SetString(PyExc_RuntimeError, "unable to open output file");
    return 0;
  }

  std::set_unexpected(unexpected);
  ErrorHandler error_handler(error);

  // Setup the filter
  FileFilter filter(ir, src, syn_base_path, syn_primary_only);
  if (syn_sxr_prefix) filter.set_sxr_prefix(syn_sxr_prefix);

  AST::SourceFile *source_file = filter.get_sourcefile(src);
  // Run OCC to generate the IR
  try
  {
    Buffer buffer(ifs.rdbuf(), source_file->abs_name());
    Lexer lexer(&buffer, tokenset);
    SymbolFactory symbols(SymbolFactory::NONE);
    Parser parser(lexer, symbols, ruleset);

    PTree::Node *ptree = parser.parse();
    Parser::ErrorList const &errors = parser.errors();
    if (!errors.empty())
    {
      for (Parser::ErrorList::const_iterator i = errors.begin(); i != errors.end(); ++i)
        (*i)->write(std::cerr);
      throw std::runtime_error("The input contains errors.");
    }
    else if (ptree)
    {
      FileFilter* filter = FileFilter::instance();
      Builder builder(source_file);
      SWalker swalker(filter, &builder, &buffer);
      SXRGenerator *sxr_generator = 0;
      if (filter->should_xref(source_file))
      {
        sxr_generator = new SXRGenerator(filter, &swalker);
        swalker.set_store_links(sxr_generator);
      }
      swalker.translate(ptree);
      Translator translator(filter, ir);
      translator.set_builtin_decls(builder.builtin_decls());
      translator.translate(builder.scope());
      delete sxr_generator;
    }
  }
  catch (const std::exception &e)
  {
    Python::Object py_e((*error_type)(Python::Tuple(e.what())));
    PyErr_SetObject(py_error, py_e.ref());
    return 0;
  }
  catch (...)
  {
    Python::Object py_e((*error_type)(Python::Tuple("internal error")));
    PyErr_SetObject(py_error, py_e.ref());
    return 0;
  }

  PTree::cleanup_gc();

  // Delete all the AST:: and Types:: objects we created
  FakeGC::delete_all();
  return ir;
}

PyMethodDef methods[] = {{(char*)"parse", parse, METH_VARARGS},
			 {0}};
}

extern "C" void initParserImpl()
{
  Python::Module module = Python::Module::define("ParserImpl", methods);
  module.set_attr("version", "0.10");
  Python::Object processor = Python::Object::import("Synopsis.Processor");
  Python::Object error_base = processor.attr("Error");
  py_error = PyErr_NewException("ParserImpl.ParseError", error_base.ref(), 0);
  module.set_attr("ParseError", py_error);
}