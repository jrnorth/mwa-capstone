#!/usr/local/bin/python

import psycopg2
import sys
from optparse import OptionParser
import socket


def main():
    usage="Usage: %prog [options]\n"
    usage+="\tReads the uvfits versions stored in mwa database."

    parser = OptionParser(usage=usage)
    parser.add_option('-v','--version',dest="version",
                      help="Version of uvfits conversion pipeline")
    parser.add_option('-s','--subversion',dest="subversion",
                      help="Subversion of uvfits conversion pipeline")

    (options,args) = parser.parse_args()

    if not 'mit.edu' in socket.gethostname():
        print 'Sorry, this script is currently only supported on eor-xx.mit.edu machines.'
        sys.exit(1)

    conditions=''
    if options.version is not None:
        conditions = 'WHERE version='+str(options.version)
    if options.subversion is not None:
        if options.version is not None:
            conditions += ' AND subversion='+str(options.subversion)
        else:
            conditions = 'WHERE subversion='+str(options.subversion)

    try:
        conn = psycopg2.connect(database='mwa',user='mwa',password='BowTie',host='mwa.mit.edu')
    except:
        print 'Could not connecto to mwa database.'
        sys.exit(1)
    cur = conn.cursor()
    print conditions
    query = "SELECT * FROM uvfits_version "+conditions+";"
    cur.execute(query)
    try:
        cur.execute(query)
    except:
        print 'Trouble querying the database.'
        sys.exit(1)
    
    result=cur.fetchall()
    if result is not None:
        print result
    else:
        print ''

    sys.exit(0)


if __name__=="__main__":
    main()
