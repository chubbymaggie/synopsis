# Config file for Perceps demo
# Files have a strange commenting pattern
# Demonstates extensibility of Synopsis

from Synopsis.Config import Base

class Config (Base):
    class Parser:
	class CXX (Base.Parser.CXX):
	    include_path = ['.'] # add current dir to include path
	    main_file = 1 # don't display #included stuff
	    extract_tails = 1 # Look for trailing comments
	    preprocessor = 'gcc'
	modules = {
	    'C++':CXX,
	}
	    
    class Linker:
	class Linker (Base.Linker.Linker):
	    comment_processors = [
		('config.py', 'PercepsCommProcessor'), # use the processor below
		('config.py', 'PercepsCommSplitter'), # use the processor below
	    ]
	modules = {
	    'Linker':Linker,
	}

    class Formatter:
	class HTML (Base.Formatter.HTML):
	    stylesheet_file = '../html.css'
	    comment_formatters = [
		'javadoc', # also use javadoc to format params and returns
		'section' # and section to insert blank lines occasionally
	    ]
	class HTML_Doxygen (Base.Formatter.HTML_Doxygen):
	    stylesheet_file = '../html-doxy.css'
	    comment_formatters = [
		'javadoc', # also use javadoc to format params and returns
		'section' # and section to insert blank lines occasionally
	    ]
	modules = Base.Formatter.modules
	modules['HTML'] = HTML
	modules['HTML_Doxygen'] = HTML_Doxygen

from Synopsis.Linker.Comments import Previous
from Synopsis.Core import AST

class PercepsCommProcessor (Previous):
    """Maps all comments to the previous definitions, except for classes and
    modules"""
    def checkPrevious(self, decl):
	"""Moves comment to previous declaration unless class or module"""
	if not len(decl.comments()): return
	if not self.last: return
	if isinstance(self.last, AST.Scope): return
	self.last.comments().extend(decl.comments())
	del decl.comments()[:]

from Synopsis.Core.AST import CommentTag
from Synopsis.Linker.Comments import CommentProcessor
import re, string

class PercepsCommSplitter (CommentProcessor):
    __c_sums = '(?P<sums>([ \t]*//: ?[^\n]*\n)*)' # Matches all summaries
    __c_dets = '(?P<dets>([ \t]*//([^:!][^\n]*)?\n)*)' # Matches all details
    __c_spec = '(?P<spec>([ \t]*//![^\n]*\n)*)' # Matches all specials
    __re_comment = '[ \t\n]*%s%s%s'%(__c_sums,__c_dets,__c_spec) # Matches a valid comment
    __re_sum = '[ \t]*//: ?(?P<text>[^\n]*\n)' # Extract text from a summary line
    __re_det = '[ \t]*// ?(?P<text>[^\n]*\n)' # Extract text from a detail line
    __re_spec = '[ \t]*//!(?P<name>[^:]*): (?P<text>[^\n]*\n)' # Extract command and text from a special line
    __re_star = r'/\*(.*?)\*/'
    def __init__(self):
	"Compile regular expressions"
	self.re_comment = re.compile(self.__re_comment, re.M| re.S)
	self.re_sum = re.compile(self.__re_sum, re.M)
	self.re_det = re.compile(self.__re_det, re.M)
	self.re_spec = re.compile(self.__re_spec, re.M)
	self.re_star = re.compile(self.__re_star, re.S)
    def strip_star(self, str):
	"""Strips all star-format comments from the docstring"""
	mo = self.re_star.search(str)
	while mo:
	    str = str[:mo.start()] + str[mo.end():]
	    mo = self.re_star.search(str)
	return str
    def process(self, decl):
	"""Parses the comment and keeps only valid comments. Specials are
	converted to javadoc tags if we know about them, since the javadoc
	formatter already does a good job of formatting them."""
        # First combine
        comments = decl.comments()
        if not len(comments):
            return
        comment = comments[0]
        tags = comment.tags()
        if len(comments) > 1:
            # Should be rare to have >1 comment
            for extra in comments[1:]:
                tags.extend(extra.tags())
                comment.set_text(comment.text() + extra.text())
            del comments[1:]
        # Now decide how much of the comment is the summary

	mo = self.re_comment.search(self.strip_star(comment.text()))
	if mo:
	    sums = mo.group('sums') or ''
	    dets = mo.group('dets') or ''
	    spec = mo.group('spec') or ''
	    # Match sums
	    summary = ''
	    mo = self.re_sum.match(sums)
	    while mo:
		summary = summary + mo.group('text')
		sums = sums[mo.end():]
		mo = self.re_sum.match(sums)
	    comment.set_summary(summary)
	    # Match dets
	    detail = summary
	    mo = self.re_det.match(dets)
	    while mo:
		detail = detail + mo.group('text')
		dets = dets[mo.end():]
		mo = self.re_det.match(dets)
	    comment.set_text(detail)
	    # Match specs
	    mo = self.re_spec.match(spec)
	    while mo:
		name, text = mo.groups()
		# Convert to javadoc style tags
		if name == 'param':
		    # Get rid of extra '-'
		    pair = string.split(text, ' - ', 1)
		    text = string.join(pair)
		    name = '@param'
		elif name == 'retval':
		    name = '@return'
		elif name == 'also':
		    # Get rid of extra '-'
		    pair = string.split(text, ' - ', 1)
		    text = string.join(pair)
		    name = '@see'
		comment.tags().append(CommentTag(name, text))
		spec = spec[mo.end():]
		mo = self.re_spec.match(spec)
	else:
	    # Invalid comment - set it to empty
	    del decl.comments()[0]
	

