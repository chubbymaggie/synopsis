//
// Copyright (C) 2011 Stefan Seefeld
// All rights reserved.
// Licensed to the public under the terms of the GNU LGPL (>= 2),
// see the file COPYING for details.
//

#include "ASGTranslator.hh"
#include <Support/utils.hh>
#include <Support/path.hh>
#include <iostream>
#include <sstream>
#include <stdexcept>

using namespace Synopsis;

namespace
{
inline bpl::dict annotations(bpl::object o) 
{ return bpl::extract<bpl::dict>(o.attr("annotations"));}
inline bpl::list comments(bpl::object o) 
{ return bpl::extract<bpl::list>(annotations(o).get("comments"));}

void cv_qual(CXType t, bpl::list mods)
{
  if (clang_isConstQualifiedType(t))
    mods.append("const");
  if (clang_isVolatileQualifiedType(t))
    mods.append("volatile");
}

// libclang doesn't report Macro definition details (such as parameters)
// so we tokenize and 'parse' the range of the macro definition here.
class MacroDefinition
{
public:
  MacroDefinition(CXTranslationUnit tu, CXCursor c)
    : is_function_(false)
  {
    CXToken *tokens;
    unsigned num_tokens;
    clang_tokenize(tu, clang_getCursorExtent(c), &tokens, &num_tokens);
    if (!num_tokens) return;
    // <macro-name> '(' <arg> [',' <args>] ')'
    for (unsigned i = 1; i != num_tokens; ++i) 
    {
      is_function_ = true;
      CXString t = clang_getTokenSpelling(tu, tokens[i]);
      char const *s = clang_getCString(t);
      // if we see a ')' it means we are done with the parameter list.
      if (*s == ')')
      {
	clang_disposeString(t);
	clang_disposeTokens(tu, tokens, num_tokens);  
	return;
      }
      // every other token is punktuation: '(' ','...')'
      else if (!(i%2))
      {
	parameters_.append(s);
      }
      clang_disposeString(t);
    }
    clang_disposeTokens(tu, tokens, num_tokens);  
  }

  bool is_function() const { return is_function_;}
  bpl::list parameters() const { return parameters_;}
private:
  bool is_function_;
  bpl::list parameters_;
};


class Stringifier
{
public:
  Stringifier(CXTranslationUnit tu) : tu_(tu) {}
  std::string stringify(CXCursor parent)
  {
    value_ = "";
    clang_visitChildren(parent, &Stringifier::visit, this);
    return value_;
  }
private:

  static CXChildVisitResult visit(CXCursor c, CXCursor p, CXClientData d)
  {
    Stringifier *stringifier = static_cast<Stringifier *>(d);

    CXString k = clang_getCursorKindSpelling(c.kind);
    std::string kind = clang_getCString(k);
    clang_disposeString(k);
    stringifier->value_ += stringify_range(stringifier->tu_, clang_getCursorExtent(c));
    return CXChildVisit_Continue;
  }

  CXTranslationUnit tu_;
  std::string value_;
};

class UsingDirectiveDereferencer
{
public:
  UsingDirectiveDereferencer() {}
  CXCursor reference(CXCursor parent)
  {
    clang_visitChildren(parent, &UsingDirectiveDereferencer::visit, this);
    return r_;
  }
private:

  static CXChildVisitResult visit(CXCursor c, CXCursor p, CXClientData d)
  {
    UsingDirectiveDereferencer *visitor = static_cast<UsingDirectiveDereferencer *>(d);
    if (c.kind == CXCursor_NamespaceRef)
      visitor->r_ = clang_getCursorReferenced(c);
    // The referenced name may be qualified, in which case we'll iterate over all scopes.
    // We are interested into the last cursor in this iteration.
    return CXChildVisit_Continue;
  }

  CXCursor r_;
};

class BaseSpecVisitor
{
public:
  BaseSpecVisitor(TypeRepository &types)
    : asg_module_(bpl::import("Synopsis.ASG")),
      types_(types)
  {
    bpl::object qname_module = bpl::import("Synopsis.QualifiedName");
    qname_ = qname_module.attr("QualifiedCxxName");  
  }

  bpl::list find_bases(CXCursor parent)
  {
    clang_visitChildren(parent, &BaseSpecVisitor::visit, this);
    return bases_;
  }
private:

