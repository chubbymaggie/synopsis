#
# Copyright (C) 2002 Stephen Davies
# Copyright (C) 2003 Stefan Seefeld
# All rights reserved.
# Licensed to the public under the terms of the GNU LGPL (>= 2),
# see the file COPYING for details.
#

import sys, os, os.path, re, string, stat, tempfile
from Synopsis import Util

# The filename where infos are stored
user_emulations_file = '~/.synopsis/cpp_emulations'

# The list of default compilers. Note that the C syntax is not quite
# supported, so including a bazillion different C compilers is futile.
default_compilers = ['cc', 'c++', 'gcc', 'g++', 'cl']

# A cache of the compiler info, loaded from the emulations file or calculated
# by inspecting available compilers
compiler_infos = {}

# A map of failed compilers. This map is kept for the lifetype of Synopsis, so
# you may have to restart it if a compiler is 'fixed'
failed = {}

# The temporary filename
temp_filename = None

def get_temp_file():
    """Returns the temporary filename. The temp file is created, but is left
    empty"""
    global temp_filename
    if temp_filename: return temp_filename
    temp_filename = tempfile.mktemp('.cc')
    f = open(temp_filename, 'w')
    f.close()
    return temp_filename

def cleanup_temp_file():
    """Removes the temporary file and resets the filename"""
    global temp_filename
    if temp_filename:
        os.unlink(temp_filename)
        temp_filename = None

class CompilerInfo:
    """Info about one compiler.

    @attr compiler The name of the compiler, typically the executable name,
    which must either be in the path or given as an absolute pathname
    @attr is_custom True if this is a custom compiler - in which case it will
    never be updated automatically.
    @attr timestamp The timestamp of the compiler binary
    @attr include_paths A list of strings indicating the include paths
    @attr macros A list of string 2-tuples indicating key=value pairs for
    macros. A value of '' (empty string) indicates an empty definition. A
    value of None (not a string) indicates that the macro should be undefined.
    """
    def __init__(self, compiler, is_custom, timestamp, include_paths, macros):
        self.compiler = compiler
        self.is_custom = is_custom
        self.timestamp = timestamp
        self.include_paths = include_paths
        self.macros = macros

def main():
    """The main function - parses the arguments and controls the program"""
    if len(sys.argv) < 2:
        print usage
        return

    filename = sys.argv[1]
    print "Filename is ", filename
    if len(sys.argv) > 2:
        compilers = sys.argv[2:]
    else:
        compilers = default_compilers
    print "compilers are:", compilers

    infos = get_compiler_infos(compilers)
    if not infos:
        print "No compilers found. Not writing file!"
        return

    file = open(filename, 'wt')
    write_compiler_infos(infos, file)
    file.close()

    print "Found info about the following compilers:"
    print string.join(map(lambda x: x[0], infos), ', ')

def get_fallback(preferred, is_first_time):
    """Tries to return info from a fallback compiler, and prints a warning
    message to the user, unless their preferred compiler was 'none'"""
    if is_first_time and preferred != 'none':
        print "Warning: The specified compiler (%s) could not be found."%(preferred,)
        print "You may want to retry with the full pathname of the compiler"
        print "or with it in your path. If you don't have this compiler, you"
        print "will need to modify the C++ Parser part of your config file."
    for compiler in ('g++', 'gcc', 'c++', 'cc'):
        if compiler_infos.has_key(compiler):
            if is_first_time:
              print "Warning: Falling back to compiler '%s'"%(compiler,)
            return compiler_infos[compiler]
    if preferred != 'none':
        print "Warning: Unable to fallback to a default compiler emulation."
        print "Unless you have set appropriate paths, expect errors."
    return None

def get_compiler_info(compiler):
    """Returns the compiler info for the given compiler. If non is
    specified (''), return the first available one. The info is returned
    as a CompilerInfo object, or None if the compiler isn't found. 
    """
    global failed, compiler_infos
    # Check if this compiler has already been found to not exist
    if failed.has_key(compiler):
        return get_fallback(compiler, 0)
    # See if already found it
    if len(compiler_infos) == 0:
        # Try to load the emulations file
        compiler_infos = load_compiler_infos()
    # if no compiler was specified take first available one
    if not compiler and len(compiler_infos) != 0:
        compiler = compiler_infos.keys()[0]
    # See if wanted compiler was in file
    if compiler_infos.has_key(compiler):
        info = compiler_infos[compiler]
        if info.is_custom: return info
        file_stamp = get_compiler_timestamp(compiler)
        # If compiler hasn't changed since then, return cached info
        if file_stamp and info.timestamp == file_stamp:
            return info
    elif compiler:
        # Add compiler to map, but with a dummy value to indicate nothing is
        # known about it
        compiler_infos[compiler] = None
    
    # Regenerate infos
    refresh_compiler_infos(compiler_infos)

    # Cache results to disk
    write_compiler_infos(compiler_infos)

    if not compiler and len(compiler_infos) != 0:
        compiler = compiler_infos.keys()[0]

    # Return discovered info, if compiler was found
    if compiler_infos.has_key(compiler):
        return compiler_infos[compiler]
    else:
        return get_fallback(compiler, 1)

