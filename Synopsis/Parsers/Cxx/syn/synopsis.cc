#include "synopsis.hh"

#include <map>
using std::map;

#ifdef DO_TRACE
int Trace::level = 0;
#endif

#define assertObject(pyo) if (!pyo) PyErr_Print(); assert(pyo)

// This func is called so you can breakpoint on it
void nullObj() {
    cout << "Null ptr." << endl;
    int* i = 0;
    *i = 1;
}

//. A functor that returns true if the declaration is 'main'
struct is_main {
    is_main(bool onlymain, string mainfile) :
	m_onlymain(onlymain), m_mainfile(mainfile) {}
    bool operator()(AST::Declaration* decl) {
	return !m_onlymain || decl->filename() == m_mainfile;
    }
    bool m_onlymain;
    string m_mainfile;
};

int count_main(AST::Scope* scope, is_main& func)
{
    int count = 0;
    vector<AST::Declaration*>::iterator iter = scope->declarations().begin();
    while (iter != scope->declarations().end()) {
	AST::Scope* subscope = dynamic_cast<AST::Scope*>(*iter);
	if (subscope) count += count_main(subscope, func);
	count += func(*iter++);
    }
    return count;
}

// The compiler firewalled private stuff
struct Synopsis::Private {
    //. Constructor
    Private(Synopsis* s) : m_syn(s), m_main(false, s->m_mainfile) {
	m_cxx = PyString_InternFromString("C++");
	Py_INCREF(Py_None);
	add((AST::Declaration*)NULL, Py_None);
	Py_INCREF(Py_None);
	add((Type::Type*)NULL, Py_None);
    }
    //. Reference to parent synopsis object
    Synopsis* m_syn;
    //. Interned string for "C++"
    PyObject* m_cxx;
    //. Returns the string for "C++"
    PyObject* cxx() { Py_INCREF(m_cxx); return m_cxx; }
    //. is_main functor
    is_main m_main;
    // Sugar
    typedef map<void*, PyObject*> ObjMap;
    // Maps from C++ objects to PyObjects
    ObjMap obj_map;

    // Note that these methods always succeed
    
    //. Return the PyObject for the given AST::Declaration
    PyObject* py(AST::Declaration*);
    //. Return the PyObject for the given AST::Inheritance
    PyObject* py(AST::Inheritance*);
    //. Return the PyObject for the given AST::Parameter
    PyObject* py(AST::Parameter*);
    //. Return the PyObject for the given AST::Comment
    PyObject* py(AST::Comment*);
    //. Return the PyObject for the given Type::Type
    PyObject* py(Type::Type*);
    //. Return the PyObject for the given string
    PyObject* py(const string&);

    //. Add the given pair
    void add(void* cobj, PyObject* pyobj) {
	if (!pyobj) { nullObj(); }
	obj_map.insert(ObjMap::value_type(cobj, pyobj));
    }

    // Convert a vector to a List
    template <class T>
    PyObject* List(const vector<T*>& vec) {
	PyObject* list = PyList_New(vec.size());
	int index = 0;
	vector<T*>::const_iterator iter = vec.begin();
	while (iter != vec.end())
	    PyList_SET_ITEM(list, index++, py(*iter++));
	return list;
    }

    // Convert a vector to a Tuple
    template <class T>
    PyObject* Tuple(const vector<T*>& vec) {
	PyObject* tuple = PyTuple_New(vec.size());
	int index = 0;
	vector<T*>::const_iterator iter = vec.begin();
	while (iter != vec.end())
	    PyTuple_SET_ITEM(tuple, index++, py(*iter++));
	return tuple;
    }

    // Convert a string vector to a List
    PyObject* List(const vector<string>& vec) {
	PyObject* list = PyList_New(vec.size());
	int index = 0;
	vector<string>::const_iterator iter = vec.begin();
	while (iter != vec.end())
	    PyList_SET_ITEM(list, index++, py(*iter++));
	return list;
    }
    
    // Convert a string vector to a Tuple
    PyObject* Tuple(const vector<string>& vec) {
	PyObject* tuple = PyTuple_New(vec.size());
	int index = 0;
	vector<string>::const_iterator iter = vec.begin();
	while (iter != vec.end())
	    PyTuple_SET_ITEM(tuple, index++, py(*iter++));
	return tuple;
    }
    
};

