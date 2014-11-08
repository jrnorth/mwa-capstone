#!/usr/bin/env python
"""
Usage: add_flags.py [options] <metafits files>
	Adds or removes flags on specified tiles/receivers to metafits file(s)
	Tile/Rx list should be comma separated
	Example:
		add_flags.py -v -r 10,11 1061645040.metafits
	will flag receivers 10 and 11
"""

import os,numpy,sys
import datetime
from optparse import OptionParser
try:
    import astropy.io.fits as pyfits
except ImportError:
    import pyfits
import mwapy

######################################################################

def main():
    usage="Usage: %prog [options] <metafits files>\n"
    usage+="\tAdds or removes flags on specified tiles/receivers to metafits file(s)\n"
    usage+="\tTile/Rx list should be comma separated\n"
    usage+="\tExample:\n\t\tadd_flags.py -v -r 10,11 1061645040.metafits\n"
    usage+="\twill flag receivers 10 and 11\n"
    parser = OptionParser(usage=usage,version=mwapy.__version__)
    parser.add_option('-t','--tile',dest='tiles',default='',
                      help='List of tile(s) to flag')
    parser.add_option('-r','--receiver',dest='receivers',default='',
                      help='List of receiver(s) to flag')

    parser.add_option('-f','--flag',dest='flag',default=True,
                      action="store_true",
                      help='Flag the specified tiles/receivers?')
    parser.add_option('-u','--unflag',dest='flag',default=True,
                      action="store_false",
                      help='UnFlag the specified tiles/receivers?')
    parser.add_option('-v','--verbose',action="store_true",
                      dest="verbose",default=False,
                      help="Increase verbosity of output")
    (options, args) = parser.parse_args()

    metafitsfiles=args
    tiles=[]
    receivers=[]
    if len(options.tiles)>0:
        try:
            tiles=map(int,options.tiles.split(','))
        except ValueError:
            tiles=[]
    if len(options.receivers)>0:
        try:
            receivers=map(int,options.receivers.split(','))
        except ValueError:
            receivers=[]
    now=datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    for metafitsfile in metafitsfiles:
        if not os.path.exists(metafitsfile):
            print 'Could not open %s' % metafitsfile
            sys.exit(1)
        f=pyfits.open(metafitsfile,mode='update')
        for tile in tiles:
            if tile is None:
                continue
            if options.flag:
                f[1].data['Flag'][f[1].data['Tile']==tile]=1
                if options.verbose:
                    print 'Flagging tile %03d' % tile
                f[1].header.add_history('%s: flagged tile %03d' % (now,tile))
            else:
                f[1].data['Flag'][f[1].data['Tile']==tile]=0
                if options.verbose:
                    print 'UnFlagging tile %03d' % tile
                f[1].header.add_history('%s: unflagged tile %03d' % (now,tile))
        for receiver in receivers:
            if receiver is None:
                continue
            if options.flag:
                f[1].data['Flag'][f[1].data['Rx']==receiver]=1
                if options.verbose:
                    print 'Flagging Rx %02d' % receiver
                f[1].header.add_history('%s: flagged Rx %02d' % (now,receiver))
            else:
                f[1].data['Flag'][f[1].data['Rx']==receiver]=0
                if options.verbose:
                    print 'UnFlagging Rx %02d' % receiver
                f[1].header.add_history('%s: unflagged Rx %02d' % (now,receiver))
        f.flush()

######################################################################

if __name__=="__main__":
    main()
