from Synopsis.process import process
from Synopsis.Processor import Processor, Parameter, Composite
from Synopsis.Parsers import Cxx
from Synopsis.Processors import *
from Synopsis.Processors import Comments
from Synopsis.Formatters import SXR

cxx = Cxx.Parser(base_path='../src/',
                 syntax_prefix='links',
                 xref_prefix='xref')

ssd = Comments.Translator(filter = Comments.SSDFilter(),
                          processor = Comments.Grouper())
ss = Comments.Translator(filter = Comments.SSFilter(),
                         processor = Comments.Grouper())
ssd_prev = Comments.Translator(filter = Comments.SSDFilter(),
                               processor = Composite(Comments.Previous(),
                                                     Comments.Grouper()))
javadoc = Comments.Translator(markup='javadoc',
                              filter = Comments.JavaFilter(),
                              processor = Comments.Grouper())

process(cxx_ssd = Composite(cxx, ssd),
        cxx_ss = Composite(cxx, ss),
        cxx_ssd_prev = Composite(cxx, ssd_prev),
        cxx_javadoc = Composite(cxx, javadoc),
        link = Linker(),
        sxr = SXR.Formatter(src_dir = '../src/',
                            xref_prefix='xref',
                            syntax_prefix='links'))
