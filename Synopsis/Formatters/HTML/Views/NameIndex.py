# $Id: NameIndex.py,v 1.9 2002/11/01 03:39:21 chalky Exp $
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
# $Log: NameIndex.py,v $
# Revision 1.9  2002/11/01 03:39:21  chalky
# Cleaning up HTML after using 'htmltidy'
#
# Revision 1.8  2002/07/04 06:43:18  chalky
# Improved support for absolute references - pages known their full path.
#
# Revision 1.7  2002/03/14 00:19:47  chalky
# Added demo of template specializations, and fixed HTML formatter to deal with
# angle brackets in class names :)
#
# Revision 1.6  2001/07/10 14:41:22  chalky
# Make treeformatter config nicer
#
# Revision 1.5  2001/07/05 05:39:58  stefan
# advanced a lot in the refactoring of the HTML module.
# Page now is a truely polymorphic (abstract) class. Some derived classes
# implement the 'filename()' method as a constant, some return a variable
# dependent on what the current scope is...
#
# Revision 1.4  2001/07/05 02:08:35  uid20151
# Changed the registration of pages to be part of a two-phase construction
#
# Revision 1.3  2001/06/28 07:22:18  stefan
# more refactoring/cleanup in the HTML formatter
#
# Revision 1.2  2001/06/26 04:32:16  stefan
# A whole slew of changes mostly to fix the HTML formatter's output generation,
# i.e. to make the output more robust towards changes in the layout of files.
#
# the rpm script now works, i.e. it generates source and binary packages.
#
# Revision 1.1  2001/02/13 02:54:15  chalky
# Added Name Index page
#
#

import os
from Synopsis.Core import AST, Type
from Synopsis.Formatter.HTML import core, Tags, Page
from Tags import *
from core import config

class NameIndex (Page.Page):
    """Creates an index of all names on one page in alphabetical order"""
    def __init__(self, manager):
	Page.Page.__init__(self, manager)

    def filename(self): return config.files.nameOfSpecial('NameIndex')
    def title(self): return 'Synopsis - Name Index'

    def register(self):
	self.manager.addRootPage(self.filename(), 'Name Index', 'main', 1)

    def process(self, start):
	"""Creates the page. It is created as a list of tables, one for each
	letter. The tables have a number of columns, which is 2 by default.
	_processItem is called for each item in the dictionary."""
	self.start_file()
	self.write(self.manager.formatHeader(self.filename()))
	self.write(entity('h1', "Name Index"))
	self.write('<i>Hold the mouse over a link to see the scope of each name</i>')

	dict = self._makeDict()
	keys = dict.keys()
	keys.sort()
	columns = 2 # TODO set from config
	linker = lambda key: '<a href="#%s">%s</a>'%(ord(key),key)
	self.write(div('nameindex-index', string.join(map(linker, keys))))
	for key in keys:
	    self.write('<a name="%s">'%ord(key)+'</a>')
	    self.write(entity('h2', key))
	    self.write('<table border=0 width="100%" summary="table of names">')
	    self.write('<col width="*">'*columns)
	    self.write('<tr>')
	    items = dict[key]
	    numitems = len(items)
	    start = 0
	    for column in range(columns):
		end = numitems * (column+1) / columns
		self.write('<td valign=top>')
		for item in items[start:end]:
		    self._processItem(item)
		self.write('</td>')
		start = end
	    self.write('</tr></table>')
	
	self.end_file()

    def _makeDict(self):
	"""Returns a dictionary of items. The keys of the dictionary are the
	headings - the first letter of the name. The values are each a sorted
	list of items with that first letter."""
	decl_filter = lambda type: isinstance(type, Type.Declared)
	def name_cmp(a,b):
	    a, b = a.name(), b.name()
	    res = cmp(a[-1],b[-1])
	    if res == 0: res = cmp(a,b)
	    return res
	dict = {}
	def hasher(type, dict=dict):
	    name = type.name()
	    try: key = name[-1][0]
	    except:
		print 'name:',name, 'type:',repr(type)
		raise
	    if key >= 'a' and key <= 'z': key = chr(ord(key) - 32)
	    if dict.has_key(key): dict[key].append(type)
	    else: dict[key] = [type]
	# Fill the dict
	map(hasher, filter(decl_filter, config.types.values()))
	# Now sort the dict
	for items in dict.values():
	    items.sort(name_cmp)
	return dict

    def _processItem(self, type):
	"""Process the given name for output"""
	name = type.name()
	decl = type.declaration() # non-declared types are filtered out
	if isinstance(decl, AST.Function):
	    realname = decl.realname()[-1] + '()'
	else:
	    realname = anglebrackets(name[-1])
	self.write('\n')
	title = string.join(name, '::')
	type = decl.type()
	name = self.reference(name, (), realname, title=title)+' '+type
	self.write(div('nameindex-item', name))

htmlPageClass = NameIndex
