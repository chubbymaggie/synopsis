# $Id: Formatter.py,v 1.5 2001/02/07 16:14:40 chalky Exp $
#
# This file is a part of Synopsis.
# Copyright (C) 2000, 2001 Stephen Davies
# Copyright (C) 2000, 2001 Stefan Seefeld
#
# Synopsis is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
# $Log: Formatter.py,v $
# Revision 1.5  2001/02/07 16:14:40  chalky
# Fixed @see linking to be more stubborn (still room for improv. tho)
#
# Revision 1.4  2001/02/07 15:31:06  chalky
# Rewrite javadoc formatter. Now all tags must be at the end of the comment,
# except for inline tags
#
# Revision 1.3  2001/02/01 16:47:48  chalky
# Added CommentFormatter as base of the Comment Formatters ...
#
# Revision 1.2  2001/02/01 15:23:24  chalky
# Copywritten brown paper bag edition.
#
#

"""CommentParser, CommentFormatter and derivatives."""

# System modules
import re, string

# Synopsis modules
from Synopsis.Core import AST, Type, Util

# HTML modules
import core
from core import config
from Tags import *

class CommentParser:
    """A class that takes a Declaration and sorts its comments out."""
    def __init__(self):
	self._formatters = core.config.commentFormatterList
    def parse(self, decl):
	"""Parses the comments of the given AST.Declaration.
	Returns a struct with vars:
	 summary - one-line summary, detail - detailed info,
	 has_detail - true if should show detail,
	 decl - the declaration for this comment
	"""
	strlist = map(lambda x:str(x), decl.comments())
	comm = core.Struct(
	    detail=string.join(strlist), summary='', 
	    has_detail=0, decl=decl)
	map(lambda f,c=comm: f.parse(c), self._formatters)
	return comm

class CommentFormatter:
    """A class that takes a comment Struct and formats its contents."""

    def parse(self, comm):
	"""Parse the comment struct"""
	pass

class SSDFormatter (CommentFormatter):
    """A class that strips //.'s from the start of lines in detail"""
    __re_star = r'/\*(.*?)\*/'
    __re_ssd = r'^[ \t]*//\. ?(.*)$'
    def __init__(self):
	self.re_star = re.compile(SSDFormatter.__re_star, re.S)
	self.re_ssd = re.compile(SSDFormatter.__re_ssd, re.M)
    def parse(self, comm):
	comm.detail = self.parse_ssd(self.strip_star(comm.detail))
    def strip_star(self, str):
	"""Strips all star-format comments from the docstring"""
	mo = self.re_star.search(str)
	while mo:
	    str = str[:mo.start()] + str[mo.end():]
	    mo = self.re_star.search(str)
	return str
    def parse_ssd(self, str):
	return string.join(self.re_ssd.findall(str),'\n')

class JavaFormatter (CommentFormatter):
    """A class that formats java /** style comments"""
    __re_java = r"/\*\*[ \t]*(?P<text>.*)(?P<lines>\n[ \t]*\*.*)*?(\n[ \t]*)?\*/"
    __re_line = r"\n[ \t]*\*[ \t]*(?P<text>.*)"
    def __init__(self):
	self.re_java = re.compile(JavaFormatter.__re_java)
	self.re_line = re.compile(JavaFormatter.__re_line)
    def parse(self, comm):
	if comm.detail is None: return
	text_list = []
	mo = self.re_java.search(comm.detail)
	while mo:
	    text_list.append(mo.group('text'))
	    lines = mo.group('lines')
	    if lines:
		mol = self.re_line.search(lines)
		while mol:
		    text_list.append(mol.group('text'))
		    mol = self.re_line.search(lines, mol.end())
	    mo = self.re_java.search(comm.detail, mo.end())
	comm.detail = string.join(text_list,'\n')

