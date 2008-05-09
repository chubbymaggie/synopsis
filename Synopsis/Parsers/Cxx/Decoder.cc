//
// Copyright (C) 2002 Stephen Davies
// Copyright (C) 2002 Stefan Seefeld
// All rights reserved.
// Licensed to the public under the terms of the GNU LGPL (>= 2),
// see the file COPYING for details.
//

#include "Decoder.hh"
#include "Types.hh"
#include "Builder.hh"
#include "STrace.hh"
#include "TypeIdFormatter.hh"
#include "Lookup.hh"
#include <iostream>
#include <sstream>

using namespace Synopsis;

Decoder::Decoder(Builder* builder)
        : m_builder(builder)
{
    m_lookup = m_builder->lookup();
}

std::string Decoder::decodeName()
{
    size_t length = *m_iter++ - 0x80;
    std::string name(length, '\0');
    std::copy(m_iter, m_iter + length, name.begin());
    m_iter += length;
    return name;
}

std::string Decoder::decodeName(code_iter iter)
{
    size_t length = *iter++ - 0x80;
    std::string name(length, '\0');
    std::copy(iter, iter + length, name.begin());
    iter += length;
    return name;
}

std::string Decoder::decodeName(const PTree::Encoding &e)
{
    PTree::Encoding::iterator i = e.begin();
    size_t length = (const unsigned char)(*i++) - 0x80;
    std::string name(reinterpret_cast<const char *>(&*i), length);
    return name;
}

void Decoder::decodeQualName(std::vector<std::string>& names)
{
    STrace trace("Decoder::decodeQualName");
    if (*m_iter++ != 'Q')
        return;
    int scopes = *m_iter++ - 0x80;
    while (scopes--)
    {
        // Only handle names here
        if (*m_iter >= 0x80)
        { // Name
            names.push_back(decodeName());
        }
        else if (*m_iter == 'T')
        {
            // Template :(
            ++m_iter;
            TypeIdFormatter f;
            std::ostringstream name;
            name << decodeName();
            char sep = '<';
            code_iter tend = m_iter;
            tend += *m_iter++ - 0x80;
            while (m_iter <= tend)
                name << sep << f.format(decodeType());
            name << '>';
            names.push_back(name.str());
        }
        else
        {
            LOG("Warning: Unknown type inside Q name: " << *m_iter);
            LOG("         String was: " << m_string);
            // FIXME: provide << operator for m_string !
            // 	    std::cerr << "         Decoding " << m_string << std::endl;
            throw ERROR("Unknown type inside Q name");
        }
    }
}

void Decoder::init(const PTree::Encoding &e)
{
  m_string = code(e.begin(), e.end());
  m_iter = m_string.begin();
}

Types::Type* Decoder::decodeType()
{
    STrace trace("Decoder::decodeType()");
    code_iter end = m_string.end();
    std::vector<std::string> premod, postmod;
    std::string name;
    Types::Type *baseType = 0;

    // Loop forever until broken
    while (m_iter != end && !name.length() && !baseType)
    {
        int c = *m_iter++;
        switch (c)
        {
        case 'P':
            postmod.insert(postmod.begin(), "*");
            break;
        case 'R':
            postmod.insert(postmod.begin(), "&");
            break;
        case 'S':
            premod.push_back("signed");
            break;
        case 'U':
            premod.push_back("unsigned");
            break;
        case 'C':
            premod.push_back("const");
            break;
        case 'V':
            premod.push_back("volatile");
            break;
        case 'A':
	{
	  std::string array("[");
	  while (*m_iter != '_') array.push_back(*m_iter++);
	  array.push_back(']');
	  ++m_iter;
	  premod.push_back(array);
	  break;
	}
        case '*':
            {
                ScopedName n;
                n.push_back("*");
                baseType = new Types::Dependent(n);
                break;
            }
        case 'i':
            name = "int";
            break;
        case 'v':
            name = "void";
            break;
        case 'b':
            name = "bool";
            break;
        case 's':
            name = "short";
            break;
        case 'c':
            name = "char";
            break;
        case 'w':
            name = "wchar_t";
            break;
        case 'l':
            name = "long";
            break;
        case 'j':
            name = "long long";
            break;
        case 'f':
            name = "float";
            break;
        case 'd':
            name = "double";
            break;
        case 'r':
            name = "long double";
            break;
        case 'e':
            name = "...";
            break;
        case '?':
            return 0;
        case 'Q':
            baseType = decodeQualType();
            break;
        case '_':
            --m_iter;
            return 0; // end of func params
        case 'F':
            baseType = decodeFuncPtr(postmod);
            break;
        case 'T':
            baseType = decodeTemplate();
            break;
        case 'M':
            // Pointer to member. Format is same as for named types
            name = decodeName() + "::*";
            break;
        default:
            if (c > 0x80)
            {
                --m_iter;
                name = decodeName();
                break;
            }
            // FIXME
            // 	    std::cerr << "\nUnknown char decoding '"<<m_string<<"': "
            // 		 << char(c) << " " << c << " at "
            // 		 << (m_iter - m_string.begin()) << std::endl;
        } // switch
    } // while
    if (!baseType && !name.length())
    {
        // FIXME
        // 	std::cerr << "no type or name found decoding " << m_string << std::endl;
        return 0;
    }
    if (!baseType)
        baseType = m_lookup->lookupType(name);
    if (premod.empty() && postmod.empty())
        return baseType;
    Types::Type* ret = new Types::Modifier(baseType, premod, postmod);
    return ret;
}