  bpl::object qname(std::string const &name) { return qname_(bpl::make_tuple(name));}
  CXChildVisitResult visit(CXCursor c)
  {
    switch (c.kind)
    {
      case CXCursor_CXXBaseSpecifier:
      {
	bpl::object parent = types_.lookup(clang_getCursorType(c));
	bpl::list attributes;
	if (clang_isVirtualBase(c))
	  attributes.append("virtual");
	attributes.append(access_spec(clang_getCXXAccessSpecifier(c)));
	bases_.append(asg_module_.attr("Inheritance")("inherits", parent, attributes));
        return CXChildVisit_Continue;
      }
      default:
	// Unfortunately there is no way to only visit base specifiers,
	// making the whole traversal rather inefficient.
        return CXChildVisit_Continue;
    }
    // If we are here, we are past the base specifiers, and can abort.
    return CXChildVisit_Break;
  }
  static CXChildVisitResult visit(CXCursor c, CXCursor p, CXClientData d)
  {
    BaseSpecVisitor *visitor = static_cast<BaseSpecVisitor*>(d);
    return visitor->visit(c);
  }
  static char const *access_spec(CX_CXXAccessSpecifier s)
  {
    switch (s)
    {
      case CX_CXXPublic: return "public";
      case CX_CXXProtected: return "protected";
      case CX_CXXPrivate: return "private";
      default: throw std::runtime_error("invalid access specifier");
    }
  };

  bpl::object asg_module_;
  bpl::object qname_;
  TypeRepository &types_;
  bpl::list bases_;
};

class ParamVisitor
{
public:
  ParamVisitor(SymbolTable &symbols, TypeRepository &types)
    : asg_module_(bpl::import("Synopsis.ASG")),
      symbols_(symbols),
      types_(types) 
  {
    bpl::object qname_module = bpl::import("Synopsis.QualifiedName");
    qname_ = qname_module.attr("QualifiedCxxName");  
  }

  bpl::list translate_function_parameters(CXCursor parent)
  {
    clang_visitChildren(parent, &ParamVisitor::visit_function_parameters, this);
    return params_;
  }
  bpl::list translate_template_parameters(CXCursor parent)
  {
    clang_visitChildren(parent, &ParamVisitor::visit_template_parameters, this);
    return params_;
  }
private:

  bpl::object qname(std::string const &name) { return qname_(bpl::make_tuple(name));}
  bpl::object create(CXCursor c)
  {
    CXString n = clang_getCursorSpelling(c);
    std::string name = clang_getCString(n);
    clang_disposeString(n);
    switch (c.kind)
    {
      case CXCursor_ParmDecl:
      {
	bpl::object type = types_.lookup(clang_getCursorType(c));
	return asg_module_.attr("Parameter")(bpl::list(), // premod
					     type,
					     bpl::list(), // postmod
					     name,
					     bpl::object()); // value
      }
      case CXCursor_TemplateTypeParameter:
      {
	bpl::object type = asg_module_.attr("DependentTypeId")("C++", qname("typename"));
	return asg_module_.attr("Parameter")(bpl::list(), // premod
					     type,
					     bpl::list(), // postmod
					     name,
					     bpl::object()); // value
      }
      case CXCursor_NonTypeTemplateParameter:
      {
	bpl::object type = types_.lookup(clang_getCursorType(c));
	return asg_module_.attr("Parameter")(bpl::list(), // premod
					     type,
					     bpl::list(), // postmod
					     name,
					     bpl::object()); // value
      }
      default:
	throw std::runtime_error("unimplemented: " + cursor_info(c));
    }
  }
  static CXChildVisitResult visit_function_parameters(CXCursor c, CXCursor p, CXClientData d)
  {
    ParamVisitor *visitor = static_cast<ParamVisitor*>(d);
    switch (c.kind)
    {
      case CXCursor_TemplateTypeParameter:
      case CXCursor_TemplateTemplateParameter:
      case CXCursor_NonTypeTemplateParameter:
	return CXChildVisit_Continue; // ignore template parameters
      case CXCursor_ParmDecl:
      {
	bpl::object o = visitor->create(c);
	// parameters aren't declared. We need them in the symbol table anyhow.
	visitor->symbols_.declare(c, o);
        visitor->params_.append(o);
	break;
      }
      default:
	break;
    }
    return CXChildVisit_Continue;
  }

  static CXChildVisitResult visit_template_parameters(CXCursor c, CXCursor p, CXClientData d)
  {
    ParamVisitor *visitor = static_cast<ParamVisitor*>(d);
    switch (c.kind)
    {
      case CXCursor_ParmDecl:
	return CXChildVisit_Continue; // ignore function parameters
      case CXCursor_TemplateTypeParameter:
      case CXCursor_NonTypeTemplateParameter:
      {
	bpl::object o = visitor->create(c);
	// parameters aren't declared. We need them in the symbol table anyhow.
	visitor->symbols_.declare(c, o);
        visitor->params_.append(o);
	break;
      }
      case CXCursor_TemplateTemplateParameter:
	break; // TBD
      default:
	break;
    }
    return CXChildVisit_Continue;
  }

  bpl::object asg_module_;
  bpl::object qname_;
  SymbolTable &symbols_;
  TypeRepository &types_;
  bpl::list params_;

};

}

