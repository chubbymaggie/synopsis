/*
  Copyright (C) 1997-2000 Shigeru Chiba, University of Tsukuba.

  Permission to use, copy, distribute and modify this software and   
  its documentation for any purpose is hereby granted without fee,        
  provided that the above copyright notice appear in all copies and that 
  both that copyright notice and this permission notice appear in 
  supporting documentation.

  Shigeru Chiba makes no representations about the suitability of this 
  software for any purpose.  It is provided "as is" without express or
  implied warranty.
*/
/*
  Copyright (c) 1995, 1996 Xerox Corporation.
  All Rights Reserved.

  Use and copying of this software and preparation of derivative works
  based upon this software are permitted. Any copy of this software or
  of any derivative work must include the above copyright notice of
  Xerox Corporation, this paragraph and the one after it.  Any
  distribution of this software or derivative works must comply with all
  applicable United States export control laws.

  This software is made available AS IS, and XEROX CORPORATION DISCLAIMS
  ALL WARRANTIES, EXPRESS OR IMPLIED, INCLUDING WITHOUT LIMITATION THE
  IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
  PURPOSE, AND NOTWITHSTANDING ANY OTHER PROVISION CONTAINED HEREIN, ANY
  LIABILITY FOR DAMAGES RESULTING FROM THE SOFTWARE OR ITS USE IS
  EXPRESSLY DISCLAIMED, WHETHER ARISING IN CONTRACT, TORT (INCLUDING
  NEGLIGENCE) OR STRICT LIABILITY, EVEN IF XEROX CORPORATION IS ADVISED
  OF THE POSSIBILITY OF SUCH DAMAGES.
*/

#include <cstdio>
#include <cstring>
#include <cstdarg>
#include <stdexcept>
#if !defined(_MSC_VER)
#include <sys/time.h>
#endif
#include "PTree.hh"
#include "Lexer.hh"
#include "Class.hh"

#if (defined(sun) && defined(SUNOS4)) || defined(SUNOS5)
extern "C" {
    int gettimeofday(struct timeval*, void*);
};
#endif

const int MAX = 32;

static PTree::Node **resultsArgs[MAX];
static int resultsIndex;

static int CountArgs(char* pat);
static char* SkipSpaces(char* pat);

bool PTree::Node::Match(PTree::Node *list, char* pattern, ...)
{
    va_list args;
    int n = CountArgs(pattern);
    if(n >= MAX)
	MopErrorMessage("PTree::Node::Match()", "bomb! too many arguments");

    va_start(args, pattern);
    for(int i = 0; i < n; ++i)
      resultsArgs[i] = va_arg(args, PTree::Node **);

    va_end(args);

    char* pat = pattern;
    resultsIndex = 0;
    pat = SkipSpaces(pat);
    pat = MatchPat(list, pat);
    if(pat == 0)
	return false;
    else{
	pat = SkipSpaces(pat);
	if(*pat == '\0')
	    return true;
	else{
	    MopWarningMessage("PTree::Node::Match()", "[ ] are forgot?");
	    MopMoreWarningMessage(pattern);
	    return false;
	}
    }
}

static int CountArgs(char* pat)
{
    int n = 0;

    for(char c = *pat; c != '\0'; c = *++pat)
	if(c == '%'){
	    c = *++pat;
	    if(c == '?' || c == 'r')
		++n;
	}

    return n;
}

char* PTree::Node::MatchPat(PTree::Node *list, char* pat)
{
    switch(*pat){
    case '[' :		/* [] means 0 */
	if(list != 0 && list->IsLeaf())
	    return 0;
	else
	    return MatchList(list, pat + 1);
    case '%' :
	switch(pat[1]){
	case '?' :
	    *resultsArgs[resultsIndex++] = list;
	    return(pat + 2);
	case '*' :
	    return(pat + 2);
	case '_' :
	case 'r' :	/* %_ and %r must be appear in a list */
	    return 0;
	default :
	    break;
	}
    }

    if(list != 0 && list->IsLeaf())
	return MatchWord(list, pat);
    else
	return 0;
}

