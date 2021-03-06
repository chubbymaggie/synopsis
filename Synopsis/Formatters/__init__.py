#
# Copyright (C) 2008 Stefan Seefeld
# All rights reserved.
# Licensed to the public under the terms of the GNU LGPL (>= 2),
# see the file COPYING for details.
#

import codecs

import os, stat
try:
    import hashlib
    md5 = hashlib.md5
except ImportError:
    # 2.4 compatibility
    import md5
    md5 = md5.new


def quote_name(name):
    """Quotes a (file-) name to remove illegal characters and keep it
    within a reasonable length for the filesystem.
   
    The md5 hash function is used if the length of the name after quoting is
    more than 100 characters. If it is used, then as many characters at the
    start of the name as possible are kept intact, and the hash appended to
    make 100 characters.
   
    Do not pass filenames with meaningful extensions to this function, as the
    hash could destroy them."""
   
    original = name # save the old name
   
    # a . is usually an extension, eg source page filename: "_page-foo.hpp" + .html
    # name = re.sub('\.','_',name) 
    # The . is arbitrary..
    for p in [('<', '.L'), ('>', '.R'), ('(', '.l'), (')', '.r'), ('::', '-'),
              (':', '.'), ('&', '.A'), ('*', '.S'), (' ', '.s'), (',', '.c'), (';', '.C')]:
        name = name.replace(*p)
   
    if len(name) > 100:
        digest = md5(original).hexdigest()
        # Keep as much of the name as possible
        name = name[:100 - len(digest)] + digest

    return name


def open_file(path, mode=511):
    """Open a file for writing. Create all intermediate directories."""

    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory, mode)
    return open(path, 'w+')
        

def open_file_with_encoding(path, enc, mode=511):
    """Open a file for writing. Create all intermediate directories."""

    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory, mode)
    return codecs.open(path, 'w+', encoding=enc)
        

def copy_file(src, dest):
    """Copy src to dest, if dest doesn't exist yet or is outdated."""

    filetime = os.stat(src)[stat.ST_MTIME]
    if not os.path.exists(dest) or filetime > os.stat(dest)[stat.ST_MTIME]:
        open_file(dest).write(open(src, 'r').read())
    

def join_paths(prefix, path):
    """
    This function joins `prefix` and `path`, irrespectively of whether
    `path` is absolute or not. To do this portably is non-trivial."""

    # FIXME: Figure out how to do this portably.
    if path.startswith('/'):
        path = path[1:]
    return os.path.join(prefix, path)
