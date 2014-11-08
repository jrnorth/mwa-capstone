#!/usr/local/bin/python

import psycopg2
import sys
from optparse import OptionParser
import urllib2
import json
import numpy as np
import mwapy
import os.path

def main():
    usage="Usage: %prog [options]\n"
    usage+="\t Does stuff"

    parser = OptionParser(usage=usage)
    parser.add_option('-o','--obsid',dest="obsid",
                      help="Observation ID")
    parser.add_option('-p','--preferred',action="store_true",dest="preferred",default=False,
                      help="Set to only return preferred host")
    parser.add_option('-n','--return_n',action="store_true",dest="return_n",default=False,
                      help="Return only the number of files. Supercedes preferred")
    parser.add_option('-a','--return_all',action="store_true",dest="return_all",default=False,
                      help="Return all files (including flag files)")
    parser.add_option('-f','--return_flag',action="store_true",dest="return_flag",default=False,
                      help="Return only flag files (usually just one or zero)")

    (options,args) = parser.parse_args()
    obsid=options.obsid

    # get file location data
    if options.return_all:
        url='http://eor-01.mit.edu:7777/QUERY?query=files_location&like='+obsid+'%&format=json'
    elif options.return_flag:
        url='http://eor-01.mit.edu:7777/QUERY?query=files_location&like='+obsid+'%flags.zip&format=json'
    else:
        url='http://eor-01.mit.edu:7777/QUERY?query=files_location&like='+obsid+'%.fits&format=json'
    response = urllib2.urlopen(url)
    contents=response.read()
    table=json.loads(contents)['files_location']

    # do some parsing
    host_col='col1'
    path_col='col2'
    nfiles=len(table)

    # read in table for path look-up and exchange
    lookup_file = os.path.dirname(os.path.dirname(mwapy.__file__))+'/configs/MIT_path_table.txt'
    lookup_table=np.loadtxt(lookup_file,dtype='str')

    paths=[]
    hosts=[]
    basenames=[]
    host_len=6 # length of hostname we need. eor-xx

    for col in table:
        host=col[host_col]
        host=host[0:host_len]
        path=col[path_col]
        volumen=path[16:23]
        
        row=np.where((lookup_table[:,0]==host) & (lookup_table[:,1]==volumen))
        row=row[0][0]
        linked_dir=lookup_table[row,2]

        path=linked_dir+path[23:]
        # Check for duplicates
        basename=os.path.basename(path)
        if basename in basenames:
            ind=basenames.index(basename)
            path2=paths[ind]
            if os.path.getctime('/nfs'+path) > os.path.getctime('/nfs'+path2):
                # current path is newer, replace older
                paths[ind]=path
                hosts[ind]=host
            continue # if current path was older, we're skipping it
        
        hosts.append(host)
        paths.append(path)
        basenames.append(basename)

    if (options.return_n):
        print len(paths)
        return
    if (options.preferred):
        print max(set(hosts),key=hosts.count)
        return
    for path in paths:
        print path

if __name__=="__main__":
    main()
