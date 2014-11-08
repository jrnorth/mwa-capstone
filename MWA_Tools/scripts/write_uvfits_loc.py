#!/usr/local/bin/python

import psycopg2
import sys
from optparse import OptionParser
import socket


def main():
    usage="Usage: %prog [options]\n"
    usage+="\tRecords the uvfits file location for an Observation ID"
    usage+="\tand version,subversion number." 

    parser = OptionParser(usage=usage)
    parser.add_option('-o','--obsid',dest="obsid",
                      help="Observation ID")
    parser.add_option('-v','--version',dest="version",
                      help="Version of uvfits conversion pipeline")
    parser.add_option('-s','--subversion',dest="subversion",
                      help="Subversion of uvfits conversion pipeline")
    parser.add_option('-f','--file',dest="file_loc",
                      help="File location of uvfits")
    parser.add_option('-c','--comment',dest="comment",
                      help="Comment (optional)")
    parser.add_option('-u','--update',action="store_true",dest="update",default=False,
                      help="Update an existing entry. If the previous entry does not exist, this will do nothing.")

    (options,args) = parser.parse_args()

    if not 'mit.edu' in socket.gethostname():
        print 'Sorry, this script is currently only supported on eor-xx.mit.edu machines.'
        sys.exit(1)

    quit_key=0

    if options.obsid is not None:
        obsid=options.obsid
    else:
        print 'Need an obsid (option -o).'
        quit_key=1

    if options.version is not None:
        version=options.version
    else:
        print 'Version of uvfits file conversion pipeline needed (option -v).'
        quit_key=1
    if options.subversion is not None:
        subversion=options.subversion
    else:
        print 'Subversion needed (option -s).'
        quit_key=1
    if options.file_loc is not None:
        file_loc=options.file_loc
    else:
        print 'File location needed (option -f).'
        quit_key=1
    if options.comment is not None:
        comment=options.comment
    else:
        comment=''

    if quit_key:
        print 'Quitting.'
        sys.exit(1)

    try:
        conn = psycopg2.connect(database='mwa',user='mwa',password='BowTie',host='mwa.mit.edu')
    except:
        print 'Could not connect to mwa database.'
        sys.exit(1)
    cur = conn.cursor()

    if (options.update):
        try:
            cur.execute("UPDATE uvfits_location SET file_location=%s WHERE (obsid,version,subversion)=(%s,%s,%s);",(file_loc,obsid,version,subversion))
        except:
            print 'Trouble updating the database.'
            cur.close()
            conn.close()
            sys.exit(1)
    else:
        try:
            cur.execute("INSERT INTO uvfits_location VALUES (%s,%s,%s,%s,%s);",
                    (obsid,version,subversion,file_loc,comment))
        except:
            print 'Trouble writing to the database.'
            cur.close()
            conn.close()
            sys.exit(1)

    conn.commit()
    cur.close()
    conn.close()
    sys.exit(0)

if __name__=="__main__":
    main()
