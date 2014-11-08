#! /usr/bin/env python

"""
splat DAS inputs and (optionally) average in time

python ~/mwa/MWA_Tools/splat_average.py -r P00-drift_121_20110927130001 -o test -c 121 -v -a 8
# INFO:splat_average: Channel order: 109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128,132,131,130,129
# INFO:splat_average: AC size for DAS 1: 14548992 bytes
# INFO:splat_average: CC size for DAS 1: 916586496 bytes
# INFO:splat_average: Num integrations in AC for DAS 1: 296
# INFO:splat_average: Num integrations in CC for DAS 1: 296
# INFO:splat_average: AC size for DAS 2: 14548992 bytes
# INFO:splat_average: CC size for DAS 2: 916586496 bytes
# INFO:splat_average: Num integrations in AC for DAS 2: 296
# INFO:splat_average: Num integrations in CC for DAS 2: 296
# INFO:splat_average: AC size for DAS 3: 14548992 bytes
# INFO:splat_average: CC size for DAS 3: 916586496 bytes
# INFO:splat_average: Num integrations in AC for DAS 3: 296
# INFO:splat_average: Num integrations in CC for DAS 3: 296
# INFO:splat_average: AC size for DAS 4: 14548992 bytes
# INFO:splat_average: CC size for DAS 4: 916586496 bytes
# INFO:splat_average: Num integrations in AC for DAS 4: 296
# INFO:splat_average: Num integrations in CC for DAS 4: 296
# INFO:splat_average: Averaging output by factor of 8
# INFO:splat_average: SPLAT and averaging AC...
# INFO:splat_average: Opened AC file for DAS 1: P00-drift_121_20110927130001_das1.LACSPC
# INFO:splat_average: Opened AC file for DAS 2: P00-drift_121_20110927130001_das2.LACSPC
# INFO:splat_average: Opened AC file for DAS 3: P00-drift_121_20110927130001_das3.LACSPC
# INFO:splat_average: Opened AC file for DAS 4: P00-drift_121_20110927130001_das4.LACSPC
# INFO:splat_average: Writing AC output to test.av.lacspc
# INFO:splat_average: SPLAT and averaging CC...
# INFO:splat_average: Opened CC file for DAS 1: P00-drift_121_20110927130001_das1.LCCSPC
# INFO:splat_average: Opened CC file for DAS 2: P00-drift_121_20110927130001_das2.LCCSPC
# INFO:splat_average: Opened CC file for DAS 3: P00-drift_121_20110927130001_das3.LCCSPC
# INFO:splat_average: Opened CC file for DAS 4: P00-drift_121_20110927130001_das4.LCCSPC
# INFO:splat_average: Writing CC output to test.av.lccspc


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
    usage+="\tsplat DAS inputs and (optionally) average in time and/or frequency\n"
    usage+="\tpython ~/mwa/MWA_Tools/splat_average.py --das=1 -r P00-drift_121_20110927130001 -o test -c 121 -v -a 8\n"
    usage+="\tIf number of DASs is > 1, will look for files like:\n\t\t<root>_das?.LACSPC or <root>_das?.lacspc\n"
    usage+="\tOtherwise looks for:\n\t\t<root>.LACSPC or <root>.lacspc\n"


    parser = OptionParser(usage=usage)
    parser.add_option('-c','--center',dest='center_channel',default=100,type=int,
                      help='Center channel of observation (if 0 no reordering is done)')
    parser.add_option('-a','--average','-t','--timeaverage',dest='n_avtime',default=1,type=int,
                      help='Number of time samples to average [default=%default]')
    parser.add_option('-f','--freqaverage',dest='n_avfreq',default=1,type=int,
                      help='Number of frequency samples to average [default=%default]')
    parser.add_option('-o','--output',dest='outroot',default='',
                      help='Root name of output [default=input root]')
    parser.add_option('-r','--root',dest='root',default='',
                      help='Root name of input')
    parser.add_option('-i','--inputs',dest='inputs',default=_NINP,type=int,
                      help='Number of input correlator streams (2*number of anteannas) [default=%default]')
    parser.add_option('-d','--das',dest='das',default=_NDAS,type=int,
                      help='Number of DASs [default=%default]')
    parser.add_option('--chansperdas',dest='chansperdas',default=_CHANSPERDAS,type=int,
                      help='Number of fine channels in each DASs [default=%default]')
    parser.add_option('-s','--subbands',dest='sub',default=1,type=int,
                      help='Number of subbands for output [default=%default]')
    parser.add_option('--adjustgains',dest='adjustgains',default=True,action='store_true',
                      help='Adjust digital PFB gains?')
    parser.add_option('--noadjustgains',dest='adjustgains',default=True,action='store_false',
                      help='Do not adjust digital PFB gains?')

    parser.add_option('-v','--verbose',action="store_true",dest="verbose",default=False,
                      help="Increase verbosity of output")
    parser.add_option('--debug',action="store_true",dest="debug",default=False,
                      help="Increase verbosity of output further")
    

    (options, args) = parser.parse_args()

    if (options.verbose):
        logger.setLevel(logging.INFO)
    if (options.debug):
        logger.setLevel(logging.DEBUG)
    if len(options.root)==0:
        logger.error('Must specify input root')
        sys.exit(1)
    if len(options.outroot)==0:
        options.outroot=options.root

    gains=None
    if options.center_channel > 0:
        correct_chan=splat_average.channel_order(options.center_channel)
        if options.adjustgains:
            gains=splat_average.get_gains(options.center_channel)
            logger.info('Adjusting coarse PFB gains by a factor of 1.0/%s' % (gains))
    else:
        correct_chan=numpy.arange(24)
    if (correct_chan is None):
        sys.exit(2)
    try:
        fnames_ac,fnames_cc,n_times=splat_average.get_filenames_integrations(options.root,
                                                                             options.das,
                                                                             options.chansperdas, options.inputs)
    except:
        sys.exit(2)

    if options.sub==1:
        if (options.n_avtime>1 or options.n_avfreq>1):
            outname_ac=options.outroot + '.av.lacspc'
            outname_cc=options.outroot + '.av.lccspc'
            if options.n_avtime>1:
                logger.info('Averaging output by factor of %d in time' % options.n_avtime)
            if options.n_avfreq>1:
                logger.info('Averaging output by factor of %d in frequency' % options.n_avfreq)
        else:
            outname_ac=options.outroot + '.lacspc'
            outname_cc=options.outroot + '.lccspc'
    else:
        logger.info('Will write %d separate sub-bands' % options.sub)
        outname_ac=[]
        outname_cc=[]
        for i in xrange(options.sub):
            if (options.n_avtime>1 or options.n_avfreq>1):
                outname_ac.append(options.outroot + '_band%02d.av.lacspc' % (i+1))
                outname_cc.append(options.outroot + '_band%02d.av.lccspc' % (i+1))
                if options.n_avtime>1:
                    logger.info('Averaging output by factor of %d in time' % options.n_avtime)
                if options.n_avfreq>1:
                    logger.info('Averaging output by factor of %d in frequency' % options.n_avfreq)
            else:
                outname_ac.append(options.outroot + '_band%02d.lacspc' % (i+1))
                outname_cc.append(options.outroot + '_band%02d.lccspc' % (i+1))
            
        
    logger.info('SPLAT and averaging AC...')
    retval=splat_average.splat_average_ac(fnames_ac, outname_ac, n_times, 
                                          options.das*options.chansperdas, options.inputs, 
                                          options.n_avtime, options.n_avfreq, correct_chan, gains=gains)
    if retval is None:
        logger.error('Error writing AC file')
        sys.exit(2)

    
    logger.info('SPLAT and averaging CC...')
    retval=splat_average.splat_average_cc(fnames_cc, outname_cc, n_times, 
                                          options.das*options.chansperdas, options.inputs, 
                                          options.n_avtime, options.n_avfreq, correct_chan, gains=gains)

    if retval is None:
        logger.error('Error writing CC file')
        sys.exit(2)
######################################################################

if __name__=="__main__":
    main()
