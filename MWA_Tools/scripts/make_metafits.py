#! /usr/bin/env python
"""

plock[128T]% python ~/mwa/bin/make_metafits.py -v -g 1035255392
# INFO:make_metafits: Connecting to database mwa@ngas01.ivec.org
# INFO:make_metafiles: Setting RA,Dec from phase center
# INFO:make_metafiles: Will flag tiles [71]
# INFO:make_metafiles: Found active receivers [9, 7, 10, 16]
# INFO:make_metafiles: Found fiber_velocity_factor=0.68
# INFO:make_metafiles: Found slot power information for starttime=1035255392, Rx=9: [True, True, True, True, True, True, True, True]
# INFO:make_metafiles: Found slot power information for starttime=1035255392, Rx=7: [True, True, True, True, True, True, True, True]
# INFO:make_metafiles: Found slot power information for starttime=1035255392, Rx=10: [True, True, True, True, True, True, True, True]
# INFO:make_metafiles: Found slot power information for starttime=1035255392, Rx=16: [True, True, True, True, True, True, True, True]
Card is too long, comment is truncated.
Card is too long, comment is truncated.
Card is too long, comment is truncated.
# INFO:make_metafits: Metafits written to 1035255392.metafits

"""
import sys,os,logging,shutil,datetime,re,subprocess,math,tempfile,string,glob
from optparse import OptionParser,OptionGroup
import ephem
import mwaconfig
import mwapy

from mwapy import ephem_utils, metadata
import numpy

# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('metadata')
logger.setLevel(logging.WARNING)

######################################################################
def main():

    observation_num=None

    usage="Usage: %prog [options]\n"
    usage+='\tMakes metadata FITS file\n'
    parser = OptionParser(usage=usage,version=mwapy.__version__ + ' ' + mwapy.__date__)
    parser.add_option('-f','--filename',dest="filename",
                      help="Create metafiles for <FILE>",metavar="FILE")
    parser.add_option('-d','--datetime',dest="datetimestring",
                      help="Create metafiles for <DATETIME> (YYYYMMDDhhmmss)",
                      metavar="DATETIME")
    parser.add_option('-g','--gps',dest="gpstime",
                      help="Create metafiles for <GPS>",type='int',
                      metavar="GPS")
    parser.add_option('--contiguous',dest="contiguous",
                      action="store_true",default=False,
                      help="Output separate files for contiguous channels only")    
    parser.add_option('--quick',dest='quick',default=False,
                      action='store_true',
                      help='Quick output (ignores all Rx connections)? [default=%default]')
    parser.add_option('--minbaddipoles',dest='min_bad_dipoles',default=2,type='int',
                      help='Minimum number of bad dipoles in a single pol required to flag the entire tile [default=%default]')
    parser.add_option('-m','--maxdiff',dest="maxtimediff",type='int',
                      help="Maximum time difference for search (in sec)", default=10)
    parser.add_option('--channels',dest="channels",default=24,type=int,
                      help="Number of coarse channels [default=%default, select automatically]")
    parser.add_option('--dt',dest="dt",default=0,type=float,
                      help="[sec] Integration time [default=%default, select by gpstime]")
    parser.add_option('--df',dest="df",default=0,type=int,
                      help="[kHz] Fine channel width  [default=%default, select by gpstime]")
    parser.add_option('--timeoffset',dest="timeoffset",default=0,type=int,
                      help="[sec] Time offset between filename and start of data [default=%default]")
    parser.add_option('-l','--lock',dest='lock',action='store_true',default=False,
                      help='Use \"-l\" option to create header file for locked phase center (RTS input)')
    parser.add_option('-o','--output',type=str,default=None,
                      help='Name of output FITS file [default=<gpstime>.metafits]')
    parser.add_option('-u','--url',default=metadata._BASEURL,
                      help="URL for metadata retrieval [default=%default]")
    parser.add_option('-v','--verbose',action="store_true",dest="verbose",default=False,
                      help="Increase verbosity of output")
    

    (options, args) = parser.parse_args()

    if (options.verbose):
        logger.setLevel(logging.INFO)

    observation_num=options.gpstime

    if options.output is None:
        options.output='%d.metafits' % observation_num

    if observation_num is not None:
        obs=metadata.MWA_Observation(observation_num, url=options.url)        
        if obs.observation_number is None:
            logger.error('No observation found for %s' % observation_num)
            sys.exit(1)
        if numpy.diff(obs.channels).max()>1 and options.contiguous:
            # the frequencies are not contiguous
            # determine the contiguous ranges
            df=numpy.diff(obs.channels)
            frequency_indices=numpy.where(df>1)[0]
            channel_selections=[]
            istart=0
            for istop in frequency_indices:
                channel_selections.append(numpy.arange(istart,istop+1))
                istart=istop+1
            channel_selections.append(numpy.arange(istart,len(obs.channels)))            
        else:
            channel_selections=[numpy.arange(len(obs.channels))]

        m=metadata.instrument_configuration(observation_num,
                                            min_bad_dipoles=options.min_bad_dipoles,
                                            lock=options.lock)

        for i,channel_selection in zip(range(len(channel_selections)),channel_selections):
            logger.info('Creating output for channels %s' % channel_selection)
            h=m.make_metafits(quick=options.quick)
            output=options.output
            if len(channel_selections)>1:
                output=output.replace('.metafits','.%02d.metafits' % i)
            if os.path.exists(output):
                os.remove(output)
            try:
                h.writeto(output)
                logger.info('Metafits written to %s' % (output))
            except Exception, e:
                logger.error('Unable to write metafits file %s:\n%s' % (output,e))
                sys.exit(1)
            
    sys.exit(0)
        


######################################################################

if __name__=="__main__":
    main()
