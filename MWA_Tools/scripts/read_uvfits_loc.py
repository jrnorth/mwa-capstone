#!/usr/local/bin/python

import psycopg2
import sys
from optparse import OptionParser
import socket


def main():
    usage="Usage: %prog [options]\n"
    usage+="\tFinds the uvfits file location for an Observation ID"
    usage+="\tand version,subversion number." 

    parser = OptionParser(usage=usage)
    parser.add_option('-o','--obsid',dest="obsid",
                      help="Observation ID")
    parser.add_option('-v','--version',dest="version",
                      help="Version of uvfits conversion pipeline")
    parser.add_option('-s','--subversion',dest="subversion",
                      help="Subversion of uvfits conversion pipeline")

    (options,args) = parser.parse_args()

    if not 'mit.edu' in socket.gethostname():
        print 'Sorry, this script is currently only supported on eor-xx.mit.edu machines.'
        sys.exit(1)

    quit_key=0

    if options.obsid is not None:
        obsid=options.obsid
    else:
        print 'Need an obsid to find uvfits file location (option -o).'
        quit_key=1

    if options.version is not None:
        version=options.version
    else:
        print 'Version of uvfits conversion pipeline needed (option -v).'
        quit_key=1
    if options.subversion is not None:
        subversion=options.subversion
    else:
        print 'Subversion needed (option -s).'
        quit_key=1

    if quit_key:
        print 'Quitting.'
        sys.exit(1)

    try:
        conn = psycopg2.connect(database='mwa',user='mwa',password='BowTie',host='mwa.mit.edu')
    except:
        print 'Could not connecto to mwa database.'
        sys.exit(1)
    cur = conn.cursor()
    try:
        cur.execute("SELECT file_location FROM uvfits_location WHERE obsid=%s AND version=%s AND subversion=%s;",(obsid,version,subversion))
    except:
        print 'Trouble querying the database.'
        sys.exit(1)
    
    result=cur.fetchone()
    if result is not None:
        if '-1' in result:
            sys.exit(1)
        else:
            print result[0]
    else:
        print ''

    sys.exit(0)

if __name__=="__main__":
    main()