PyObject* Synopsis::Private::py(AST::Declaration* decl)
{
    ObjMap::iterator iter = obj_map.find(decl);
    if (iter == obj_map.end()) {
	// Need to convert object first
	decl->accept(m_syn);
	iter = obj_map.find(decl);
	if (iter == obj_map.end()) {
	    cout << "Fatal: Still not PyObject after converting." << endl;
	    throw "Synopsis::Private::py(AST::Declaration*)";
	}
    }
    PyObject* obj = iter->second;
    Py_INCREF(obj);
    return obj;
}

PyObject* Synopsis::Private::py(AST::Inheritance* decl)
{
    ObjMap::iterator iter = obj_map.find(decl);
    if (iter == obj_map.end()) {
	// Need to convert object first
	decl->accept(m_syn);
	iter = obj_map.find(decl);
	if (iter == obj_map.end()) {
	    cout << "Fatal: Still not PyObject after converting." << endl;
	    throw "Synopsis::Private::py(AST::Inheritance*)";
	}
    }
    PyObject* obj = iter->second;
    Py_INCREF(obj);
    return obj;
}
PyObject* Synopsis::Private::py(AST::Parameter* decl)
{
    ObjMap::iterator iter = obj_map.find(decl);
    if (iter == obj_map.end()) {
	// Need to convert object first
	decl->accept(m_syn);
	iter = obj_map.find(decl);
	if (iter == obj_map.end()) {
	    cout << "Fatal: Still not PyObject after converting." << endl;
	    throw "Synopsis::Private::py(AST::Parameter*)";
	}
    }
    PyObject* obj = iter->second;
    Py_INCREF(obj);
    return obj;
}

PyObject* Synopsis::Private::py(AST::Comment* decl)
{
    ObjMap::iterator iter = obj_map.find(decl);
    if (iter == obj_map.end()) {
	// Need to convert object first
	m_syn->visitComment(decl);
	iter = obj_map.find(decl);
	if (iter == obj_map.end()) {
	    cout << "Fatal: Still not PyObject after converting." << endl;
	    throw "Synopsis::Private::py(AST::Comment*)";
	}
    }
    PyObject* obj = iter->second;
    Py_INCREF(obj);
    return obj;
}


PyObject* Synopsis::Private::py(Type::Type* type)
{
    ObjMap::iterator iter = obj_map.find(type);
    if (iter == obj_map.end()) {
	// Need to convert object first
	type->accept(m_syn);
	iter = obj_map.find(type);
	if (iter == obj_map.end()) {
	    cout << "Fatal: Still not PyObject after converting." << endl;
	    throw "Synopsis::Private::py(Type::Type*)";
	}
    }
    PyObject* obj = iter->second;
    Py_INCREF(obj);
    return obj;
}

PyObject* Synopsis::Private::py(const string& str)
{
    PyObject* pystr = PyString_FromStringAndSize(str.data(), str.size());
    PyString_InternInPlace(&pystr);
    return pystr;
}






//
// Class Synopsis
//

Synopsis::Synopsis(string mainfile, PyObject *decl, PyObject *dict)
        : m_declarations(decl), m_dictionary(dict), m_mainfile(mainfile)
{
    Trace trace("Synopsis::Synopsis");
    m_ast  = PyImport_ImportModule("Synopsis.Core.AST");
    assertObject(m_ast);
    m_type = PyImport_ImportModule("Synopsis.Core.Type");
    assertObject(m_type);

    m_onlymain = false;
    m = new Private(this);
}

Synopsis::~Synopsis()
{
    Trace trace("Synopsis::~Synopsis");
    /*
    PyObject *file = PyObject_CallMethod(scopes.back(), "declarations", 0);
    size_t size = PyList_Size(file);
    for (size_t i = 0; i != size; i++)
        PyObject_CallMethod(declarations, "append", "O", PyList_GetItem(file, i));
    */
    Py_DECREF(m_type);
    Py_DECREF(m_ast);
    delete m;
}

void Synopsis::onlyTranslateMain()
{
    m_onlymain = true;
    m->m_main.m_onlymain = true;
}

void Synopsis::translate(AST::Scope* scope)
{
    PyObject_CallMethod(m_declarations, "extend", "O",
	m->List(scope->declarations())
    );
}

