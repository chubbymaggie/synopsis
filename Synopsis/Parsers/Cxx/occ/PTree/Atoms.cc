//
// Copyright (C) 1997-2000 Shigeru Chiba
// Copyright (C) 2004 Stefan Seefeld
// All rights reserved.
// Licensed to the public under the terms of the GNU LGPL (>= 2),
// see the file COPYING for details.
//
#include "PTree/Atoms.hh"
#include "Walker.hh"

namespace
{
// little helper for initialization
char *dup_alloc(const char *str1, size_t len1,
		const char *str2, size_t len2)
{
  char *buffer = new (GC) char[len1 + len2];
  memmove(buffer, str1, len1);
  memmove(buffer + len1, str2, len2);
  return buffer;
}

}

using namespace PTree;

DupAtom::DupAtom(const char *str, size_t len)
  : CommentedAtom(static_cast<char *>(memmove(new (GC) char[len], str, len)), len)
{
}

DupAtom::DupAtom(const char *str1, size_t len1,
		 const char *str2, size_t len2)
  : CommentedAtom(dup_alloc(str1, len1, str2, len2), len1 + len2)
{
}

Node *Identifier::Translate(Walker* w)
{
  return w->TranslateVariable(this);
}

void Identifier::Typeof(Walker* w, TypeInfo& t)
{
  w->TypeofVariable(this, t);
}

Node *This::Translate(Walker* w)
{
  return w->TranslateThis(this);
}

void This::Typeof(Walker* w, TypeInfo& t)
{
  w->TypeofThis(this, t);
}