class SummarySplitter (CommentFormatter):
    """A formatter that splits comments into summary and detail"""
    __re_summary = r"[ \t\n]*(.*?\.)([ \t\n]|$)"
    def __init__(self):
	self.re_summary = re.compile(SummarySplitter.__re_summary, re.S)
    def parse(self, comm):
	"""Split comment into summary and detail. This method uses a regular
	expression to find the first sentence. If the expression fails then
	summary is the whole comment and detail is None. If there is only one
	sentence then detail is still the full comment (you must compare
	them). It then calls _calculateHasDetail to fill in has_detail."""
	mo = self.re_summary.match(comm.detail)
	if mo: comm.summary = mo.group(1)
	else:
	    comm.summary = comm.detail
	    comm.detail = None
	self._calculateHasDetail(comm)
    def _calculateHasDetail(self, comm):
	"""Template method to fill in the has_detail variable. The default
	algorithm follows set has_detail if:
	 . A summary was found (first sentence)
	 . The summary text is different from the detail text (no sentence)
	 . Enums always have detail (the enum values)
	 . Functions have detail if they have an exception spec
	 . Scopes never have detail since they have their own pages for that
	"""
	decl = comm.decl
	# Basic detail check
	has_detail = comm.detail is not comm.summary
	has_detail = has_detail and comm.detail is not None
	# Always show enums
	has_detail = has_detail or isinstance(decl, AST.Enum)
	# Show functions if they have exceptions
	has_detail = has_detail or (isinstance(decl, AST.Function) and len(decl.exceptions()))
	# Don't show detail for scopes (they have their own pages)
	has_detail = has_detail and not isinstance(decl, AST.Scope)
	# Store:
	comm.has_detail = has_detail