//
// Type object factories
//

PyObject *Synopsis::Base(Type::Base* type)
{
    Trace trace("Synopsis::addBase");
    PyObject *name, *base = PyObject_CallMethod(m_type, "Base", "OO",
	m->cxx(), name = m->Tuple(type->name())
    );
    PyObject_SetItem(m_dictionary, name, base);
    return base;
}

PyObject *Synopsis::Forward(Type::Forward* type)
{
    Trace trace("Synopsis::addForward");
    PyObject *name, *forward = PyObject_CallMethod(m_type, "Base", "OO",
	m->cxx(), name = m->Tuple(type->name())
    );
    PyObject_SetItem(m_dictionary, name, forward);
    return forward;
}

PyObject *Synopsis::Declared(Type::Declared* type)
{
    Trace trace("Synopsis::addDeclared");
    PyObject *name, *declared = PyObject_CallMethod(m_type, "Declared", "OOO", 
	m->cxx(), name = m->Tuple(type->name()), m->py(type->declaration())
    );
    PyObject_SetItem(m_dictionary, name, declared);
    return declared;
}

PyObject *Synopsis::Template(Type::Template* type)
{
    Trace trace("Synopsis::addTemplate");
    PyObject *name, *templ = PyObject_CallMethod(m_type, "Template", "OOOO",
	m->cxx(), name = m->Tuple(type->name()), m->py(type->declaration()),
	m->List(type->parameters())
    );
    PyObject_SetItem(m_dictionary, name, templ);
    return templ;
}

PyObject *Synopsis::Modifier(Type::Modifier* type)
{
    Trace trace("Synopsis::addModifier");
    PyObject *modifier = PyObject_CallMethod(m_type, "Modifier", "OOOO",
	m->cxx(), m->py(type->alias()), m->List(type->pre()), m->List(type->post())
    );
    return modifier;
}

PyObject *Synopsis::Parameterized(Type::Parameterized* type)
{
    Trace trace("Synopsis::addParametrized");
    PyObject *parametrized = PyObject_CallMethod(m_type, "Parametrized", "OOO",
	m->cxx(), m->py(type->templateType()), m->List(type->parameters())
    );
    return parametrized;
}

PyObject *Synopsis::FuncPtr(Type::FuncPtr* type)
{
    Trace trace("Synopsis::addFunctionType");
    PyObject *func = PyObject_CallMethod(m_type, "Function", "OOOO",
	m->cxx(), m->py(type->returnType()), m->List(type->pre()),
	m->List(type->parameters())
    );
    return func;
}


//
// AST object factories
//

void Synopsis::addComments(PyObject* pydecl, AST::Declaration* cdecl)
{
    PyObject* comments = PyObject_CallMethod(pydecl, "comments", NULL);
    PyObject_CallMethod(comments, "extend", "O", m->List(cdecl->comments()));
    // Also set the accessability..
    PyObject_CallMethod(pydecl, "set_accessability", "i", int(cdecl->access()));
}

PyObject *Synopsis::Forward(AST::Forward* decl)
{
    Trace trace("Synopsis::addForward");
    PyObject *forward = PyObject_CallMethod(m_ast, "Forward", "OiiOOO", 
	m->py(decl->filename()), decl->line(), decl->filename() == m_mainfile, m->cxx(),
	m->py(decl->type()), m->Tuple(decl->name())
    );
    addComments(forward, decl);
    return forward;
}

PyObject *Synopsis::Comment(AST::Comment* decl)
{
    Trace trace("Synopsis::addComment");
    PyObject *text = PyString_FromStringAndSize(decl->text().data(), decl->text().size());
    PyObject *comment = PyObject_CallMethod(m_ast, "Comment", "OOi", 
	text, m->py(decl->filename()), decl->line()
    );
    return comment;
}

PyObject *Synopsis::Scope(AST::Scope* decl)
{
    Trace trace("Synopsis::addScope");
    PyObject *scope = PyObject_CallMethod(m_ast, "Scope", "OiiOOO", 
	m->py(decl->filename()), decl->line(), decl->filename() == m_mainfile, m->cxx(),
	m->py(decl->type()), m->Tuple(decl->name())
    );
    PyObject *decls = PyObject_CallMethod(scope, "declarations", NULL);
    PyObject_CallMethod(decls, "extend", "O", m->List(decl->declarations()));
    addComments(scope, decl);
    return scope;
}