TypeRepository::TypeRepository(bpl::dict types, bool verbose)
  : asg_module_(bpl::import("Synopsis.ASG")),
    types_(types),
    verbose_(verbose)
{
  bpl::object qname_module = bpl::import("Synopsis.QualifiedName");
  qname_ = qname_module.attr("QualifiedCxxName");  

#define DECLARE_BUILTIN_TYPE(T) types_[qname(T)] = asg_module_.attr("BuiltinTypeId")("C++", qname(T))

  DECLARE_BUILTIN_TYPE("bool");
  DECLARE_BUILTIN_TYPE("char");
  DECLARE_BUILTIN_TYPE("unsigned char");
  DECLARE_BUILTIN_TYPE("signed char");
  DECLARE_BUILTIN_TYPE("short");
  DECLARE_BUILTIN_TYPE("unsigned short");
  DECLARE_BUILTIN_TYPE("int");
  DECLARE_BUILTIN_TYPE("unsigned int");
  DECLARE_BUILTIN_TYPE("long");
  DECLARE_BUILTIN_TYPE("unsigned long");
  DECLARE_BUILTIN_TYPE("long long");
  DECLARE_BUILTIN_TYPE("unsigned long long");
  DECLARE_BUILTIN_TYPE("int");
  DECLARE_BUILTIN_TYPE("unsigned int");
  DECLARE_BUILTIN_TYPE("float");
  DECLARE_BUILTIN_TYPE("double");
  DECLARE_BUILTIN_TYPE("void");
  DECLARE_BUILTIN_TYPE("...");
  DECLARE_BUILTIN_TYPE("long double");
  DECLARE_BUILTIN_TYPE("wchar_t");
  // some GCC extensions...
  DECLARE_BUILTIN_TYPE("__builtin_va_list");

#undef DECLARE_BUILTIN_TYPE
}

void TypeRepository::declare(CXType t, bpl::object declaration, bool visible)
{
  if (verbose_)
    std::cout << "declare " << type_info(t) << std::endl;
  bpl::object name = declaration.attr("name");
  bpl::object type;
  if (visible) type = asg_module_.attr("DeclaredTypeId")("C++", name, declaration);
  else type = asg_module_.attr("UnknownTypeId")("C++", name, declaration);
  types_[name] = type;
  // We also declare objects without a corresponding type, such as macro definitions.
  if (t.kind != CXType_Invalid)
    cx_types_[t] = type;
}

bpl::object TypeRepository::lookup(CXType t) const
{
  if (verbose_)
    std::cout << "lookup " << type_info(t) << std::endl;
  switch (t.kind)
  {
    case CXType_Void: return types_[qname("void")];
    case CXType_Bool: return types_[qname("bool")];
    case CXType_UChar: return types_[qname("unsigned char")];
    case CXType_UShort: return types_[qname("unsigned short")];
    case CXType_UInt: return types_[qname("unsigned int")];
    case CXType_ULong: return types_[qname("unsigned long")];
    case CXType_ULongLong: return types_[qname("unsigned long long")];
    case CXType_SChar: return types_[qname("signed char")];
    case CXType_Char_S: return types_[qname("char")];
    case CXType_WChar: return types_[qname("wchar_t")];
    case CXType_Short: return types_[qname("short")];
    case CXType_Int: return types_[qname("int")];
    case CXType_Long: return types_[qname("long")];
    case CXType_LongLong: return types_[qname("long long")];
    case CXType_Float: return types_[qname("float")];
    case CXType_Double: return types_[qname("double")];
    case CXType_LongDouble: return types_[qname("long double")];
    case CXType_Typedef: return lookup(clang_getCanonicalType(t));
    case CXType_LValueReference:
    {
      CXType i = clang_getPointeeType(t);
      bpl::list postmod;
      cv_qual(i, postmod);
      postmod.append("&");
      bpl::object inner = lookup(i);
      return asg_module_.attr("ModifierTypeId")("C++", inner, bpl::list(), postmod);
    }
    case CXType_Pointer:
    {
      CXType i = clang_getPointeeType(t);
      bpl::list postmod;
      cv_qual(i, postmod);
      postmod.append("*");
      bpl::object inner = lookup(i);
      return asg_module_.attr("ModifierTypeId")("C++", inner, bpl::list(), postmod);
    }
    case CXType_ConstantArray:
    {
      CXType i = clang_getArrayElementType(t);
      bpl::object inner = lookup(i);
      bpl::list sizes;
      sizes.append(clang_getArraySize(t));
      return asg_module_.attr("ArrayTypeId")("C++", inner, sizes);
    }
    case CXType_Unexposed:
    {
      // FIXME: Find a way to use the actual type name (stringified ?), instead of
      // just '<unknown>'

      // This may be a dependent type.
      // if (clang_isDependentType(t))
      // 	return asg_module_.attr("UnknownTypeId")("C++", qname("<dependent>"));
      return asg_module_.attr("UnknownTypeId")("C++", qname("<unknown>"));
    }
    case CXType_Dependent:
    {
      // FIXME: Find a way to use the actual type name (stringified ?), instead of
      // just '<unknown>'

      return asg_module_.attr("UnknownTypeId")("C++", qname("<dependent>"));
    }
    default:
    {
      bpl::object type = cx_types_[t];
      if (!type)
	// throw std::runtime_error("undefined type " + type_info(t));
	type = asg_module_.attr("UnknownTypeId")("C++", qname("<unknown>"));
      return type;
    }
  };
}

