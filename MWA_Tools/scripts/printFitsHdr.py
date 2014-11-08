#!/usr/bin/python

# a simple tool to print the first header in a FITS file as a series of lines
# with newlines after each header item. It stops when it finds a line starting
# with "END     "
# this is useful for greping things out of FITS headers and not accidentally
# finding the string in the file data when using grep on the whole file
# Randall Wayth. Feb, 2013

import sys

def printFitsHdr(fp):
  """print the primary HDU from an open file handle"""
  theend=False
  count=0
  endstr="END     "
  while not theend:
    # read 80 chars (a line) from the header
    line=fp.read(80)
    if line[0:len(endstr)]==endstr:
      theend=True
    print line
    count+=1
    if count>1000:	# stop spewing out megabytes by mistake
      theend=True

def usage():
  print >> sys.stderr, "Usage: "+sys.argv[0]+" filename"
  print >> sys.stderr, "\tuse '-' for filename to read from stdin"
  sys.exit(0);

if __name__ == "__main__":
  if len(sys.argv)==1:
    usage();
  if sys.argv[1]=='-':
    fp=sys.stdin
  else:
    fp=open(sys.argv[1])
  printFitsHdr(fp)