PyObject *Synopsis::Namespace(AST::Namespace* decl)
{
    Trace trace("Synopsis::addNamespace");
    PyObject *module = PyObject_CallMethod(m_ast, "Module", "OiiOOO", 
	m->py(decl->filename()), decl->line(), decl->filename() == m_mainfile, m->cxx(),
	m->py(decl->type()), m->Tuple(decl->name())
    );
    PyObject *decls = PyObject_CallMethod(module, "declarations", NULL);
    PyObject_CallMethod(decls, "extend", "O", m->List(decl->declarations()));
    addComments(module, decl);
    return module;
}

PyObject *Synopsis::Inheritance(AST::Inheritance* decl)
{
    Trace trace("Synopsis::Inheritance");
    PyObject *inheritance = PyObject_CallMethod(m_ast, "Inheritance", "sOO", 
	"inherits", m->py(decl->parent()), m->List(decl->attributes())
    );
    return inheritance;
}

PyObject *Synopsis::Class(AST::Class* decl)
{
    Trace trace("Synopsis::addClass");
    PyObject *clas = PyObject_CallMethod(m_ast, "Class", "OiiOOO", 
	m->py(decl->filename()), decl->line(), decl->filename() == m_mainfile, m->cxx(),
	m->py(decl->type()), m->Tuple(decl->name())
    );
    // This is necessary to prevent inf. loops in several places
    m->add(decl, clas);
    PyObject *decls = PyObject_CallMethod(clas, "declarations", NULL);
    PyObject_CallMethod(decls, "extend", "O", m->List(decl->declarations()));
    PyObject *parents = PyObject_CallMethod(clas, "parents", NULL);
    PyObject_CallMethod(parents, "extend", "O", m->List(decl->parents()));
    if (decl->templateType()) {
	PyObject_CallMethod(clas, "set_template", "O", m->py(decl->templateType()));
    }
    addComments(clas, decl);
    return clas;
}

PyObject *Synopsis::Typedef(AST::Typedef* decl)
{
    Trace trace("Synopsis::addTypedef");
    // FIXME: what to do about the declarator?
    PyObject *tdef = PyObject_CallMethod(m_ast, "Typedef", "OiiOOOOiO", 
	m->py(decl->filename()), decl->line(), decl->filename() == m_mainfile, m->cxx(),
	m->py(decl->type()), m->Tuple(decl->name()),
	m->py(decl->alias()), decl->constructed(), m->py((AST::Declaration*)NULL)
    );
    addComments(tdef, decl);
    return tdef;
}

PyObject *Synopsis::Enumerator(AST::Enumerator* decl)
{
    Trace trace("Synopsis::addEnumerator");
    PyObject *enumor = PyObject_CallMethod(m_ast, "Enumerator", "OiiOOs", 
	m->py(decl->filename()), decl->line(), decl->filename() == m_mainfile, m->cxx(),
	m->Tuple(decl->name()), decl->value().c_str()
    );
    addComments(enumor, decl);
    return enumor;
}

PyObject *Synopsis::Enum(AST::Enum* decl)
{
    Trace trace("Synopsis::addEnum");
    PyObject *enumor = PyObject_CallMethod(m_ast, "Enum", "OiiOOO", 
	m->py(decl->filename()), decl->line(), decl->filename() == m_mainfile, m->cxx(),
	m->Tuple(decl->name()), m->List(decl->enumerators())
    );
    addComments(enumor, decl);
    return enumor;
}

PyObject *Synopsis::Variable(AST::Variable* decl)
{
    Trace trace("Synopsis::addVariable");
    PyObject *var = PyObject_CallMethod(m_ast, "Variable", "OiiOOOOiO", 
	m->py(decl->filename()), decl->line(), decl->filename() == m_mainfile, m->cxx(),
	m->py(decl->type()), m->Tuple(decl->name()),
	m->py(decl->vtype()), decl->constructed(), m->py((AST::Declaration*)NULL)
    );
    addComments(var, decl);
    return var;
}