ASGTranslator::ASGTranslator(std::string const &filename,
			     std::string const &base_path, bool primary_file_only,
			     bpl::object asg, bpl::dict files,
			     bool v, bool d)
  : asg_module_(bpl::import("Synopsis.ASG")),
    sf_module_(bpl::import("Synopsis.SourceFile")),
    files_(files),
    types_(bpl::extract<bpl::dict>(asg.attr("types"))(), v),
    primary_filename_(filename),
    primary_file_only_(primary_file_only),
    base_path_(base_path),
    verbose_(v),
    debug_(d)
{
  bpl::object qname_module = bpl::import("Synopsis.QualifiedName");
  qname_ = qname_module.attr("QualifiedCxxName");
  declarations_ = bpl::extract<bpl::list>(asg.attr("declarations"))();
  // determine canonical filenames
  std::string long_filename = Synopsis::make_full_path(primary_filename_);
  std::string short_filename = Synopsis::make_short_path(primary_filename_, base_path_);

  bpl::object file = files_.get(short_filename);
  if (file)
    file_ = file;
  else
  {
    file_ = sf_module_.attr("SourceFile")(short_filename, long_filename, "C++");
    files_[short_filename] = file_;
  }
  annotations(file_)["primary"] = true;
}

void ASGTranslator::translate(CXTranslationUnit tu)
{
  tu_ = tu; // save to make tu accessible elsewhere (tokenization)
  CXFile f = clang_getFile(tu, primary_filename_.c_str());
  comment_horizon_ = clang_getLocationForOffset(tu, f, 0);
  // prev_cursor_.push(clang_getNullCursor())
  clang_visitChildren(clang_getTranslationUnitCursor(tu), &ASGTranslator::visit, this);
}

bool ASGTranslator::is_visible(CXCursor c)
{
  // Whether a cursor is visible depends on the file it is positioned in.
  // If 'primary_file_only_' is true, only 'primary_filename_' is accepted.
  // Otherwise, all files that match the given 'base_path_' are.
  CXSourceLocation l = clang_getCursorLocation(c);
  CXFile sf;
  clang_getSpellingLocation(l, &sf, 0 /*line*/, /*column*/ 0, /*offset*/ 0);
  CXString f = clang_getFileName(sf);
  char const *s = clang_getCString(f);
  std::string filename = s ? make_full_path(s) : "";
  bool visible = !filename.empty() &&                     // not a builtin entity
    (primary_file_only_ ? primary_filename_ == filename : // a primary file
     matches_path(filename, base_path_));                 // or inside the base_path
  clang_disposeString(f);
  return visible;
}

bpl::object ASGTranslator::get_source_file(std::string const &filename)
{
  std::string long_filename = make_full_path(filename);
  std::string short_filename = make_short_path(filename, base_path_);

  bpl::object file = files_.get(short_filename);
  if (!file)
  {
    file = sf_module_.attr("SourceFile")(short_filename, long_filename, "C++");
    if (base_path_.empty() || matches_path(long_filename, base_path_))
      annotations(file)["primary"] = true;
    files_[short_filename] = file;
  }
  return file;
}

bpl::object ASGTranslator::qname(std::string const &name)
{
  if (scope_.size())
    return scope_.top().attr("name") + bpl::make_tuple(name);
  else
    return qname_(bpl::make_tuple(name));
}

void ASGTranslator::declare(CXCursor c, bpl::object d)
{
  if (scope_.size())
    bpl::extract<bpl::list>(scope_.top().attr("declarations"))().append(d);
  else
    declarations_.append(d);
  bpl::extract<bpl::list>(file_.attr("declarations"))().append(d);
  symbols_.declare(c, d);
}

