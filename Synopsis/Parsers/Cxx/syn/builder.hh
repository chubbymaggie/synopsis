// File: builder.hh

#ifndef H_SYNOPSIS_CPP_BUILDER
#define H_SYNOPSIS_CPP_BUILDER

#include "ast.hh"
#include <stack.h>

// Forward declare some Type::Types
namespace Type {
    class Type;
    class Forward;
    class Template;
}

typedef vector<string> Name;

//. AST Builder.
//. This class manages the building of an AST, including queries on the
//. existing AST such as name and type lookups. The building operations are
//. called by SWalker as it walks the parse tree.
class Builder {
public:
    //. Constructor
    Builder();
    //. Destructor. Recursively destroys all AST objects
    ~Builder();

    //
    // AST Methods
    //

    //. Returns the current scope
    AST::Scope* scope() { return m_scope; }

    //. Add the given Declaration to the current scope
    void add(AST::Declaration*);

    //. Construct and open a new Namespace. The Namespace is becomes the
    //. current scope, and the old one is pushed onto the stack.
    AST::Namespace* startNamespace(string name);

    //. End the current namespace and pop the previous Scope off the stack
    void endNamespace();

    //. Construct and open a new Class. The Class becomes the current scope,
    //. and the old one is pushed onto the stack. The type argument is the
    //. type, ie: "class" or "struct". This is tested to determine the default
    //. accessability.
    AST::Class* startClass(string type, string name);

    //. End the current class and pop the previous Scope off the stack
    void endClass();

    //. Add an operation
    AST::Operation* addOperation(int, string name, vector<string> premod, Type::Type* ret, string realname);

    //. Add a variable
    AST::Variable* addVariable(int, string name, Type::Type* vtype, bool constr);

    //
    // Type Methods
    //

    //. Create a Forward type for the given name in the current scope
    Type::Forward* Forward(string name);

    //. Create a Template type for the given name in the current scope
    Type::Template* Template(string name, const vector<Type::Type*>&); 

private:
    //. Current filename
    string m_filename;

    //. Current scope object
    AST::Scope* m_scope;

    //. Stack of containing scopes
    stack<AST::Scope*> m_scope_stack;


}; // class Builder

#endif