PyObject *Synopsis::Const(AST::Const* decl)
{
    Trace trace("Synopsis::addConst");
    PyObject *cons = PyObject_CallMethod(m_ast, "Const", "OiiOOOOOs", 
	m->py(decl->filename()), decl->line(), decl->filename() == m_mainfile, m->cxx(),
	m->py(decl->type()),
	m->py(decl->ctype()), m->Tuple(decl->name()), decl->value().c_str()
    );
    addComments(cons, decl);
    return cons;
}

PyObject *Synopsis::Parameter(AST::Parameter* decl)
{
    Trace trace("Synopsis::Parameter");
    PyObject *param = PyObject_CallMethod(m_ast, "Parameter", "OOOOO", 
	m->py(decl->premodifier()), m->py(decl->type()), m->py(decl->postmodifier()),
	m->py(decl->name()), m->py(decl->value())
    );
    return param;
}

PyObject *Synopsis::Function(AST::Function* decl)
{
    Trace trace("Synopsis::addFunction");
    AST::Name realname = decl->name();
    realname.back() = decl->realname();
    PyObject *func = PyObject_CallMethod(m_ast, "Function", "OiiOOOOOO", 
	m->py(decl->filename()), decl->line(), decl->filename() == m_mainfile, m->cxx(),
	m->py(decl->type()), m->List(decl->premodifier()), m->py(decl->returnType()),
	m->Tuple(decl->name()), m->Tuple(realname)
    );
    PyObject* params = PyObject_CallMethod(func, "parameters", NULL);
    PyObject_CallMethod(params, "extend", "O", m->List(decl->parameters()));
    addComments(func, decl);
    return func;
}

PyObject *Synopsis::Operation(AST::Operation* decl)
{
    Trace trace("Synopsis::addOperation");
    AST::Name realname = decl->name();
    realname.back() = decl->realname();
    PyObject *oper = PyObject_CallMethod(m_ast, "Operation", "OiiOOOOOO", 
	m->py(decl->filename()), decl->line(), decl->filename() == m_mainfile, m->cxx(),
	m->py(decl->type()), m->List(decl->premodifier()), m->py(decl->returnType()),
	m->Tuple(decl->name()), m->Tuple(realname)
    );
    PyObject* params = PyObject_CallMethod(oper, "parameters", NULL);
    PyObject_CallMethod(params, "extend", "O", m->List(decl->parameters()));
    addComments(oper, decl);
    return oper;
}



////////////////MISC CRAP

/*
void Synopsis::Inheritance(Inheritance* type)
{
    PyObject *to = PyObject_CallMethod(clas, "parents", 0);
    PyObject *from = V2L(parents);
    size_t size = PyList_Size(from);
    for (size_t i = 0; i != size; ++i)
        PyList_Append(to, PyList_GetItem(from, i));
    Py_DECREF(to);
    Py_DECREF(from);
}

PyObject *Synopsis::N2L(const string &name)
{
    Trace trace("Synopsis::N2L");
    vector<string> scope;
    string::size_type b = 0;
    while (b < name.size())
    {
        string::size_type e = name.find("::", b);
        scope.push_back(name.substr(b, e == string::npos ? e : e - b));
        b = e == string::npos ? string::npos : e + 2;
    }
    PyObject *pylist = PyList_New(scope.size());
    for (size_t i = 0; i != scope.size(); ++i)
        PyList_SetItem(pylist, i, PyString_FromString(scope[i].c_str()));
    return pylist;
}

PyObject *Synopsis::V2L(const vector<string> &strings)
{
    Trace trace("Synopsis::V2L(vector<string>)");
    PyObject *pylist = PyList_New(strings.size());
    for (size_t i = 0; i != strings.size(); ++i)
        PyList_SetItem(pylist, i, PyString_FromString(strings[i].c_str()));
    return pylist;
}

PyObject *Synopsis::V2L(const vector<PyObject *> &objs)
{
    Trace trace("Synopsis::V2L(vector<PyObject*>)");
    PyObject *pylist = PyList_New(objs.size());
    for (size_t i = 0; i != objs.size(); ++i)
        PyList_SetItem(pylist, i, objs[i]);
    return pylist;
}

PyObject *Synopsis::V2L(const vector<size_t> &sizes)
{
    //Trace trace("Synopsis::V2L");
    PyObject *pylist = PyList_New(sizes.size());
    for (size_t i = 0; i != sizes.size(); ++i)
        PyList_SetItem(pylist, i, PyInt_FromLong(sizes[i]));
    return pylist;
}

void Synopsis::Declaration(Declaration* type)
{
    PyObject *scope = scopes.back();
    PyObject *declarations = PyObject_CallMethod(scope, "declarations", 0);
    PyObject_CallMethod(declarations, "append", "O", declaration);
    PyObject_CallMethod(declaration, "set_accessability", "i", m_accessability);
}
*/