class JavadocFormatter (CommentFormatter):
    """A formatter that formats comments similar to Javadoc @tags"""
    # @see IDL/Foo.Bar
    # if a line starts with @tag then all further lines are tags
    __re_see = '@see (([A-Za-z+]+)/)?(([A-Za-z_]+\.?)+)'
    __re_tags = '(?P<text>.*?)\n[ \t]*(?P<tags>@[a-zA-Z]+[ \t]+.*)'
    __re_see_line = '^[ \t]*@see[ \t]+(([A-Za-z+]+)/)?(([A-Za-z_]+\.?)+)(\([^)]*\))?([ \t]+(.*))?$'
    __re_param = '^[ \t]*@param[ \t]+(?P<name>(A-Za-z+]+)([ \t]+(?P<desc>.*))?$'

    def __init__(self):
	"""Create regex objects for regexps"""
	self.re_see = re.compile(self.__re_see)
	self.re_tags = re.compile(self.__re_tags,re.M|re.S)
	self.re_see_line = re.compile(self.__re_see_line,re.M)
    def parse(self, comm):
	"""Parse the comm.detail for @tags"""
	comm.detail = self.parseText(comm.detail, comm.decl)
	comm.summary = self.parseText(comm.summary, comm.decl)
    def extract(self, regexp, str):
	"""Extracts all matches of the regexp from the text. The MatchObjects
	are returned in a list"""
	mo = regexp.search(str)
	ret = []
	while mo:
	    ret.append(mo)
	    start, end = mo.start(), mo.end()
	    str = str[:start] + str[end:]
	    mo = regexp.search(str, start)
	return str, ret

    def parseTags(self, str):
	"""Returns text, tags"""
	# Find tags
	mo = self.re_tags.search(str)
	if not mo: return str, ''
	str, tags = mo.group('text'), mo.group('tags')
	# Split the tag section into lines
	tags = map(string.strip, string.split(tags,'\n'))
	# Join non-tag lines to the previous tag
	joiner = lambda x,y: len(y) and y[0]=='@' and x+[y] or x[:-1]+[x[-1]+y]
	tags = reduce(joiner, tags, [])
	return str, tags

    def parseText(self, str, decl):
	if str is None: return str
	#str, see = self.extract(self.re_see_line, str)
	see_tags, param_tags, return_tag = [], [], None
	str, tags = self.parseTags(str)
	# Parse each of the tags
	for line in tags:
	    tag, rest = string.split(line,' ',1)
	    if tag == '@see':
		see_tags.append(string.split(rest,' ',1))
	    elif tag == '@param':
		param_tags.append(string.split(rest,' ',1))
	    elif tag == '@return':
		return_tag = rest
	    else:
		# Warning: unknown tag
		pass
	return "%s%s%s%s"%(
	    self.parse_see(str, decl),
	    self.format_params(param_tags),
	    self.format_return(return_tag),
	    self.format_see(see_tags, decl)
	)
    def parse_see(self, str, decl):
	"""Parses inline @see tags"""
	# Parse inline @see's  #TODO change to link or whatever javadoc uses
	mo = self.re_see.search(str)
	while mo:
	    groups, start, end = mo.groups(), mo.start(), mo.end()
	    lang = groups[1] or ''
	    tag = self.find_link(groups[2], decl)
	    str = str[:start] + tag + str[end:]
	    end = start + len(tag)
	    mo = self.re_see.search(str, end)
	return str
    def format_params(self, param_tags):
	"""Formats a list of (param, description) tags"""
	if not len(param_tags): return ''
	return "%s<ul>%s</ul>"%(
	    div('tag-param-header',"Parameters:"),
	    string.join(
		map(lambda p:"<li><b>%s</b> - %s</li>"%(p[0],p[1]), param_tags)
	    )
	)
    def format_return(self, return_tag):
	"""Formats a since description string"""
	if not return_tag: return ''
	return "%s<ul><li>%s</li></ul>"%(div('tag-return-header',"Return:"),return_tag)
    def format_see(self, see_tags, decl):
	"""Formats a list of (ref,description) tags"""
	if not len(see_tags): return ''
	seestr = div('tag-see-header', "See Also:")
	seelist = []
	for see in see_tags:
	    ref,desc = see[0], len(see)>1 and see[1] or ''
	    tag = self.find_link(ref, decl)
	    seelist.append(div('tag-see', tag+desc))
	return seestr + string.join(seelist,'')
    def find_link(self, ref, decl):
	"""Given a "reference" and a declaration, returns a HTML link. Various
	methods are tried to resolve the reference."""
	# Remove (...)'s
	index, label = string.find(ref,'('), ref
	if index >= 0: ref = ref[:index]
	# Try up-a-scope + ref
	entry = config.toc.lookup(list(decl.name()[:-1])+[ref])
	if entry: return href(entry.link, label)
	# Try all methods in scope
	entry = self.find_method_entry(ref, decl)
	if entry: return href(entry.link, label)
	# Try ref verbatim
	entry = config.toc.lookup([ref])
	if entry: return href(entry.link, label)
	# Not found
	return label+" "
    def find_method_entry(self, ref, decl):
	"""Tries to find a TOC entry for a method adjacent to decl. The
	enclosing scope is found using the types dictionary, and the
	realname()'s of all the functions compared to ref."""
	scope = config.types[decl.name()[:-1]]
	if not scope: return None
	if not isinstance(scope, Type.Declared): return None
	scope = scope.declaration()
	if not isinstance(scope, AST.Scope): return None
	for decl in scope.declarations():
	    if isinstance(decl, AST.Function):
		if decl.realname()[-1] == ref:
		    return config.toc.lookup(decl.name())
	return None


class SectionFormatter (CommentFormatter):
    """A test formatter"""
    __re_break = '\n[ \t]*\n'

    def __init__(self):
	self.re_break = re.compile(SectionFormatter.__re_break)
    def parse(self, comm):
	comm.detail = self.parse_break(comm.detail)
    def parse_break(self, str):
	if str is None: return str
	mo = self.re_break.search(str)
	while mo:
	    start, end = mo.start(), mo.end()
	    text = '</p><p>'
	    str = str[:start] + text + str[end:]
	    end = start + len(text)
	    mo = self.re_break.search(str, end)
	return '<p>%s</p>'%str



commentParsers = {
    'default' : CommentParser,
}
commentFormatters = {
    'none' : CommentFormatter,
    'ssd' : SSDFormatter,
    'java' : JavaFormatter,
    'summary' : SummarySplitter,
    'javadoc' : JavadocFormatter,
    'section' : SectionFormatter,
}