char* PTree::Node::MatchList(PTree::Node *list, char* pat)
{
    char c, d;
    pat = SkipSpaces(pat);
    while((c = *pat) != '\0'){
	if(c == ']')
	    if(list == 0)
		return(pat + 1);
	    else
		return 0;
	else if(c == '%' && (d = pat[1], (d == 'r' || d == '_'))){
	    /* %r or %_ */
	    if(d == 'r') 
		*resultsArgs[resultsIndex++] = list;

	    list = 0;
	    pat = pat + 2;
	}
	else if(list == 0)
	    return 0;
	else{
	    pat = MatchPat(list->Car(), pat);
	    if(pat == 0)
		return 0;

	    list = list->Cdr();
	}

	pat = SkipSpaces(pat);
    }

    MopErrorMessage("PTree::Node::Match()", "unmatched bracket");
    return 0;
}

char* PTree::Node::MatchWord(PTree::Node *list, char* pat)
{
    char* str = list->GetPosition();
    int str_len = list->GetLength();

    for(int j = 0; ; ++pat){
	char c = *pat;
	switch(c){
	case '\0' :
	case ' ' :
	case '\t' :
	case '[' :
	case ']' :
	    if(j == str_len)
		return pat;
	    else
		return 0;
	case '%' :
	    c = *++pat;
	    switch(c){
	    case '[' :
	    case ']' :
	    case '%' :
		if(j >= str_len || c != str[j++])
		    return 0;

		break;
	    default :
		if(j == str_len)
		    return pat;
		else
		    return 0;
	    }
	    break;
	default :
	    if(j >= str_len || c != str[j++])
		return 0;
	}
    }
}

static char* SkipSpaces(char* pat)
{
    while(*pat == ' ' || *pat == '\t')
	++pat;

    return pat;
}

PTree::Node *PTree::Node::GenSym()
{
    static char head[] = "_sym";
    static int seed = 1;
    int len1, len2;

    IntegerToString(seed, len1);

#if !defined(_MSC_VER) && !defined(__WIN32__)
    struct timeval time;
    gettimeofday(&time, 0);
    uint rnum = (time.tv_sec * 10 + time.tv_usec / 100) & 0xffff;
#else
    static uint time = 0;
    time++;
    uint rnum = time & 0xffff;
#endif
    char* num = IntegerToString(rnum, len2);

    int size = len1 + len2 + sizeof(head) - 1 + 1;
    char* name = new (GC) char[size];
    memmove(name, head, sizeof(head) - 1);
    memmove(&name[sizeof(head) - 1], num, len2);
    name[sizeof(head) - 1 + len2] = '_';
    num = IntegerToString(seed++, len1);
    memmove(&name[sizeof(head) - 1 + len2 + 1], num, len1);
    return new PTree::Atom(name, size);
}

// If you edit Make(), you should also edit MakeStatement().

PTree::Node *PTree::Node::Make(const char* pat, ...)
{
    va_list args;
    const int N = 4096;
    static char buf[N];
    char c;
    int len;
    char* ptr;
    PTree::Node *p;
    PTree::Node *q;
    int i = 0, j = 0;
    PTree::Node *result = 0;

    va_start(args, pat);
    while((c = pat[i++]) != '\0')
	if(c == '%'){
	    c = pat[i++];
	    if(c == '%')
		buf[j++] = c;
	    else if(c == 'd'){
		ptr = IntegerToString(va_arg(args, int), len);
		memmove(&buf[j], ptr, len);
		j += len;
	    }
	    else if(c == 's'){
		ptr = va_arg(args, char*);
		len = strlen(ptr);
		memmove(&buf[j], ptr, len);
		j += len;
	    }
	    else if(c == 'c')
		buf[j++] = va_arg(args, int);
	    else if(c == 'p'){
	      p = va_arg(args, PTree::Node *);
		if(p == 0)
		    /* ignore */;
		else if(p->IsLeaf()){
		    memmove(&buf[j], p->GetPosition(), p->GetLength());
		    j += p->GetLength();
		}
		else{   
		    if(j > 0)
			q = List(new PTree::DupAtom(buf, j), p);
		    else
			q = List(p);

		    j = 0;
		    result = Nconc(result, q);
		}
	    }
	    else
		MopErrorMessage("PTree::Node::Make()", "invalid format");
	}
	else
	    buf[j++] = c;

    va_end(args);

    if(j > 0)
	if(result == 0)
	    result = new PTree::DupAtom(buf, j);
	else
	    result = Snoc(result, new PTree::DupAtom(buf, j));

    return result;
}

