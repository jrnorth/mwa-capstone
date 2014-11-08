#!/usr/local/bin/python
# A simple script to get the number of files in the mandc db for a given obsid

import psycopg2
import sys
from optparse import OptionParser
import socket
import mwaconfig
import base64

def main():
    usage="Usage: %prog [options]\n"
    usage+="\tFinds the number of files associated with an observation ID"
    
    parser = OptionParser(usage=usage)
    parser.add_option('-o','--obsid',dest="obsid",help="Observation ID")
    parser.add_option('-a','--count_all',action="store_true",dest="count_all",default=False,
                      help="Count all files (including flag files)")
    parser.add_option('-f','--count_flag',action="store_true",dest="count_flag",default=False,
                      help='Count only flag files (zipped, so usually 1 or 0)')

    (options,args) = parser.parse_args()

    if options.obsid is not None:
        obsid=options.obsid
    else:
        print "Observation ID required"
        sys.exit(1)
    
    try:
        conn = psycopg2.connect(database=mwaconfig.mandc.dbname, user=mwaconfig.mandc.dbuser, password=base64.decodestring(mwaconfig.mandc.dbpass), host=mwaconfig.mandc.dbhost)
    except:
        print 'Could not connect to mandc database.'
        sys.exit(1)
    cur=conn.cursor()
    try:
        if options.count_all:
            cur.execute("select count(*) from data_files where observation_num=%s",[obsid])
        elif options.count_flag:
            cur.execute("select count(*) from data_files where observation_num=%s and filename like '%%flags.zip'",[obsid])
        else:
            cur.execute("select count(*) from data_files where observation_num=%s and filename like '%%.fits'",[obsid])
    except:
        print 'Trouble querying the database'
        sys.exit(1)

    nfiles=cur.fetchone()
    if nfiles is not None:
        print nfiles[0]
    else:
        print 0

    sys.exit(0)

if __name__=="__main__":
    main()