def load_compiler_infos():
    """Loads the compiler infos from a file"""
    glob = {'__builtins__':{}, '__name__':'__main__', 'setattr':setattr}
    filename = os.path.expanduser(user_emulations_file)
    try: execfile(filename, glob, glob)
    except IOError: return {}
    if glob.has_key('infos'):
        return glob['infos']
    return {} 

def get_compiler_timestamp(compiler):
    """Returns the timestamp for the given compiler, or 0 if not found"""
    path = os.getenv('PATH', os.defpath)
    path = string.split(path, os.pathsep)
    for directory in path:
        # Try to stat the compiler in this directory, if it exists
        filename = os.path.join(directory, compiler)
        if os.name == 'nt': filename += '.exe'
        try: stats = os.stat(filename)
        except OSError: continue
        return stats[stat.ST_CTIME]
    # Not found
    return 0

def refresh_compiler_infos(infos):
    """Refreshes the list of infos, by rediscovering all non-custom compilers
    in the map. The map is modified in-place."""
    global failed
    # Refresh each non-custom compiler in the map 
    for compiler, info in infos.items():
        if info and info.is_custom:
            # Skip custom compilers
            continue
        if failed.has_key(compiler):
            # Skip compilers that have already failed
            del infos[compiler]
            continue
        info = find_compiler_info(compiler)
        if info: infos[compiler] = info
        else:
            del infos[compiler]
            failed[compiler] = None
    # Now try to add defaults
    for compiler in default_compilers:
        # Don't retry already-failed compilers
        if failed.has_key(compiler):
            continue
        info = find_compiler_info(compiler)
        if info: infos[compiler] = info

    # Cleanup the temp file
    cleanup_temp_file()
        

#def get_compiler_infos(compilers):
#    infos = filter(None, map(find_compiler_info, compilers))
#    return infos

def write_compiler_infos(infos):
    filename = os.path.expanduser(user_emulations_file)
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        os.mkdir(dirname)
    file = open(filename, 'wt')
    writer = Util.PyWriter(file)
    writer.write_top('"""This file contains info about compilers for use by '+
    'Synopsis.\nSee the Synopsis RefManual for info on customizing this list."""\n')
    writer.ensure_struct()
    writer.write('infos = {\n')
    writer.indent()
    ccomma = 0
    for compiler, info in infos.items():
        if ccomma: writer.write(",\n")
        else: ccomma = 1
        writer.write("'%s' : struct(\n"%compiler)
        writer.write('is_custom = %d,\n' % info.is_custom)
        writer.write('timestamp = %d,\n' % info.timestamp)
        writer.write("include_paths = ")
        writer.write_long_list(info.include_paths)
        writer.write(",\nmacros = ")
        writer.write_long_list(info.macros)
        writer.write(")")
    writer.outdent()
    writer.write("\n}\n")
    writer.flush()
    file.close()
    
