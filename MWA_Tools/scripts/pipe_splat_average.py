#! /usr/bin/env python

"""


"""


import sys,os,logging,shutil,datetime,re,subprocess,math,tempfile,string,glob
from optparse import OptionParser
import numpy
from mwapy import splat_average

# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('splat_average')
logger.setLevel(logging.WARNING)

# this works for 32T
_CHANSPERDAS=192
_NDAS=4
# 32 antennas * 2 polns
_NINP=64

######################################################################
def main():

    usage="Usage: %prog [options]\n"
    usage+="\tsplat L files and (optionally) average in time and/or frequency\n"
    usage+="\tInput is from <STDIN>\n"
    usage+="\tOutput is <STDOUT> by default, or can output to a file\n"
    usage+="\tCan only process a single input/output stream\n"
    usage+="\tExample:\n\t\tcat 1031507112.lacspc | ~/mwa/bin/pipe_splat_average.py -v -c 0 -i 64 --channels 3072 --auto --average=4 --freqaverage=4 > ! test2.lacspc\n"


    parser = OptionParser(usage=usage)
    parser.add_option('--cross',dest='cross',default=False,action='store_true',
                      help='Data are cross-correlations')
    parser.add_option('--auto',dest='auto',default=False,action='store_true',
                      help='Data are auto-correlations')

    parser.add_option('-c','--center',dest='center_channel',default=0,type=int,
                      help='Center channel of observation (if 0 no reordering is done) [default=%default]')
    parser.add_option('-a','--average','-t','--timeaverage',dest='n_avtime',default=1,type=int,
                      help='Number of time samples to average [default=%default]')
    parser.add_option('-f','--freqaverage',dest='n_avfreq',default=1,type=int,
                      help='Number of frequency samples to average [default=%default]')
    parser.add_option('-o','--output',dest='output',default=None,
                      help='Name of output')
    parser.add_option('-i','--inputs',dest='inputs',default=_NINP,type=int,
                      help='Number of input correlator streams (2*number of anteannas) [default=%default]')
    parser.add_option('--channels',dest='channels',default=_CHANSPERDAS,type=int,
                      help='Number of fine channels [default=%default]')
    parser.add_option('--coarse',dest='coarse',default=24,type=int,
                      help='Number of coarse channels [default=%default]')
    parser.add_option('--adjustgains',dest='adjustgains',default=True,action='store_true',
                      help='Adjust digital PFB gains?')
    parser.add_option('--noadjustgains',dest='adjustgains',default=True,action='store_false',
                      help='Do not adjust digital PFB gains?')

    parser.add_option('-v','--verbose',action="store_true",dest="verbose",default=False,
                      help="Increase verbosity of output")
    

    (options, args) = parser.parse_args()

    if (options.verbose):
        logger.setLevel(logging.INFO)

    if not (options.auto or options.cross):
        logger.error('Must process either auto- or cross-correlations')
        sys.exit(0)
    if  (options.auto and options.cross):
        logger.error('Cannot process both auto- and cross-correlations')
        sys.exit(0)

    if options.n_avtime>1:
        logger.info('Averaging output by factor of %d in time' % options.n_avtime)
    if options.n_avfreq>1:
        logger.info('Averaging output by factor of %d in frequency' % options.n_avfreq)

    if options.output is None or len(options.output)==0 or options.output=='-':
        options.output=None

    gains=None
    if options.center_channel > 0:
        correct_chan=splat_average.channel_order(options.center_channel)
        if options.adjustgains:
            gains=splat_average.get_gains(options.center_channel)
            logger.info('Adjusting coarse PFB gains by a factor of 1.0/%s' % (gains))
    else:
        correct_chan=numpy.arange(options.coarse)
    if (correct_chan is None):
        sys.exit(2)        

    if options.auto:
        logger.info('SPLAT and averaging AC...')
        retval=splat_average.splat_average_ac_pipe(options.output,
                                                   options.channels, options.coarse, options.inputs, 
                                                   options.n_avtime, options.n_avfreq, correct_chan, gains=gains)
        logger.info('Processed %d time samples' % retval)

    if options.cross:
        logger.info('SPLAT and averaging CC...')
        retval=splat_average.splat_average_cc_pipe(options.output,
                                                   options.channels, options.coarse, options.inputs, 
                                                   options.n_avtime, options.n_avfreq, correct_chan, gains=gains)
        logger.info('Processed %d time samples' % retval)


######################################################################

if __name__=="__main__":
    main()
