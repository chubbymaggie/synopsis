# NameLookup provides the fully scoped name of a given type
#
# Translator creates a Synopsis tree out of an omniidl AST
# 

from omniidl import idlast, idltype, idlvisitor, idlutil
import _omniidl
import sys, getopt, os, os.path, string
from Synopsis import Types

class NameLookup (idlvisitor.TypeVisitor):
    def __init__(self):
        self.__result_type = ""
        self.__basetypes = {
            idltype.tk_void:       "void",
            idltype.tk_short:      "short",
            idltype.tk_long:       "long",
            idltype.tk_ushort:     "unsigned short",
            idltype.tk_ulong:      "unsigned long",
            idltype.tk_float:      "float",
            idltype.tk_double:     "double",
            idltype.tk_boolean:    "boolean",
            idltype.tk_char:       "char",
            idltype.tk_octet:      "octet",
            idltype.tk_any:        "any",
            idltype.tk_TypeCode:   "CORBA::TypeCode",
            idltype.tk_Principal:  "CORBA::Principal",
            idltype.tk_longlong:   "long long",
            idltype.tk_ulonglong:  "unsigned long long",
            idltype.tk_longdouble: "long double",
            idltype.tk_wchar:      "wchar"
            }
    def visitBaseType(self, type):
        self.__result_type = self.__basetypes[type.kind()]
    def visitStringType(self, type):
        if type.bound() == 0:
            self.__result_type = "string"
        else:
            self.__result_type = "string<" + str(type.bound()) + ">"
    def visitWStringType(self, type):
        if type.bound() == 0:
            self.__result_type = "wstring"
        else:
            self.__result_type = "wstring<" + str(type.bound()) + ">"
    def visitSequenceType(self, type):
        type.seqType().accept(self)
        if type.bound() == 0:
            self.__result_type = "sequence<" + self.__result_type + ">"
        else:
            self.__result_type = "sequence<" + self.__result_type + ", " +\
                                  str(type.bound()) + ">"
    def visitFixedType(self, type):
        self.__result_type = "fixed <" + str(type.digits()) + ", " +\
                              str(type.scale()) + ">"
    def visitDeclaredType(self, type):
        self.__result_type = "::" + \
                              idlutil.ccolonName(type.decl().scopedName())
    def lookup(self, type):
        type.accept(self)
        return self.__result_type

