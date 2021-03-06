#include <Synopsis/Trace.hh>
#include <Synopsis/Buffer.hh>
#include <Synopsis/Lexer.hh>
#include <Synopsis/Parser.hh>
#include <Synopsis/PTree.hh>
#include <Synopsis/PTree/Display.hh>
#include <Synopsis/PTree/Writer.hh>
#include <Synopsis/SymbolTable.hh>
#include <Synopsis/TypeAnalysis.hh>
#include <iostream>
#include <iomanip>
#include <fstream>

using namespace Synopsis;

//. Evaluating types of expressions may involve
//. overload resolution, if the types of the subexpressions
//. are user defined (enums, classes).
//. As this is a unit test for type evaluation, not overload
//. resolution, we restrict ourselfs to builtin types.
//.
//. Test input should be a set of declarations where
//. the initializers are expressions which we look up
//. the type for.
class InitializerFinder : private SymbolTable::Walker
{
public:
  InitializerFinder(SymbolTable::Scope *scope, std::ostream &os)
    : SymbolTable::Walker(scope), my_os(os) {}
  void find(PTree::Node *node) { node->accept(this);}

private:
  virtual void visit(PTree::Declaration *node)
  {
    PTree::Node *type = PTree::second(node);
    type->accept(this);
    PTree::Node *rest = PTree::third(node);
    if (rest->is_atom()) return; // ';'
    for (; rest; rest = rest->cdr())
    {
      PTree::Node *p = rest->car();
      p->accept(this);
    }
  }
  virtual void visit(PTree::Declarator *decl)
  {
    size_t length = PTree::length(decl);
    if (length >= 2 && *PTree::nth(decl, length - 2) == '=')
    {
      PTree::Node *init = PTree::tail(decl, length - 1)->car();
      // do the type evaluation here...
      std::cout << "Expression : " << PTree::reify(init) << std::endl;
      TypeAnalysis::Type const *type = TypeAnalysis::type_of(init, current_scope());
//       std::cout << "Type : " << type << std::endl;
//       std::cout << "Type : " << type.is_const() << std::endl;
//       std::cout << "Type : " << type.is_builtin_type() << std::endl;
//       std::cout << "Type : " << type << std::endl;
    }
  }

  std::ostream &my_os;
};

int main(int argc, char **argv)
{
  if (argc < 3)
  {
    std::cerr << "Usage: " << argv[0] << " [-d] <output> <input>" << std::endl;
    exit(-1);
  }
  try
  {
    std::string output;
    std::string input;
    if (argv[1] == std::string("-d"))
    {
      Trace::enable(Trace::ALL);
      output = argv[2];
      input = argv[3];
    }
    else
    {
      output = argv[1];
      input = argv[2];
    }
    std::ofstream ofs;
    {
      if (output != "-")
	ofs.open(output.c_str());
      else
      {
	ofs.copyfmt(std::cout);
	static_cast<std::basic_ios<char> &>(ofs).rdbuf(std::cout.rdbuf());
      }
    }
    std::ifstream ifs(input.c_str());
    Buffer buffer(ifs.rdbuf(), input);
    Lexer lexer(&buffer);
    SymbolFactory symbols;
    Parser parser(lexer, symbols);
    PTree::Node *node = parser.parse();
    InitializerFinder finder(symbols.current_scope(), ofs);
    finder.find(node);
  }
  catch (std::exception const &e)
  {
    std::cerr << "Caught exception : " << e.what() << std::endl;
  }
}