//
// AST::Visitor methods
//
/*void Synopsis::visitDeclaration(AST::Declaration* decl) {
    m->add(decl, this->Declaration(decl));
}*/
void Synopsis::visitScope(AST::Scope* decl) {
    if (count_main(decl, m->m_main))
	m->add(decl, Scope(decl));
    else
	m->add(decl, Forward(new Type::Forward(decl->name())));
}
void Synopsis::visitNamespace(AST::Namespace* decl) {
    if (count_main(decl, m->m_main))
	m->add(decl, Namespace(decl));
    else
	m->add(decl, Forward(new Type::Forward(decl->name())));
}
void Synopsis::visitClass(AST::Class* decl) {
    if (count_main(decl, m->m_main))
	m->add(decl, Class(decl));
    else
	m->add(decl, Forward(new Type::Forward(decl->name())));
}
void Synopsis::visitForward(AST::Forward* decl) {
    if (m->m_main(decl))
	m->add(decl, Forward(decl));
    else
	m->add(decl, Forward(new Type::Forward(decl->name())));
}
void Synopsis::visitTypedef(AST::Typedef* decl) {
    if (m->m_main(decl))
	m->add(decl, Typedef(decl));
    else
	m->add(decl, Forward(new Type::Forward(decl->name())));
}
void Synopsis::visitVariable(AST::Variable* decl) {
    if (m->m_main(decl))
	m->add(decl, Variable(decl));
    else
	m->add(decl, Forward(new Type::Forward(decl->name())));
}
void Synopsis::visitConst(AST::Const* decl) {
    if (m->m_main(decl))
	m->add(decl, Const(decl));
    else
	m->add(decl, Forward(new Type::Forward(decl->name())));
}
void Synopsis::visitEnum(AST::Enum* decl) {
    if (m->m_main(decl))
	m->add(decl, Enum(decl));
    else
	m->add(decl, Forward(new Type::Forward(decl->name())));
}
void Synopsis::visitEnumerator(AST::Enumerator* decl) {
    m->add(decl, Enumerator(decl));
}
void Synopsis::visitFunction(AST::Function* decl) {
    if (m->m_main(decl))
	m->add(decl, Function(decl));
    else
	m->add(decl, Forward(new Type::Forward(decl->name())));
}
void Synopsis::visitOperation(AST::Operation* decl) {
    if (m->m_main(decl))
	m->add(decl, Operation(decl));
    else
	m->add(decl, Forward(new Type::Forward(decl->name())));
}

void Synopsis::visitInheritance(AST::Inheritance* decl) {
    m->add(decl, Inheritance(decl));
}
void Synopsis::visitParameter(AST::Parameter* decl) {
    m->add(decl, Parameter(decl));
}
void Synopsis::visitComment(AST::Comment* decl) {
    m->add(decl, Comment(decl));
}

//
// Type::Visitor methods
//
/*void Synopsis::visitType(Type::Type* type) {
    m->add(type, this->Type(type));
}*/
void Synopsis::visitForward(Type::Forward* type) {
    m->add(type, Forward(type));
}
void Synopsis::visitModifier(Type::Modifier* type) {
    m->add(type, Modifier(type));
}
/*void Synopsis::visitNamed(Type::Named* type) {
    m->add(type, Named(type));
}*/
void Synopsis::visitBase(Type::Base* type) {
    m->add(type, Base(type));
}
void Synopsis::visitDeclared(Type::Declared* type) {
    m->add(type, Declared(type));
}
void Synopsis::visitTemplateType(Type::Template* type) {
    m->add(type, Template(type));
}
void Synopsis::visitParameterized(Type::Parameterized* type) {
    m->add(type, Parameterized(type));
}
void Synopsis::visitFuncPtr(Type::FuncPtr* type) {
    m->add(type, FuncPtr(type));
}


