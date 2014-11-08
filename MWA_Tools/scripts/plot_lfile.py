#!/usr/bin/env python

import logging, sys, os, glob, string, re, urllib, math, time
from optparse import OptionParser
import numpy
from mwapy import plot_lfile

# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('plot_lfile')
logger.setLevel(logging.WARNING)


######################################################################
def main():
    usage="Usage: %prog [options]\n"
    usage+='\tPlots diagnostic information from auto-correlations stored in L file\n'
    usage+='\tExample:\n\t\tpython ./plot_lfile.py -f /Volumes/RAID1/dlk/mwadata/CORRELATED_DATA/HydA_121_20110430101202/HydA_121_20110430101202_das1.LACSPC -c 192 -o test -v -l 3\n'
    parser = OptionParser(usage=usage)
    parser.add_option('-f','--filename',dest="filename",default=None,
                      help="Plot data from <FILE>",metavar="FILE")
    parser.add_option('-i','--inputs',dest="inputs",default=64,type='int',
                      help="Number of inputs in file (2*antennas usually)")
    parser.add_option('-c','--channels',dest="channels",default=768,type='int',
                      help="Number of channels in file")
    parser.add_option('-a','--antennas',dest="antennas",default=None,type='int',
                      help="Number of antennas in file (inputs/2 usually)")
    parser.add_option('-o','--output',dest="output",default=None,
                      help="Root name of output file")
    parser.add_option('-l','--level',dest="level",default='1',
                      choices=['1','2','3'],
                      help="Level of output")
    parser.add_option('-e','--ext',dest="extension",default='png',
                      help="Extension of output file")
    parser.add_option('-v','--verbose',action="store_true",dest="verbose",default=False,
                      help="Increase verbosity of output")
    

    (options, args) = parser.parse_args()

    if (options.verbose):
        logger.setLevel(logging.INFO)


    if options.filename is None:
        logger.error('Must specify L file to plot')
        sys.exit(1)

    if options.antennas is not None:
        options.inputs=2*options.antennas

    if isinstance(options.level,str):
        options.level=int(options.level)

    logger.info('# Will plot data at level %d from L file %s, %d inputs * %d channels, write output to %s*.%s' % (
        options.level,
        options.filename,
        options.inputs,
        options.channels,
        options.output,
        options.extension))
    
    data=plot_lfile.load_acdata(options.filename, options.inputs, options.channels)
    if data is None:
        logger.error('Problem loading data from L file %s' % options.filename)
        sys.exit(1)
    outputfilenames=plot_lfile.plot_acdata(data, options.output, level=options.level, format=options.extension)
    if outputfilenames is None or len(outputfilenames)==0:
        logger.error('Problem plotting data from L file %s' % options.filename)
        sys.exit(0)
    logger.info('# Wrote %s!' % ','.join(outputfilenames))
    sys.exit(0)


######################################################################
if __name__=="__main__":
    main()
