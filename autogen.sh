#!/bin/sh
#

conf() 
{
  (cd $1
   echo "Generating $1/configure..."
   autoconf
  )
}

conf Synopsis/Parser/C
conf Synopsis/Parser/C++
conf Synopsis/Parser/C++/gc