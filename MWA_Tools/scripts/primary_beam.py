#!/bin/env python
"""
Write a primary beam fits file.

Author: D. Kaplan

Interfaces to primary_beam.write_primary_beam in MWA_Tools
"""
from mwapy import ephem_utils
try:
    from mwapy.obssched.base import schedule
except:
    pass
import sys,bisect
try:
    from receiverStatusPy import ReceiverStatusParser,StatusTools
    use_statustools=True
except:
    use_statustools=False
import pyfits,numpy,math
import os
import getopt
from primary_beam import *


######################################################################
def main():

    freq=100.0
    useazza=False
    xpol=True
    ypol=True
    HA=None
    Dec=None
    try:
        opts, args = getopt.getopt(sys.argv[1:], 
                                   "hf:c:a:xy",
                                   ["help",
                                    "chan=",
                                    "freq=",
                                    "az=",
                                    "HA=",
                                    "Dec="])
    except getopt.GetoptError,err:
        logger.error('Unable to parse command-line options: %s\n',err)
        usage()
        sys.exit(2)        

    for opt,val in opts:
        # Usage info only
        if opt in ("-h", "--help"):
            usage()
            sys.exit(1)
        elif opt in ("-c","--chan"):
            chan=int(val)
            freq=chan*1.28
        elif opt in ("-f","--freq"):
            freq=float(val)
        elif opt in ("-a","--az"):
            useazza=int(val)
        elif (opt in ("-x")):
            ypol=False
        elif (opt in ("-y")):
            xpol=False
        elif (opt in ("--HA")):
            HA=float(val)
        elif (opt in ("--Dec")):
            Dec=float(val)
        
    if (len(args)>0):
        for datetime in args:
            write_primary_beam(datetime=datetime, freq=freq*1e6, useazza=useazza, xpol=xpol, ypol=ypol,HA=HA,Dec=Dec)
    else:
            write_primary_beam(freq=freq*1e6, useazza=useazza, xpol=xpol, ypol=ypol,HA=HA,Dec=Dec)



if __name__ == "__main__":
    main()