/*
  MakeStatement() is identical to Make() except that the generated
  code is wrapped by a PtreeNonExpr object.
  This helps code-traverse functions such as WalkExpr() distinguish
  statements from expressions.

  Note: this version is perfectly identical to Make(). 97/3/26
*/
PTree::Node *PTree::Node::MakeStatement(const char* pat, ...)
{
    va_list args;
    const int N = 4096;
    static char buf[N];
    char c;
    int len;
    char* ptr;
    PTree::Node *p;
    PTree::Node *q;
    int i = 0, j = 0;
    PTree::Node *result = 0;

    va_start(args, pat);

    Class::WarnObsoleteness("PTree::Node::MakeStatement()", "PTree::Node::Make()");

    while((c = pat[i++]) != '\0')
	if(c == '%'){
	    c = pat[i++];
	    if(c == '%')
		buf[j++] = c;
	    else if(c == 'd'){
		ptr = IntegerToString(va_arg(args, int), len);
		memmove(&buf[j], ptr, len);
		j += len;
	    }
	    else if(c == 's'){
		ptr = va_arg(args, char*);
		len = strlen(ptr);
		memmove(&buf[j], ptr, len);
		j += len;
	    }
	    else if(c == 'c')
		buf[j++] = va_arg(args, int);
	    else if(c == 'p'){
	      p = va_arg(args, PTree::Node *);
		if(p == 0)
		    /* ignore */;
		else if(p->IsLeaf()){
		    memmove(&buf[j], p->GetPosition(), p->GetLength());
		    j += p->GetLength();
		}
		else{   
		    if(j > 0)
			q = new PTree::DupAtom(buf, j);
		    else
			q = 0;

		    j = 0;
		    result = Nconc(result, List(q, p));
		}
	    }
	    else
		MopErrorMessage("PTree::Node::MakeStatement()", "invalid format");
	}
	else
	    buf[j++] = c;

    va_end(args);

    if(j > 0)
	if(result == 0)
	    result = new PTree::DupAtom(buf, j);
	else
	    result = Snoc(result, new PTree::DupAtom(buf, j));

    return result;
}

bool PTree::Node::Reify(unsigned int& value)
{
  if(!IsLeaf()) return false;

  const char* p = GetPosition();
  int len = GetLength();
  value = 0;
  if(len > 2 && *p == '0' && is_xletter(p[1]))
  {
    for(int i = 2; i < len; ++i)
    {
      char c = p[i];
      if(is_digit(c)) value = value * 0x10 + (c - '0');
      else if('A' <= c && c <= 'F') value = value * 0x10 + (c - 'A' + 10);
      else if('a' <= c && c <= 'f') value = value * 0x10 + (c - 'a' + 10);
      else if(is_int_suffix(c)) break;
      else return false;
    }
    return true;
  }
  else if(len > 0 && is_digit(*p))
  {
    for(int i = 0; i < len; ++i)
    {
      char c = p[i];
      if(is_digit(c)) value = value * 10 + c - '0';
      else if(is_int_suffix(c)) break;
      else return false;
    }
    return true;
  }
  else return false;
}