def find_ms_compiler_info(compiler):
    """Try to find a compiler on the windows platform.
    Return tuple of include path list and macro dictionary."""

    vc6 = ('SOFTWARE\\Microsoft\\DevStudio\\6.0\\Products\\Microsoft Visual C++', 'ProductDir')
    vc7 = ('SOFTWARE\\Microsoft\\VisualStudio\\7.0', 'InstallDir')
    vc71 = ('SOFTWARE\\Microsoft\\VisualStudio\\7.1', 'InstallDir')

    vc6_macros =  [('__uuidof(x)', 'IID()'),
                   ('__int64', 'long long'),
                   ('_MSC_VER', '1200'),
                   ('_MSC_EXTENSIONS', ''),
                   ('_WIN32', ''),
                   ('_M_IX86', ''),
                   ('_WCHAR_T_DEFINED', ''),
                   ('_INTEGRAL_MAX_BITS', '64'),
                   ('PASCAL', ''),
                   ('RPC_ENTRY', ''),
                   ('SHSTDAPI', 'HRESULT'),
                   ('SHSTDAPI_(x)', 'x')]
    vc6_paths = ['Include']

    vc7_macros = [('__forceinline', '__inline'),
                  ('__uuidof(x)', 'IID()'),
                  ('__w64', ''),
                  ('__int64', 'long long'),
                  ('_MSC_VER', '1300'),
                  ('_MSC_EXTENSIONS', ''),
                  ('_WIN32', ''),
                  ('_M_IX86', ''),
                  ('_WCHAR_T_DEFINED', ''),
                  ('_INTEGRAL_MAX_BITS', '64'),
                  ('PASCAL', ''),
                  ('RPC_ENTRY', ''),
                  ('SHSTDAPI', 'HRESULT'),
                  ('SHSTDAPI_(x)', 'x')]
    vc7_paths = ['..\\..\\Vc7\\Include',
                 '..\\..\\Vc7\\PlatformSDK\\Include']

    vc71_macros = [('__forceinline', '__inline'),
                   ('__uuidof(x)', 'IID()'),
                   ('__w64', ''),
                   ('__int64', 'long long'),
                   ('_MSC_VER', '1310'),
                   ('_MSC_EXTENSIONS', ''),
                   ('_WIN32', ''),
                   ('_M_IX86', ''),
                   ('_WCHAR_T_DEFINED', ''),
                   ('_INTEGRAL_MAX_BITS', '64'),
                   ('PASCAL', ''),
                   ('RPC_ENTRY', ''),
                   ('SHSTDAPI', 'HRESULT'),
                   ('SHSTDAPI_(x)', 'x')]
    vc71_paths = ['..\\..\\Vc7\\Include',
                  '..\\..\\Vc7\\PlatformSDK\\Include']

    compilers = [(vc71, vc71_macros, vc71_paths),
                 (vc7, vc7_macros, vc7_paths),
                 (vc6, vc6_macros, vc6_paths)]

    paths, macros = [], []

    import _winreg
    for c in compilers:
        try:
            key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, c[0][0])
            path, type = _winreg.QueryValueEx(key, c[0][1])
            paths.extend([os.path.join(str(path), p) for p in c[2]])
            macros.extend(c[1])
            break
        except:
            continue

    return paths, macros

def find_gcc_compiler_info(compiler):
    # Run the compiler with -v and get the displayed info

    paths, macros = [], []

    command = 'LANG=en_US %s -E -v -dD %s'%(compiler, get_temp_file())
    cin, out,err = os.popen3(command)
    lines = err.readlines()
    cin.close()
    err.close()

    state = 0
    for line in lines:
        line = line.rstrip()
        if state == 0:
            if line[:11] == 'gcc version': state = 1
        elif state == 1:
            # cpp command line
            args = string.split(line)
            for arg in args:
                if arg[0] != '-':
                    continue
                if arg[1] == 'D':
                    if arg.find('=') != -1:
                        macros.append(tuple(string.split(arg[2:], '=', 1)))
                    else:
                        macros.append((arg[2:], ''))
                # TODO: do we need the asserts?
            state = 2
        elif state == 2:
            if line == '#include <...> search starts here:':
                state = 3
        elif state == 3:
            if line == 'End of search list.':
                state = 4
            else:
                paths.append(line.strip())

    # now read built-in macros
    state = 0
    for line in out.readlines():
        line = line.rstrip()
        if state == 0:
            if line == '# 1 "<built-in>"':
                state = 1
        elif state == 1:
            if line.startswith('#define '):
                tokens = line[8:].split(' ', 1)
                if len(tokens) == 1: tokens.append('')
                macros.append(tuple(tokens))
            elif line == '# 1 "<command line>"':
                state = 2

    out.close()
        
    # Per-compiler adjustments
    for name, value in tuple(macros):
        if name == '__GNUC__' and value == '2':
            # gcc 2.x needs this or it uses nonstandard syntax in the headers
            macros.append(('__STRICT_ANSI__', ''))

    return paths, macros

def find_compiler_info(compiler):
    print "Finding info for '%s' ..."%compiler,

    paths, macros = [], []

    if compiler == 'cl' and os.name == 'nt':
        paths, macros = find_ms_compiler_info(compiler)

    else:
        paths, macros = find_gcc_compiler_info(compiler)
        
    if not paths or not macros:
        print "Failed"
        return None
    print "Found"

    timestamp = get_compiler_timestamp(compiler)
    return CompilerInfo(compiler, 0, timestamp, paths, macros)

   