class Translator (idlvisitor.AstVisitor):
    def __init__(self):
        self.__names = NameLookup()
        self.__rootNodes = []
        self.__current = []
    def nodes(self): return self.__rootNodes
    def visitAST(self, node):
        for n in node.declarations():
            n.accept(self)

    def visitModule(self, node):
        if node.mainFile() != 1: return
        self.__current.append(Types.Module(node.file(),
                                           node.line(),
                                           "IDL",
                                           "module",
                                           node.identifier(),
                                           node.scopedName()))
        for n in node.definitions():
            n.accept(self)
        if len(self.__current) == 1:
            self.__rootNodes.append(self.__current[0])
        else:
            self.__current[-2].types().append(self.__current[-1])
        self.__current.pop()

    def visitInterface(self, node):
        if node.mainFile() != 1: return
        self.__current.append(Types.Class(node.file(),
                                          node.line(),
                                          "IDL",
                                          "interface",
                                          node.identifier(),
                                          node.scopedName())) 
        for i in node.inherits(): self.__current[-1].parents().append(Types.Inheritance("", i, []))
        for c in node.contents(): c.accept(self)
        if len(self.__current) == 1:
            self.__rootNodes.append(self.__current[0])
        else:
            self.__current[-2].declarations().append(self.__current[-1])
        self.__current.pop()

    def visitForward(self, node):      return
    def visitConst(self, node):        return
    def visitDeclarator(self, node): return
    def visitTypedef(self, node):
        if node.mainFile() != 1: return
        identifiers = []
        for d in node.declarators(): identifiers.append(d.identifier())
        type = Types.Typedef(node.file(),
                             node.line(),
                             "IDL",
                             self.__names.lookup(node.aliasType()),
                             [],
                             identifiers)
        if len(self.__current): self.__current[-1].declarations().append(type)
        else: self.__rootNodes.append(type)

    def visitMember(self, node):
        identifiers = []
        for d in node.declarators(): identifiers.append(d.identifier())
        self.__current[-1].declarations().append(Types.Variable(node.file(),
                                                                node.line(),
                                                                "IDL",
                                                                "member",
                                                                self.__names.lookup(node.memberType()),
                                                                [],
                                                                identifiers,
                                                                ""))
    def visitStruct(self, node):
        if node.mainFile() != 1: return
        self.__current.append(Types.Class(node.file(),
                                          node.line(),
                                          "IDL",
                                          "struct",
                                          node.identifier(),
                                          node.scopedName()))
        for member in node.members(): member.accept(self)
        if len(self.__current) == 1:
            self.__rootNodes.append(self.__current[0])
        else:
            self.__current[-2].declarations().append(self.__current[-1])
        self.__current.pop()
        
    def visitException(self, node):    return
    def visitCaseLabel(self, node):    return
    def visitUnionCase(self, node):    return
    def visitUnion(self, node):        return
    def visitEnumerator(self, node):   return
    def visitEnum(self, node):         return
    def visitAttribute(self, node):
        pre = []
        if node.readonly(): pre.append("readonly")
        interface = self.__current[-1]
        interface.operations().append(Types.Operation(node.file(),
                                                      node.line(),
                                                      "IDL",
                                                      "attribute",
                                                      pre,
                                                      self.__names.lookup(node.attrType()),
                                                      node.identifiers()[0],
                                                      self.__current[-1].scope(),
                                                      []))
    def visitParameter(self, node):
        interface = self.__current[-1]
        operation = interface.operations()[-1]
        pre = []
        if node.direction() == 0: pre.append("in")
        elif node.direction() == 1: pre.append("out")
        else: pre.append("inout")
        post = []
        operation.parameters().append(Types.Parameter(pre,
                                                      self.__names.lookup(node.paramType()),
                                                      post,
                                                      node.identifier()))

    def visitOperation(self, node):
        pre = []
        if node.oneway(): pre.append("oneway")
        interface = self.__current[-1]
        interface.operations().append(Types.Operation(node.file(),
                                                      node.line(),
                                                      "IDL",
                                                      "operation",
                                                      pre,
                                                      self.__names.lookup(node.returnType()),
                                                      node.identifier(),
                                                      self.__current[-1].scope(),
                                                      []))
        for p in node.parameters(): p.accept(self)

    def visitNative(self, node):       return
    def visitStateMember(self, node):  return
    def visitFactory(self, node):      return
    def visitValueForward(self, node): return
    def visitValueBox(self, node):     return
    def visitValueAbs(self, node):     return
    def visitValue(self, node):        return

def __parseArgs(args):
    global preprocessor_args

    preprocessor_args = []
    try:
        opts,remainder = getopt.getopt(args, "I:")
    except getopt.error, e:
        sys.stderr.write("Error in arguments: " + e + "\n")
        sys.exit(1)

    for opt in opts:
        o,a = opt

        if o == "-I":
            preprocessor_args.append("-I" + a)

def parse(file, args):
    global preprocessor_args
    __parseArgs(args)
    if hasattr(_omniidl, "__file__"):
        preprocessor_path = os.path.dirname(_omniidl.__file__)
    else:
        preprocessor_path = os.path.dirname(sys.argv[0])
    preprocessor      = os.path.join(preprocessor_path, "omni-cpp")
    preprocessor_cmd  = preprocessor + " -lang-c++ -undef -D__OMNIIDL__=" + _omniidl.version
    preprocessor_cmd = preprocessor_cmd + " " + string.join(preprocessor_args, " ") + " " + file
    fd = os.popen(preprocessor_cmd, "r")

    tree = _omniidl.compile(fd)
    if tree == None:
        sys.stderr.write("omni: Error parsing " + file + "\n")
        sys.exit(1)
    translator = Translator()
    tree.accept(translator)
    return translator.nodes()
