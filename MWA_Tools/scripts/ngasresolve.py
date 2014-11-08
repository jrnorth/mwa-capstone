#!/usr/bin/env python

import sys
from resolve import *
from optparse import OptionParser

def main():
    
    try:
        parser = OptionParser(usage="usage: %prog [options]", version="%prog 1.0")
        parser.add_option("-r", action="store", dest="host_port", help="NGAS resolver host:port")
        parser.add_option("-u", action="store", dest="uri", help="NGAS URI")
        parser.add_option("-o", action="store", dest="out", help="Output directory")
        
        (options, args) = parser.parse_args()
        
        if options.host_port == None:
            print 'host:port is empty'
            sys.exit(-1)
            
        if options.uri == None:
            print 'URI is empty'
            sys.exit(-1)
        
        print 'Resolving URI %s' % (options.uri,)
        
        url = resolveURI(options.host_port, options.uri)
        
        print 'Resolved to %s' % (url,)
        
        downloadURL(url, options.out)

    except (KeyboardInterrupt):
        sys.exit(-1)
    
    except Exception, e:
        print e
        sys.exit(-1)
            
    sys.exit(0)

if __name__ == "__main__":
    main()
    
