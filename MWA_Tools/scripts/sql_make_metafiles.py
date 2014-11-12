#! /usr/bin/env python
"""
margle[~/mwa]% python software/bin/make_metafiles.py -v -g 1028714112 --channels=12
# INFO:make_metafiles: Will flag tiles []
# INFO:make_metafiles: Found active receivers [2]
# INFO:make_metafiles: Creating fake tile 501
# INFO:make_metafiles: Creating fake tile 502
# INFO:make_metafiles: Creating fake tile 503
# INFO:make_metafiles: Creating fake tile 504
# INFO:make_metafiles: Creating fake tile 505
# INFO:make_metafiles: Creating fake tile 506
# INFO:make_metafiles: Creating fake tile 507
# INFO:make_metafiles: Creating fake tile 508
# INFO:make_metafiles: Creating fake tile 517
# INFO:make_metafiles: Creating fake tile 518
# INFO:make_metafiles: Creating fake tile 519
# INFO:make_metafiles: Creating fake tile 520
# INFO:make_metafiles: Creating fake tile 521
# INFO:make_metafiles: Creating fake tile 522
# INFO:make_metafiles: Creating fake tile 523
# INFO:make_metafiles: Creating fake tile 524
# INFO:make_metafiles: Creating fake tile 525
# INFO:make_metafiles: Creating fake tile 526
# INFO:make_metafiles: Creating fake tile 527
# INFO:make_metafiles: Creating fake tile 528
# INFO:make_metafiles: Creating fake tile 529
# INFO:make_metafiles: Creating fake tile 530
# INFO:make_metafiles: Creating fake tile 531
# INFO:make_metafiles: Creating fake tile 532
# INFO:make_metafiles: Wrote instr_config file instr_config.txt!
# INFO:make_metafiles: Wrote antenna_locations file antenna_locations.txt!
# INFO:make_metafiles: Setting RA,Dec from phase center
# INFO:make_metafiles: Wrote header file header.txt!

"""
import sys,os,logging,shutil,datetime,re,subprocess,math,tempfile,string,glob
from optparse import OptionParser,OptionGroup
from datetime import datetime
import ephem
import mwaconfig

from mwapy import ephem_utils

# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('make_metafiles')
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
    usage+='\tMakes metadata files necessary for corr2uvfits\n'
    usage+='\t128T sampling windows:\n'
    for i in xrange(len(make_metafiles._START)):
        t1=ephem_utils.MWATime(gpstime=make_metafiles._START[i])
        if i<len(make_metafiles._START)-1:
            t2=ephem_utils.MWATime(gpstime=make_metafiles._START[i+1]-1)
        else:
            t2=ephem_utils.MWATime(gpstime=9046304456)
        usage+='\t%s (%10d) - %s (%10d): %.1f s, %d kHz\n' % (t1.datetime.strftime('%y-%m-%dT%H:%M:%S'),
                                                          t1.gpstime,
                                                          t2.datetime.strftime('%y-%m-%dT%H:%M:%S'),
                                                          t2.gpstime,
                                                          make_metafiles._DT[i],
                                                          make_metafiles._DF[i])
    parser = OptionParser(usage=usage)
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
    parser.add_option('--minbaddipoles',dest='min_bad_dipoles',default=2,type='int',
                      help='Minimum number of bad dipoles in a single pol required to flag the entire tile [default=%default]')
    parser.add_option('-m','--maxdiff',dest="maxtimediff",type='int',
                      help="Maximum time difference for search (in sec)", default=10)
    parser.add_option('--channels',dest="channels",default=24,type=int,
                      help="Number of coarse channels [default=%default]")
    parser.add_option('--channel',dest="channel",default=None,type=int,
                      help="Coarse channel (implies channels=1) [default=%default]")
    parser.add_option('--dt',dest="dt",default=0,type=float,
                      help="[sec] Integration time [default=%default, select by gpstime]")
    parser.add_option('--df',dest="df",default=0,type=int,
                      help="[kHz] Fine channel width  [default=%default, select by gpstime]")
    parser.add_option('--timeoffset',dest="timeoffset",default=0,type=int,
                      help="[sec] Time offset between filename and start of data [default=%default]")
    parser.add_option('--header',dest='header',default='header_%gpstime%_%channel%.txt',
                      help="Name of header output file [default=%default]")
    parser.add_option('--antenna',dest='antenna',default='antenna_locations_%gpstime%_%channel%.txt',
                      help="Name of antenna_locations output file [default=%default]")
    parser.add_option('--instr',dest='instr',default='instr_config_%gpstime%_%channel%.txt',
                      help="Name of instr_config output file [default=%default]")
    parser.add_option('--rts',dest='rts',default=False,action="store_true",
                      help="Write RTS files (array file and rts_in)?")
    parser.add_option('--array',dest='array',default='array_file.txt',
                      help="Name of RTS array file  output file [default=%default]")
    parser.add_option('-v','--verbose',action="store_true",dest="verbose",default=False,
                      help="Increase verbosity of output")
    parser.add_option('--debug',action="store_true",dest="debug",default=False,
                      help="Display all database commands")
    parser.add_option('-l','--lock',dest='lock',action='store_true',default=False,
                          help='Use \"-l\" option to create header file for locked phase center (RTS input)')
    

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


    if options.channel is not None:
        options.channels=1
    if observation_num is not None:
        obs=get_observation_info.MWA_Observation(observation_number=observation_num, db=db)        
        # do this first so that the instrument_configuration can know the duration
        h=make_metafiles.Corr2UVFITSHeader(observation_num, coarse_channels=options.channels,
                                           coarse_channel=options.channel,
                                           timeoffset=options.timeoffset,
                                           inttime=options.dt,
                                           fine_channel=options.df,
                                           lock=options.lock,
                                           db=db)
        vars={'gpstime': observation_num,
              'channel': make_metafiles.ternary(options.channel is None,'all',options.channel)}

        if '%' in options.header:
            options.header=make_metafiles.update_filename(options.header,vars)
        if '%' in options.instr:
            options.instr=make_metafiles.update_filename(options.instr,vars)
        if '%' in options.antenna:
            options.antenna=make_metafiles.update_filename(options.antenna,vars)
            
        T=make_metafiles.instrument_configuration(gpstime=observation_num, duration=h.obs.duration, db=db,
                                                  min_bad_dipoles=options.min_bad_dipoles,
                                                  debug=options.debug)
        result=T.make_instr_config()
        if result is None:
            logger.error('Error making instr_config file')
            sys.exit(1)
        try:
            f=open(options.instr,'w')
        except:
            logger.error('Could not open instr_config file %s for writing' % options.instr)
            sys.exit(1)
            
        f.write(str(T))
        f.close()
        logger.info('Wrote instr_config file %s!' % (options.instr))

        try:
            f=open(options.antenna,'w')
        except:
            logger.error('Could not open antenna_locations file %s for writing' % options.antenna)
            sys.exit(1)
        f.write(T.antenna_locations())
        f.close()
        logger.info('Wrote antenna_locations file %s!' % (options.antenna))

        if options.rts:
            try:
                f=open(options.array,'w')
            except:
                logger.error('Could not open RTS array_file  file %s for writing' % options.array)
                sys.exit(1)
            f.write(T.array_file())
            f.close()
            logger.info('Wrote array file %s!' % (options.array))

            try:
                f=open("rts.in",'w')
            except:
                logger.error('Could not open RTS configuration file rts.in for writing' )
                sys.exit(1)
            try:
                f.write(T.rts_in(rtstime=datetime.strptime(options.datetimestring,"%Y%m%d%H%M%S")))
                f.close()
                logger.info('Wrote rts_in file !')
            except:
                logger.error('Unable to write rts_in file')


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


        for i,channel_selection in zip(range(len(channel_selections)),channel_selections):
            header_name=options.header
            logger.info('Creating output for channels %s' % channel_selection)
            h.channel_selection=channel_selection

            h.make_header()
            if len(channel_selections)>1:
                header_name=header_name.replace('.txt','.%02d.txt' % i)
            try:
                f=open(header_name,'w')
            except:
                logger.error('Could not open header file %s for writing' % header_name)
                sys.exit(1)
            f.write(str(h))
            f.close()
            logger.info('Wrote header file %s!' % (header_name))
        


######################################################################

if __name__=="__main__":
    main()
