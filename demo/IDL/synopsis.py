#! /usr/bin/env python

from Synopsis.process import process
from Synopsis.Processor import *
from Synopsis.Parsers import IDL
from Synopsis.Processors import *
from Synopsis.Formatters import HTML
from Synopsis.Formatters.HTML.TreeFormatterJS import TreeFormatterJS

parser = IDL.Parser(include_paths=['.'])

linker = Composite(Unduplicator(),     # remove duplicate and forward declarations
                   SSDComments())      # filter out any non-'//.' comments

format = HTML.Formatter(stylesheet_file = '../html.css',
                        tree_formatter = TreeFormatterJS())

process(parse = parser,
        link = linker,
        format = format)