bpl::object ASGTranslator::create(CXCursor c)
{
  if (verbose_)
    std::cout << "create " << cursor_info(c) << std::endl;
  CXString k = clang_getCursorKindSpelling(c.kind);
  CXString n = clang_getCursorSpelling(c);
  std::string kind = clang_getCString(k);
  std::string name = clang_getCString(n);
  clang_disposeString(n);
  clang_disposeString(k);
  CXFile sf;
  unsigned line;
  CXSourceLocation l = clang_getCursorLocation(c);
  clang_getSpellingLocation(l, &sf, &line, /*column*/ 0, /*offset*/ 0);
  CXString f = clang_getFileName(sf);
  std::string file = clang_getCString(f);
  clang_disposeString(f);
  bpl::object source_file = get_source_file(file);
  if (name.empty() && c.kind != CXCursor_Namespace)
    // Anonymous namespaces are handled differently.
    name = make_anonymous_name(primary_filename_);
  switch (c.kind)
  {
    case CXCursor_InclusionDirective:
    {
      CXToken *tokens;
      unsigned num_tokens;
      clang_tokenize(tu_, clang_getCursorExtent(c), &tokens, &num_tokens);
      // The first token is '#', the second 'include' or 'include_next',
      // and the third starts either with '"' or '<'
      // Due to a libclang bug, in some cases the '<' is the last token.
      // We extract the header name otherwise, and thus have all the info we need.
      CXString i = clang_getTokenSpelling(tu_, tokens[1]);
      bool is_next = std::string("include_next") == clang_getCString(i);
      clang_disposeString(i);
      CXString header_start = clang_getTokenSpelling(tu_, tokens[2]);
      char s = clang_getCString(header_start)[0];
      CXFile header = clang_getIncludedFile(c);
      CXString h = clang_getFileName(header);
      std::string file = clang_getCString(h);
      clang_disposeString(h);
      bpl::object target = get_source_file(file);
      bool is_macro = false;
      if (s == '"')
	name = clang_getCString(header_start);
      else if (s == '<')
	name = '<' + name + '>';
      else
      {
	name = clang_getCString(header_start);
	is_macro = true;
      }
      clang_disposeString(header_start);
      clang_disposeTokens(tu_, tokens, num_tokens);  
      bpl::object include = sf_module_.attr("Include")(target, name, is_macro, is_next);
      bpl::extract<bpl::list>(source_file.attr("includes"))().append(include);
    }
    case CXCursor_MacroDefinition:
    {
      MacroDefinition definition(tu_, c);
      return asg_module_.attr("Macro")(source_file, line,
				       "macro", // type
				       qname(name),
				       definition.parameters(),
				       ""); // body
    }
    case CXCursor_StructDecl:
      return asg_module_.attr("Class")(source_file, line, "struct", qname(name));
    case CXCursor_UnionDecl:
      return asg_module_.attr("Class")(source_file, line, "union", qname(name));
    case CXCursor_ClassDecl:
      return asg_module_.attr("Class")(source_file, line, "class", qname(name));
    case CXCursor_ClassTemplate:
    case CXCursor_ClassTemplatePartialSpecialization:
    {
      // For template specializations we alter the name to include the template signature.
      // Specializations can't be found via symbol lookup, but we do want to be able to refer
      // to them explicitly.
      if (c.kind == CXCursor_ClassTemplatePartialSpecialization)
      {
	CXString sn = clang_getCursorDisplayName(c);
	name = clang_getCString(sn);
	clang_disposeString(sn);
      }
      ParamVisitor param_visitor(symbols_, types_);
      bpl::list params = param_visitor.translate_template_parameters(c);
      CXCursorKind k = clang_getTemplateCursorKind(c);
      char const *kind = "class";
      if (k == CXCursor_StructDecl) kind == "struct";
      else if (k == CXCursor_UnionDecl) kind == "union";
      bpl::object templ = asg_module_.attr("ClassTemplate")(source_file, line, "class", qname(name));
      bpl::object t_id = asg_module_.attr("TemplateId")("C++", qname(name), templ, params);
      templ.attr("template") = t_id;
      return templ;
    }
    case CXCursor_Namespace:
    {
      if (name.empty()) // anonymous
      {
	name = bpl::extract<std::string>(file_.attr("name"));
	std::string::size_type p = name.rfind('/');
	if (p != std::string::npos) name.erase(0, p + 1);
	name = "{" + name + "}";
      }

      // If the namespace already exists, return it.
      bpl::object qname = this->qname(name);
      bpl::object decls = declarations_;
      if (scope_.size()) decls = scope_.top().attr("declarations");
      for (size_t i = 0; i != bpl::len(decls); ++i)
	if (decls[i].attr("name") == qname) return decls[i];
      return asg_module_.attr("Module")(source_file, line, "namespace", qname);
    }
    case CXCursor_FieldDecl:
    {
      bpl::object type = types_.lookup(clang_getCursorType(c));
      return asg_module_.attr("Variable")(source_file, line, "data member", qname(name), type, false);
    }
    case CXCursor_EnumConstantDecl:
    {
      Stringifier stringifier(tu_);
      bpl::object value(stringifier.stringify(c));
      return asg_module_.attr("Enumerator")(source_file, line, qname(name), value);
    }
    case CXCursor_VarDecl:
    {
      CXType t = clang_getCursorType(c);
      bool is_const = clang_isConstQualifiedType(t);
      bool is_volatile = clang_isVolatileQualifiedType(t);
      bpl::object type = types_.lookup(t);
      std::string stype = scope_.size() ?
	std::string(bpl::extract<std::string>(scope_.top().attr("type"))) :
	"global";
      std::string vtype = stype == "function" ? "local " : "";
      vtype += is_const ? "constant" : "variable";
      if (stype == "class" || stype == "struct" || stype == "union") vtype = "data member";
      if (is_const)
      {
	Stringifier stringifier(tu_);
	bpl::object value(stringifier.stringify(c));
	return asg_module_.attr("Const")(source_file, line, vtype, qname(name), type, value);
      }
      else
	return asg_module_.attr("Variable")(source_file, line, vtype, qname(name), type, false);
    }
    case CXCursor_TypedefDecl:
    {
      bpl::object type = types_.lookup(clang_getCursorType(c));
      // HACK: Find out whether the referenced type is an UnknownTypeId.
      //       If it is, assume it was constructed in-place.
      bpl::object name_attr = bpl::getattr(type, "name", bpl::object());
      if (name_attr &&
	  bpl::extract<char const *>(bpl::str(name_attr))[0] == '`')
	return asg_module_.attr("Typedef")(source_file, line, "typedef", qname(name), type, true);
      else
	return asg_module_.attr("Typedef")(source_file, line, "typedef", qname(name), type, false);
    }
    case CXCursor_EnumDecl:
    {
      enumerators_ = bpl::list();
      visit_children(c);
      return asg_module_.attr("Enum")(source_file, line, qname(name), enumerators_);
    }
    case CXCursor_FunctionDecl:
    case CXCursor_FunctionTemplate:
    case CXCursor_Constructor:
    case CXCursor_Destructor:
    case CXCursor_CXXMethod:
    case CXCursor_ConversionFunction:
    {
      CXString dn = clang_getCursorDisplayName(c);
      std::string full_name = clang_getCString(dn);
      clang_disposeString(dn);
      bpl::object return_type = types_.lookup(clang_getCursorResultType(c));
      visit_children(c);
      bpl::object f;
      if (c.kind == CXCursor_FunctionTemplate)
      {
	f = asg_module_.attr("FunctionTemplate")(source_file, line,
						 "function template",
						 bpl::list(), // premod
						 return_type,
						 bpl::list(), // postmod
						 qname(full_name), // fname (mangled)
						 name); // fname
	ParamVisitor param_visitor(symbols_, types_);
	bpl::list params = param_visitor.translate_template_parameters(c);
	bpl::object t_id = asg_module_.attr("TemplateId")("C++", qname(name), f, params);
	f.attr("template") = t_id;
      }
      else if (c.kind == CXCursor_FunctionDecl)
	f = asg_module_.attr("Function")(source_file, line,
					 "function",
					 bpl::list(), // premod
					 return_type,
					 bpl::list(), // postmod
					 qname(full_name), // fname (mangled)
					 name); // fname
      else if (c.kind == CXCursor_Constructor ||
	       c.kind == CXCursor_Destructor ||
	       c.kind == CXCursor_CXXMethod ||
	       c.kind == CXCursor_ConversionFunction)
      {
	char const *type = c.kind == CXCursor_Constructor ? "constructor" :
	  c.kind == CXCursor_Destructor ? "destructor" :
	  "operation";
	bpl::list premod;
	if (clang_CXXMethod_isStatic(c))
	  premod.append("static");
	else if (clang_CXXMethod_isVirtual(c))
	  premod.append("virtual");
	f = asg_module_.attr("Operation")(source_file, line,
					  type,
					  premod,
					  return_type,
					  bpl::list(), // postmod
					  qname(full_name), // fname (mangled)
					  name); // fname
      }
      ParamVisitor param_visitor(symbols_, types_);
      f.attr("parameters") = param_visitor.translate_function_parameters(c);
      return f;
    }
    case CXCursor_UsingDirective:
    {
      UsingDirectiveDereferencer udd;
      CXCursor r = udd.reference(c);
      bpl::object aliased = symbols_.lookup(r);
      return asg_module_.attr("UsingDirective")(source_file, line, "using", bpl::object(aliased.attr("name")));
    }
    case CXCursor_UsingDeclaration:
    {
      bpl::object aliased = symbols_.lookup(clang_getCursorReferenced(c));
      return asg_module_.attr("UsingDeclaration")(source_file, line, "using", qname(name), aliased);
    }
    default:
      throw std::runtime_error("unimplemented: " + cursor_info(c));
  }
}