Types::Type* Decoder::decodeQualType()
{
    STrace trace("Decoder::decodeQualType()");
    // Qualified type: first is num of scopes, each a name.
    int scopes = *m_iter++ - 0x80;
    std::vector<std::string> names;
    std::vector<Types::Type*> types; // if parameterized
    while (scopes--)
    {
        // Only handle two things here: names and templates
        if (*m_iter >= 0x80)
        { // Name
            names.push_back(decodeName());
        }
        else if (*m_iter == 'T')
        {
            // Template :(
            ++m_iter;
            std::string tname = decodeName();
            code_iter tend = m_iter;
            tend += *m_iter++ - 0x80;
            while (m_iter <= tend)
                types.push_back(decodeType());
            names.push_back(tname);
        }
        else
        {
            //std::cerr << "Warning: Unknown type inside Q: " << *m_iter << std::endl;
            // FIXME
            //std::cerr << "         Decoding " << m_string << std::endl;
        }
    }
    // Ask for qualified lookup
    Types::Type* baseType;
    try
    {
        baseType = m_lookup->lookupType(names);
    }
    catch (...)
    {
        // Ignore error, and return an Unknown instead
        return new Types::Unknown(names);
    }
    // If the type is a template, then parameterize it with the params found
    // in the T decoding
    if (types.size())
    {
        Types::Declared* declared = dynamic_cast<Types::Declared*>(baseType);
        ASG::ClassTemplate* tempclas = declared ? dynamic_cast<ASG::ClassTemplate*>(declared->declaration()) : 0;
        Types::Template* templType = tempclas ? tempclas->template_id() : 0;
        if (templType && types.size())
        {
            return new Types::Parameterized(templType, types);
        }
    }
    return baseType;
}

Types::Type* Decoder::decodeFuncPtr(std::vector<std::string>& postmod)
{
    // Function ptr. Encoded same as function
    Types::Type::Mods premod;
    // Move * from postmod to funcptr's premod. This makes the output be
    // "void (*convert)()" instead of "void (convert)()*"
    if (postmod.size() > 0 && postmod[0] == "*")
    {
        premod.push_back(postmod.front());
        postmod.erase(postmod.begin());
    }
    Types::Type::vector params;
    while (1)
    {
        Types::Type* type = decodeType();
        if (type)
            params.push_back(type);
        else
            break;
    }
    ++m_iter; // skip over '_'
    Types::Type* returnType = decodeType();
    Types::Type* ret = new Types::FuncPtr(returnType, premod, params);
    return ret;
}

Types::Parameterized* Decoder::decodeTemplate()
{
    STrace trace("Decoder::decodeTemplate()");

    // Template type: Name first, then size of arg field, then arg
    // types eg: T6vector54cell <-- 5 is len of 4cell
    if (*m_iter == 'T')
        ++m_iter;
    std::string name = decodeName();
    code_iter tend = m_iter;
    tend += *m_iter++ - 0x80;
    std::vector<Types::Type*> types;
    while (m_iter <= tend)
        types.push_back(decodeType());
    Types::Type* type = m_lookup->lookupType(name);
    // if type is declared and declaration is class and class is template..
    Types::Declared* declared = dynamic_cast<Types::Declared*>(type);
    Types::Named* templ = 0;
    if (declared)
    {
      if (ASG::ClassTemplate* t_class = dynamic_cast<ASG::ClassTemplate*>(declared->declaration()))
        templ = t_class->template_id();
      else if (ASG::Forward* t_forward = dynamic_cast<ASG::Forward*>
               (declared->declaration()))
        templ = t_forward->template_id();
    }
    else if (Types::Dependent* d = dynamic_cast<Types::Dependent*>(type))
      templ = d;
//     if (templ)
//       std::cout << "creating Parameterized for " << name << ' ' << templ->name() << std::endl;
//     else
//       std::cout << "no template found for " << name << ' ' << typeid(type).name() << std::endl;
    return new Types::Parameterized(templ, types);
}

// vim: set ts=8 sts=4 sw=4 et: