//
// Copyright (C) 2004 Stefan Seefeld
// All rights reserved.
// Licensed to the public under the terms of the GNU LGPL (>= 2),
// see the file COPYING for details.
//

#ifndef _Synopsis_ASG_SourceFile_hh
#define _Synopsis_ASG_SourceFile_hh

#include <Synopsis/Python/Object.hh>
#include <Synopsis/ASG/Declaration.hh>

namespace Synopsis
{

class Include : public Python::Object
{
public:
  Include(const Python::Object &o) throw(TypeError) : Python::Object(o) { assert_type();}
  SourceFile target() const { return narrow<SourceFile>(attr("target")());}
  std::string name() const { return narrow<std::string>(attr("name")());}
  bool is_macro() const { return narrow<bool>(attr("is_macro")());}
  bool is_next() const { return narrow<bool>(attr("is_next")());}
  void assert_type() throw(TypeError) { Python::Object::assert_type("Synopsis.SourceFile", "Include");}
};

class MacroCall : public Python::Object
{
public:
  MacroCall(const Python::Object &o) throw(TypeError) : Python::Object(o) { assert_type();}
  void assert_type() throw(TypeError) { Python::Object::assert_type("Synopsis.SourceFile", "MacroCall");}
  std::string name() { return narrow<std::string>(attr("name"));}
  long start_line() { return narrow<long>(attr("start").get(0));}
  long start_col() { return narrow<long>(attr("start").get(1));}
  long end_line() { return narrow<long>(attr("end").get(0));}
  long end_col() { return narrow<long>(attr("end").get(1));}
  long e_start_line() { return narrow<long>(attr("expanded_start").get(0));}
  long e_start_col() { return narrow<long>(attr("expanded_start").get(1));}
  long e_end_line() { return narrow<long>(attr("expanded_end").get(0));}
  long e_end_col() { return narrow<long>(attr("expanded_end").get(1));}
};

}

#endif