CXChildVisitResult ASGTranslator::visit_pp_directive(CXCursor c, CXCursor p)
{
  // Skip any builtin declarations
  if (!is_visible(c))
    return CXChildVisit_Continue;

  switch (c.kind)
  {
    case CXCursor_MacroDefinition:
    {
      bpl::list comments = get_comments(c);
      bpl::object d = create(c);
      declare(c, d);
      if (d && comments)
	bpl::extract<bpl::dict>(d.attr("annotations"))()["comments"] = comments;
      types_.declare(clang_getCursorType(c), d, true);
      break;
    }
    case CXCursor_MacroInstantiation:
      break;
    case CXCursor_InclusionDirective:
    {
      bpl::object d = create(c);
      // Nothing to do here. The include directive was already added to the source file
      // inside the create() function.
      break;
    }
  default:
      throw std::runtime_error("unimplemented: " + cursor_info(c));
  }
  comment_horizon_ = clang_getRangeEnd(clang_getCursorExtent(c));
  return CXChildVisit_Continue;
}

CXChildVisitResult ASGTranslator::visit_declaration(CXCursor c, CXCursor p)
{
  // Skip any builtin declarations
  if (!is_visible(c))
    return CXChildVisit_Continue;

  bpl::object declaration;
  bpl::list comments = get_comments(c);
  bool consume_comments = true;
  CXType type = clang_getCursorType(c);
  bpl::list bases;
  switch (c.kind)
  {
    case CXCursor_StructDecl:
    case CXCursor_UnionDecl:
    case CXCursor_ClassDecl:
    case CXCursor_ClassTemplate:
    case CXCursor_ClassTemplatePartialSpecialization:
    case CXCursor_Namespace:
    {
      declaration = create(c);
      // If this is a namespace, only add it the first time
      if (c.kind == CXCursor_Namespace)
      {
	bool reopened = false;
	if (scope_.size())
	{
	  if (bpl::extract<bpl::list>(scope_.top().attr("declarations"))().contains(declaration))
	    reopened = true;
	}
	else
	{
	  if (declarations_.contains(declaration))
	    reopened = true;
	}
	if (!reopened)
	  declare(c, declaration);
      }
      // If this is a class / struct, look for base specifiers
      else
      {
	declare(c, declaration);
	BaseSpecVisitor base_visitor(types_);
	declaration.attr("parents") = base_visitor.find_bases(c);
      }
      if (c.kind == CXCursor_ClassTemplatePartialSpecialization)
      {
	CXCursor p = clang_getSpecializedCursorTemplate(c);
	bpl::object primary = lookup(p);
	bpl::extract<bpl::list>(primary.attr("specializations"))().append(declaration);
	declaration.attr("primary_template") = primary;
      }
      // HACK: If this is an anonymous struct, class, etc., we look back to see
      //       whether this is part of a typedef declaration (with in-place construction)
      //       such as 'typedef struct {...} foo;'
      //       If it is, we don't consume the comments, to allow the typedef to use them,
      //       which is visited after the struct.
      if (bpl::extract<char const *>(bpl::str(declaration.attr("name")))[0] == '`')
	consume_comments = false;
      if (type.kind != CXType_Invalid) // e.g. for namespaces
	types_.declare(type, declaration, true);
      scope_.push(declaration);
      visit_children(c);
      scope_.pop();
      break;
    }
    case CXCursor_EnumConstantDecl:
      declaration = create(c);
      // enumerators aren't declared. We need them in the symbol table anyhow.
      symbols_.declare(c, declaration);
      enumerators_.append(declaration);
      break;
    case CXCursor_FieldDecl:
    case CXCursor_VarDecl:
    case CXCursor_TypedefDecl:
      if (type.kind != CXType_Invalid) // e.g. builtin typendefs
      {
	declaration = create(c);
	declare(c, declaration);
	types_.declare(type, declaration, true);
      }
      break;
    case CXCursor_EnumDecl:
      declaration = create(c);
      declare(c, declaration);
      types_.declare(type, declaration, true);
      break;
    case CXCursor_FunctionDecl:
    case CXCursor_FunctionTemplate:
    case CXCursor_Constructor:
    case CXCursor_Destructor:
    case CXCursor_CXXMethod:
    case CXCursor_ConversionFunction:
    case CXCursor_UsingDeclaration:
      declaration = create(c);
      declare(c, declaration);
      break;
    case CXCursor_UsingDirective:
      break;
    // These are dealt with elsewhere. Ignore them in this context.
    case CXCursor_ParmDecl:
    case CXCursor_TemplateTypeParameter:
    case CXCursor_TemplateTemplateParameter:
    case CXCursor_NonTypeTemplateParameter:
      break;
      // TBD
    case CXCursor_NamespaceAlias:
      break;
    case CXCursor_UnexposedDecl:
      if (debug_)
	std::cout << cursor_info(c) << " in " << cursor_location(c) << std::endl;
      // clang reports 'extern "C" ...' as an unexposed decl, which we definitely
      // need to recurse into.
      visit_children(c);
      break;
    case CXCursor_CXXAccessSpecifier:
      break;
    default:
      throw std::runtime_error("unimplemented: " + cursor_info(c));
  }
  if (declaration && comments)
    bpl::extract<bpl::dict>(declaration.attr("annotations"))()["comments"] = comments;
  if (consume_comments)
    comment_horizon_ = clang_getRangeEnd(clang_getCursorExtent(c));
  return CXChildVisit_Continue;
}

