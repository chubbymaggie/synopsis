/*$Id: GapBuffer.hh,v 1.2 2001/06/05 05:28:34 chalky Exp $
 *
 * This source file is a part of the Berlin Project.
 * Copyright (C) 1999 Stefan Seefeld <stefan@berlin-consortium.org> 
 * http://www.berlin-consortium.org
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Library General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Library General Public
 * License along with this library; if not, write to the
 * Free Software Foundation, Inc., 675 Mass Ave, Cambridge,
 * MA 02139, USA.
 */
#ifndef _GapBuffer_hh
#define _GapBuffer_hh

#include <vector>

//.
//. the design of a gap buffer should follow the typical behavior
//. when editing text. Editing text has two parts: modifying it
//. and simply browsing it. The text contains a 'cursor', which indicates
//. the actual position. When in editing mode, we have to take care to
//. use smart memory management. For this purpose we introduce a little
//. memory gap into the string where new characters can be inserted,
//. so not on every insert() all the following characters have to be moved
//.
//. a gap buffer is layed out like this:
//.   
//.   |***********************..........**********|
//.   ^                      ^         ^          ^
//.  begin()                gbegin()  gend()     end()
//.
//. the following (in)equalities should always hold:
//. 
//. gend() > gbegin()
//. gend() - gbegin() <= gmaxsize()
//. end() >= gend()
//. 
//.
template <class T, short gapsize>
class GapBuffer : private std::vector<T>
{
  typedef std::vector<T> rep_type;
  typedef typename std::vector<T>::value_type value_type;
  iterator gbegin() { return begin() + gapbegin;}
  iterator gend() { return begin() + gapend;}
  iterator cursor() { return begin() + curs;}
  void newgap()
    {
      rep_type::insert(gbegin(), gapsize, value_type(0));
      gapend += gapsize;
    }
  void movegap(int d)
    {
      if (d > 0)
	{
	  if (gend() + d > end()) rep_type::insert(end(), size_type(gend() + d - end()), value_type(0));
	  copy(gend(), gend() + d, gbegin());
	}
      else
	copy(rep_type::reverse_iterator(gbegin()), rep_type::reverse_iterator(gbegin() + d), rep_type::reverse_iterator(gend()));
      gapbegin += d, gapend += d;
    }
  size_type gap() { return gapend - gapbegin;}
  void editing() { size_type d = curs - gapbegin; if (d != 0) movegap(d);}
  void compact() { size_type d = end() - gend(); if (d > 0) movegap(d);}
public:
  GapBuffer() : curs(0), gapbegin(0), gapend(0) {}
  size_type size() { compact(); return gbegin() - begin();}
  void forward()
    {
      if (curs == gapbegin && gend() != end()) curs += gap();
      else if (cursor() < end()) curs++;
    }
  void backward()
    {
      if (curs == gapend) curs -= gap();
      else if (cursor() > begin()) curs--;
    }
  void shift(size_type d)
    {
      size_type tmp = curs + d;
      if ((curs > gapend && tmp > gapend) || (curs <= gapbegin && tmp <= gapbegin)) curs = tmp;
      else if (d < 0) curs += d - gap();
      else curs += d + gap();
    }
  size_type position() { return curs > gapend ? curs - gap() : curs;}
  void position(size_type p) { shift(p - curs);}
  void insert(value_type u)
    {
      editing();
      if (!gap()) newgap();
      *cursor() = u;
      curs++, gapbegin++;
    }
  void insert(value_type *u, size_type n)
    {
      editing();
      rep_type::insert(cursor(), u, u + n);
      curs += n, gapbegin += n, gapend += n;
    }
  void remove_backward(size_type n)
    {
      if (curs <= gapbegin)
	{
	  if (curs < n) n = curs;
	  erase(cursor() - n, cursor());
	  curs -= n, gapbegin -= n, gapend -= n;
	}
      else if (curs - gapend > n)
	{
	  erase(cursor() - n, cursor());
	  curs -= n;
	}
      else
	{
	  size_type d = curs - gapend;
	  erase(gbegin() - (n - d), gbegin());
	  erase(cursor() - d, cursor());
	  gapbegin -= n - d, gapend -= n - d;
	  curs -= n;
	}
    }
  void remove_forward(size_type n)
    {
      if (curs >= gapend)
	{
	  if (size_type(end() - cursor()) < n) n = end() - cursor();
	  erase(cursor(), cursor() + n);
	}
      else if (gapbegin - curs > n)
	{
	  erase(cursor(), cursor() + n);
	  gapbegin -= n, gapend -= n;
	}
      else
	{
	  size_type d = gapbegin - curs;
	  erase(gend(), gend() + (n - d));
	  erase(cursor(), cursor() + d);
	  gapbegin -= d, gapend -= d;
	}
    }
  const value_type *get() { compact(); return begin();}
private:
  size_type curs, gapbegin, gapend;
};

#endif
