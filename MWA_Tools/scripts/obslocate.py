#! /usr/bin/env python
"""
A little script to find the location of a particular dataset
"""
import sys, os
from mwapy.resolve import *
from optparse import OptionParser
import psycopg2
import threading
import urllib2, urllib
import time
import curses
import mwaconfig

def resolveURI_host(resolvehost, uri):
    
    sock = None
    data = {}
    data['uri'] = uri

    url_values = urllib.urlencode(data)
    full_url = "http://" + resolvehost + "/ngas/RESOLVE/?" + url_values
    try:
        sock =  urllib2.urlopen(full_url)
        buff = None
        block_sz = 8192
        while True:
            buffer = sock.read(block_sz)
            if not buffer:
                break
        
            if (buff == None):
                buff = buffer
            else:
                buff = buff + buffer

        ele = ElementTree.XML(buff)
        res = ele.find('Result')
        if res.text == 'OK':
            urlsEle = ele.find('URL')
            
            result = urlparse(urlsEle.text)
            return result.netloc
#            rdata = {}
#            # THIS IS A TEMPORARY FIX FOR TAPE STAGING NOT NEEDED FOR PAWSEY
#            if 'cortex' in result.netloc:
#                rdata['processing'] = 'ngamsMWACortexStageDppi'
#            
#            rdata['file_id'] = parseURI(result.query)
#            
#            return "http://" + result.netloc + "/RETRIEVE?" + urllib.urlencode(rdata)
        else:
            raise NGASException(ele.find('ErrorCode').text, ele.find('ErrorDescription').text)
        
    finally:
        if sock:
            sock.close()

def main():
    conn = None
    stat = None
    stdscr = None
    
    try:
        parser = OptionParser(usage="usage: %prog [options]", version="%prog 1.0")
        parser.add_option("-r", default=mwaconfig.mandc.dbhost, action="store", dest="host_port", help="NGAS resolver host:port")
        parser.add_option("-s", default=mwaconfig.mandc.dbhost, action="store", dest="dbhost", help="MWA database host")
        parser.add_option("-p", default='5432', action="store", dest="dbport", help="MWA database port (default: 5432)")
        parser.add_option("-o", action="store", dest="obs", help="Observation ID")
        parser.add_option("-f",action="store_true",help="return error if the input obs is not available at specfied resolver")
#        parser.add_option("-d", action="store", dest="out", help="Output directory (default: ./<Observation ID>")
#        parser.add_option("-t", default='4', action="store", dest="td", help="Number of simultaneous downloads (default: 4)")
        
        (options, args) = parser.parse_args()
        
        if options.host_port == None:
            print 'host:port is empty'
            sys.exit(-1)
            
        if options.obs == None:
            print 'Observation ID is empty'
            sys.exit(-1)
            
#        if int(options.td) < 0:
#            print 'Number of simultaneous downloads must be > 0\n'
#            sys.exit(-1)
        
        print '%s' % (options.obs,),
        conn = psycopg2.connect(database=mwaconfig.mandc.dbname, user=mwaconfig.mandc.dbuser, password=mwaconfig.mandc.dbpass, host=options.dbhost, port=options.dbport)
        cur = conn.cursor()
        cur.execute('select site_path from data_files where observation_num = %s', [options.obs,])
        rows = cur.fetchall()
        
        if cur.rowcount <= 0:
            print 'No files found for observaiton %s' % (options.obs,)
            sys.exit(-1)
        
        urls = []


        for r in rows:
            #print 'Resolving URI %s' % (r[0],)
        
            try:
                url = resolveURI_host(options.host_port, r[0])
            except Exception as n:
#                print n
                urls.append("elsewhere")
                continue
            urls.append(url)
        sites = list(set(urls))
        for site in sites:
            print site.split(':')[0],urls.count(site),
        print
        if options.f:
	    assert(len(sites)==1)
    except KeyboardInterrupt as k:
        raise k
    
    except Exception as e:
        raise e
    
if __name__ == "__main__":
    try:
        main()            # Enter the main loop
        sys.exit(0)
    except KeyboardInterrupt as k:
        print 'Interrupted, shutting down'
        sys.exit(-1)
    except(AssertionError):
	print "observation is split between sites"
	sys.exit(1)
    except Exception as e:
        print e
        sys.exit(-1)
