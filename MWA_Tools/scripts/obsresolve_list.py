#! /usr/bin/env python
import sys, os

if (len(sys.argv) != 2):
    print 'Usage: obsresolve_list.py [file containing list of obs IDs]'
else:

    listfile = str(sys.argv[1])

    list_file = open(listfile)

    for line in list_file:

        obsID = str(line)
        
        cmd = "obsresolve.py -r ngas01.ivec.org -s ngas01.ivec.org -o %s" % obsID

        print cmd

        os.system(cmd)


    list_file.close()
