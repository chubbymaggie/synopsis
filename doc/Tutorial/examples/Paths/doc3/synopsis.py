from Synopsis.process import process
from Synopsis.Processor import Processor, Parameter, Composite
from Synopsis.Parsers import Cxx
from Synopsis.Processors import *
from Synopsis.Processors.Comments import SSComments
from Synopsis.Processors.Comments import SSDComments
from Synopsis.Processors.Comments import JavaComments
from Synopsis.Processors.Comments import Previous
from Synopsis.Processors.Comments import JavaTags
from Synopsis.Processors.Comments import Grouper1
from Synopsis.Formatters import HTML
from Synopsis.Formatters.HTML.FileLayout import *
from Synopsis.Formatters.HTML.TreeFormatterJS import *
from Synopsis.Formatters.HTML.Views import *
from Synopsis.Formatters.HTML import Comments
from Synopsis.Formatters import Dot

cxx = Cxx.Parser(base_path='../src',
                 syntax_prefix='links',
                 xref_prefix='xref')

cxx_ssd = Composite(cxx, SSDComments())

html = HTML.Formatter(file_layout = NestedFileLayout(),
                      tree_formatter = TreeFormatterJS(),
                      comment_formatters = [Comments.QuoteHTML(),
                                            Comments.Section(),
                                            Comments.Javadoc()],
                      views = [FramesIndex(),
                               Scope(),
                               Source(prefix = 'links'),
                               XRef(xref_file = 'Paths.xref'),
                               ModuleListing(),
                               ModuleIndexer(),
                               FileListing(),
                               FileIndexer(),
                               FileDetails(),
                               InheritanceTree(),
                               InheritanceGraph(),
                               NameIndex()])

process(cxx_ssd = cxx_ssd,
        cxx_ss = Composite(cxx, SSComments()),
        cxx_ssd_prev = Composite(cxx, SSDComments(), Previous()),
        cxx_javadoc = Composite(cxx, JavaComments(), JavaTags()),
        link = Linker(Grouper1()),
        xref = XRefCompiler(prefix='xref'),
        html = html)
