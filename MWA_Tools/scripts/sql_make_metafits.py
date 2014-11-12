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

from mwapy import ephem_utils

# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('make_metafits')
logger.setLevel(logging.WARNING)

try:
    from mwapy.obssched.base import schedule
except:
    logger.error("Unable to open connection to database")
    sys.exit(1)
    
from mwapy import get_observation_info, make_metafiles
import numpy

# open up database connection
try:
    db = schedule.getdb()
except:
    logger.error("Unable to open connection to database")
    sys.exit(1)

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
    parser.add_option('-o','--output',type=str,default=None,
                      help='Name of output FITS file [default=<gpstime>.metafits]')
    parser.add_option('-v','--verbose',action="store_true",dest="verbose",default=False,
                      help="Increase verbosity of output")
    #parser.add_option('-l','--lock',dest='lock',action='store_true',default=False,
    #                      help='Use \"-l\" option to create header file for locked phase center (RTS input)')
    

    (options, args) = parser.parse_args()

    if (options.verbose):
        logger.setLevel(logging.INFO)

    logger.info('Connecting to database %s@%s' % (mwaconfig.mandc.dbuser,mwaconfig.mandc.dbhost))

    if options.filename is not None:
        observation_num=get_observation_info.find_observation_num(options.filename,
                                                                  maxdiff=options.maxtimediff, db=db)
        if observation_num is None:
            logger.error('No matching observation found for filename=%s\n' % (options.filename))
            sys.exit(1)
    elif options.datetimestring is not None:
        observation_num=get_observation_info.find_observation_num(options.datetimestring,
                                                                  maxdiff=options.maxtimediff, db=db)
        if observation_num is None:
            logger.error('No matching observation found for datetimestring=%s\n' % (options.datetimestring))
            sys.exit(1)

    elif options.gpstime is not None:
        observation_num=get_observation_info.find_closest_observation((options.gpstime),
                                                                      maxdiff=options.maxtimediff,db=db)
        if observation_num is None:
            logger.error('No matching observation found for gpstime=%d\n' % (options.gpstime))
            sys.exit(1)

    else:
        logger.error('Must specify one of filename, datetime, or gpstime')
        sys.exit(1)


    if options.output is None:
        options.output='%d.metafits' % observation_num

    if observation_num is not None:
        obs=get_observation_info.MWA_Observation(observation_number=observation_num, db=db)        
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
        # do this first so that the instrument_configuration can know the duration
        hh=make_metafiles.Corr2UVFITSHeader(observation_num, coarse_channels=options.channels,
                                            timeoffset=options.timeoffset,
                                            inttime=options.dt,
                                            fine_channel=options.df,
                                            #lock=options.lock,
                                            db=db)


        T=make_metafiles.instrument_configuration(gpstime=observation_num, duration=hh.obs.duration,
                                                  min_bad_dipoles=options.min_bad_dipoles,
                                                  db=db)
        result=T.make_instr_config(quick=options.quick)
        if result is None:
            logger.error('Error making instr_config file')
            sys.exit(1)

        for i,channel_selection in zip(range(len(channel_selections)),channel_selections):
            logger.info('Creating output for channels %s' % channel_selection)
            T.channel_selection=channel_selection
            hh.channel_selection=channel_selection
        
            hh.make_header()
            T.corr2uvfitsheader=hh

            h=T.make_metafits(quick=options.quick)
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