void ASGTranslator::visit_children(CXCursor c)
{
  CXSourceLocation comment_horizon_backup = comment_horizon_;
  clang_visitChildren(c, &ASGTranslator::visit, this);
  comment_horizon_ = comment_horizon_backup;
}

bpl::list ASGTranslator::get_comments(CXCursor c)
{
  // Terminology:
  // A single comment is either a C-style ('/* ... */') comment,
  // or a consecutive set of C++-style comments, i.e. where individual
  // comment lines are separated only by a single newline.
  //
  // In addition, if the given cursor is separated from preceding comments by an
  // empty line, an empty item is pushed into the list, to allow comment-processors
  // to take this into account during filtering.
  bpl::list comments;
  bool next_is_cxx_comment = false;
  unsigned next_token_start_line;
  clang_getSpellingLocation(clang_getRangeStart(clang_getCursorExtent(c)),
			    0, &next_token_start_line, 0, 0);
  // Tokenize the range from the comment horizon to the start
  // of the current cursor.
  CXSourceRange range = clang_getRange(comment_horizon_,
				       clang_getRangeStart(clang_getCursorExtent(c)));
  if (debug_)
    std::cout << "looking for comments in " << range_info(range) << std::endl;
  CXToken *tokens;
  unsigned num_tokens;
  clang_tokenize(tu_, range, &tokens, &num_tokens);
  // FIXME: Due to a bug in clang_tokenize, the last token returned is actually outside
  //        the range
  if (num_tokens) --num_tokens;
  // Walk backwards from the given cursor, stopping
  // at the first non-comment token
  unsigned last = num_tokens;
  // Macro definition cursors start after the 'define', so we need
  // to step back two tokens to be able to see what comes before the pp directive.
  if (c.kind == CXCursor_MacroDefinition && last > 2) last -= 2;
  for (unsigned i = last; i; --i)
  {
    if (debug_)
      std::cout << token_info(tu_, tokens[i - 1]) << std::endl;
    CXTokenKind kind = clang_getTokenKind(tokens[i - 1]);
    // FIXME: Right now the cursor extent of certain types may not go quite far enough.
    //        For example, function declarations may start with a macro which is actually defined
    //        to be empty (and thus can't be seen by the extent-computing machinery.
    //
    //        As a simple heuristic (and until we find a better solution), ignore such tokens.
    if (kind == CXToken_Identifier && bpl::len(comments) == 0)
    {
      // look it up to see whether it is actually part of a macro instantiation (and defines to nothing).
      //...
      continue;
    }
    else if (kind != CXToken_Comment) break;

    CXString s = clang_getTokenSpelling(tu_, tokens[i - 1]);
    char const *text = clang_getCString(s);
    bool is_cxx_comment = text[1] == '/';
    CXSourceRange token_range = clang_getTokenExtent(tu_, tokens[i - 1]);
    unsigned prev_token_end_line;
    clang_getSpellingLocation(clang_getRangeEnd(token_range),
			      0, &prev_token_end_line, 0, 0);
    // If the comment directly preceding the cursor is separated from it by
    // an empty line, insert an empty string into the comments.
    if (bpl::len(comments) == 0 &&
	prev_token_end_line + 1 != next_token_start_line)
      comments.append("");

    // If two consecutive comments are both C++-style and are only separated by
    // a single newline, concatenate them.
    if (prev_token_end_line + 1 == next_token_start_line &&
	is_cxx_comment && next_is_cxx_comment)
    {
      std::string comment = bpl::extract<std::string>(comments[0]);
      comment.insert(0, "\n");
      comment.insert(0, text);
      comments[0] = comment;
    }
    else comments.insert(0, text);

    clang_disposeString(s);

    next_is_cxx_comment = is_cxx_comment;
    clang_getSpellingLocation(clang_getRangeStart(token_range),
			      0, &next_token_start_line, 0, 0);
  }
  clang_disposeTokens(tu_, tokens, num_tokens);
  return comments;
}

CXChildVisitResult ASGTranslator::visit(CXCursor c, CXCursor p, CXClientData d)
{
  ASGTranslator *translator = static_cast<ASGTranslator*>(d);
  if (translator->verbose_)
    std::cout << "visit " << cursor_info(c) << std::endl;

  try
  {
    if (clang_isPreprocessing(c.kind)) return translator->visit_pp_directive(c, p);
    else if (clang_isDeclaration(c.kind)) return translator->visit_declaration(c, p);
    translator->comment_horizon_ = clang_getRangeEnd(clang_getCursorExtent(c));
    return CXChildVisit_Continue;
  }
  catch (...)
  {
    if (translator->debug_)
      std::cerr << "Error at " << cursor_info(c) << " in " << cursor_location(c, true) << std::endl;
    throw;
  }
}
