#!/usr/local/bin/python

import psycopg2
import sys
from optparse import OptionParser
import socket

def main():
    usage="Usage: %prog [options]\n"
    usage+="\tRecords a uvfits conversion version to the database."
    usage+="\tNote that a version is required before recording the uvfits file locations." 

    parser = OptionParser(usage=usage)
    parser.add_option('-v','--version',dest="version",
                      help="Version of uvfits conversion pipeline (REQUIRED)")
    parser.add_option('-s','--subversion',dest="subversion",
                      help="Subversion of uvfits conversion pipeline (REQUIRED)")
    parser.add_option('-c','--comment',dest="comment",
                      help="Comment (REQUIRED for entry creation)")
    parser.add_option('-f','--follow_up',dest="follow_up",
                      help="Follow up on how the run went (optional)")
    parser.add_option('-u','--update',action="store_true",dest="update",default=False,
                      help="Update an existing entry. If the previous entry does not exist, this will do nothing.")

    (options,args) = parser.parse_args()

    if not 'mit.edu' in socket.gethostname():
        print 'Sorry, this script is currently only supported on eor-xx.mit.edu machines.'
        sys.exit(1)

    quit_key=0

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
    if options.comment is not None:
        comment=options.comment
    else:
        if not (options.update):
            print 'Comment required. Describe conversion method.'
            quit_key=1
    if options.follow_up is not None:
        follow_up=options.follow_up

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
        if options.comment is not None:
            if options.follow_up is not None:
                query="UPDATE uvfits_version SET comment='%s',follow_up='%s' WHERE (version,subversion)=(%s,%s);" %(comment,follow_up,version,subversion)
            else:
                query="UPDATE uvfits_version SET comment='%s' WHERE (version,subversion)=(%s,%s);" %(comment,version,subversion)
        else:
            if options.follow_up is not None:
                query="UPDATE uvfits_version SET follow_up='%s' WHERE (version,subversion)=(%s,%s);" %(follow_up,version,subversion)
            else:
                print 'Comment or follow_up required for version update'
    else:
        if options.follow_up is not None:
            query="INSERT INTO uvfits_version VALUES (%s,%s,'%s','%s');" %(version,subversion,comment,follow_up)
        else:
            query="INSERT INTO uvfits_version (version,subversion,comment) VALUES (%s,%s,'%s');" %(version,subversion,comment)

    try:
        cur.execute(query)
    except:
        print 'Trouble updating the database.'
        cur.close()
        conn.close()
        sys.exit(1)

    conn.commit()
    cur.close()
    conn.close()
    sys.exit(0)

if __name__=="__main__":
    main()