bool PTree::Node::Reify(char*& str)
{
  if(!IsLeaf()) return false;
  char* p = GetPosition();
  int length = GetLength();
  if(*p != '"') return false;
  else
  {
    str = new(GC) char[length];
    char* sp = str;
    for(int i = 1; i < length; ++i)
      if(p[i] != '"')
      {
	*sp++ = p[i];
	if(p[i] == '\\' && i + 1 < length) *sp++ = p[++i];
      }
      else while(++i < length && p[i] != '"');
    *sp = '\0';
    return true;
  }
}

char* PTree::Node::IntegerToString(sint num, int& length)
{
    const int N = 16;
    static char buf[N];
    bool minus;

    int i = N - 1;
    if(num >= 0)
	minus = false;
    else{
	minus = true;
	num = -num;
    }

    buf[i--] = '\0';
    if(num == 0){
	buf[i] = '0';
	length = 1;
	return &buf[i];
    }
    else{
	while(num > 0){
	    buf[i--] = '0' + char(num % 10);
	    num /= 10;
	}

	if(minus)
	    buf[i--] = '-';

	length = N - 2 - i;
	return &buf[i + 1];
    }
}

PTree::Node *PTree::Node::qMake(char*)
{
    MopErrorMessage("PTree::Node::qMake()",
		    "the metaclass must be compiled by OpenC++.");
    return 0;
}

PTree::Node *PTree::Node::qMakeStatement(char*)
{
    MopErrorMessage("PTree::Node::qMakeStatement()",
		    "the metaclass must be compiled by OpenC++.");
    return 0;
}

// class PtreeHead	--- this is used to implement PTree::Node::qMake().

PTree::Head &PTree::Head::operator + (PTree::Node *p)
{
    ptree = Append(ptree, p);
    return *this;
}

PTree::Head &PTree::Head::operator + (const char* str)
{
    if(*str != '\0')
	ptree =  Append(ptree, (char*)str, strlen(str));

    return *this;
}

PTree::Head &PTree::Head::operator + (char* str)
{
    if(*str != '\0')
	ptree =  Append(ptree, str, strlen(str));

    return *this;
}

PTree::Head &PTree::Head::operator + (char c)
{
    ptree =  Append(ptree, &c, 1);
    return *this;
}

PTree::Head &PTree::Head::operator + (int n)
{
    int len;
    char* str = PTree::Node::IntegerToString(n, len);
    ptree =  Append(ptree, str, len);
    return *this;
}

PTree::Node *PTree::Head::Append(PTree::Node *lst, PTree::Node *tail)
{
    PTree::Node *last;
    PTree::Node *p;
    PTree::Node *q;

    if(tail == 0)
	return lst;

    if(!tail->IsLeaf() && tail->Length() == 1){
	tail = tail->Car();
	if(tail == 0)
	    return lst;
    }

    if(tail->IsLeaf() && lst != 0){
	last = PTree::Node::Last(lst);
	if(last != 0){
	    p = last->Car();
	    if(p != 0 && p->IsLeaf()){
		q = new PTree::DupAtom(p->GetPosition(), p->GetLength(),
				 tail->GetPosition(), tail->GetLength());
		last->SetCar(q);
		return lst;
	    }
	}
    }

    return PTree::Node::Snoc(lst, tail);
}

PTree::Node *PTree::Head::Append(PTree::Node *lst, char* str, int len)
{
    PTree::Node *last;
    PTree::Node *p;
    PTree::Node *q;

    if(lst != 0){
	last = PTree::Node::Last(lst);
	if(last != 0){
	    p = last->Car();
	    if(p != 0 && p->IsLeaf()){
		q = new PTree::DupAtom(p->GetPosition(), p->GetLength(),
				 str, len);
		last->SetCar(q);
		return lst;
	    }
	}
    }

    return PTree::Node::Snoc(lst, new DupAtom(str, len));
}
