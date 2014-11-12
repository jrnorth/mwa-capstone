#! /usr/bin/env python
import logging, sys, os, glob, subprocess, string, re, urllib, math, time
from optparse import OptionParser,OptionGroup
import numpy

import ephem
from mwapy import convert_ngas, get_observation_info
from mwapy.obssched.base import schedule

# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('convert_ngas')
logger.setLevel(logging.WARNING)

# open up database connection
try:
    db = schedule.getdb()
except:
    logger.error("Unable to open connection to database")
    sys.exit(1)

_NGPUBOX=2
_GPUBOXNAME='gpubox'

######################################################################
def main():

    gpstime=None
    quack=4

    command=' '.join(sys.argv)

    usage="Usage: %prog [options] <file1> <file2> [<file3> <file4>]\n"
    usage+='\tConverts NGAS FITS files to Lfile (and possibly to UVFITS)\n'
    usage+='\tAnd/Or plots auto/cross powers\n'
    usage+='\tExample:\n\t\tpython ~/mwa/bin/convert_ngas.py -v --header="header_%gpstime%.txt" -t 4 -f 4 -uvfits=test 1031507112_20120912174453_gpubox01.rts.mwa128t.org_00.fits 1031507112_20120912174453_gpubox02_00.fits 1031507112_20120912174535_gpubox01.rts.mwa128t.org_01.fits 1031507112_20120912174535_gpubox02_01.fits\n\n'
    usage+='\tIf basic information for database lookup is not supplied should be able to run just by specifying existing meta-data files instead\n'
    usage+='\tFiles should come in pairs for 2 GPU boxes\n'
    parser = OptionParser(usage=usage)
    parser.add_option('--filename',dest="filename",default=None,
                      help="Lookup metadata for <FILE>",metavar="FILE")
    parser.add_option('--datetime',dest="datetimestring",default=None,
                      help="Lookup metadata for <DATETIME> (YYYYMMDDhhmmss)",
                      metavar="DATETIME")
    parser.add_option('--gps',dest="gpstime",default=None,
                      help="Lookup metadata for <GPS>",type='int',
                      metavar="GPS")
    parser.add_option('-m','--maxdiff',dest="maxtimediff",type='int',
                      help="Maximum time difference for search (in sec) [default=%default]", default=10)
    parser.add_option('--center',dest="center_channel",type='int',default=None,
                      help="Center coarse channel number")
    parser.add_option('--lfile',dest="lfile",type=str,default=None,
                      help="Root name for L file conversion")
    parser.add_option('--uvfits',dest="uvfits",type=str,default=None,
                      help="Root name for UVFITS conversion")

    parser.add_option('-v','--verbose',action="store_true",dest="verbose",default=False,
                      help="Increase verbosity of output")
    parser.add_option('-q','--quiet',action="store_false",dest="verbose",default=False,
                      help="Decrease verbosity of output")

    plotgroup=OptionGroup(parser,'Plotting Options',
                          "For plotting auto/cross data")
    plotgroup.add_option('--plot',dest="plot",type=str,default=None,
                      help="Root name for plotting autos and crosses")
    plotgroup.add_option('--auto',dest="auto",type=str,default=None,
                      help="Root name for plotting autos")
    plotgroup.add_option('--cross',dest="cross",type=str,default=None,
                      help="Root name for plotting crosses")

    
    lfilegroup=OptionGroup(parser,'Lfile Conversion Options',
                           "For converting to L files")

    lfilegroup.add_option('-t','--timeaverage',dest='nav_time',default=1,type=int,
                      help='Number of time samples to average [default=%default]')
    lfilegroup.add_option('-f','--freqaverage',dest='nav_freq',default=1,type=int,
                      help='Number of frequency samples to average [default=%default]')
    lfilegroup.add_option('-s','--subbands',dest='sub',default=1,type=int,
                      help='Number of subbands for output [default=%default]')
    lfilegroup.add_option('--adjustgains',dest='adjustgains',default=True,action='store_true',
                      help='Adjust digital PFB gains?')
    lfilegroup.add_option('--noadjustgains',dest='adjustgains',default=True,action='store_false',
                      help='Do not adjust digital PFB gains?')
    lfilegroup.add_option('--quack',dest='quack',default=quack,type=int,
                      help='Number of starting samples to flag (quack) [default=%default]')

    
    uvfitsgroup=OptionGroup(parser,'UVFITS Conversion Options',
                            "For converting to UVFITS")
    uvfitsgroup.add_option('--autoflag',dest='autoflag',default=True,action='store_true',
                           help='Use autoflagging in corr2uvfits? [default: %default]')
    uvfitsgroup.add_option('--noautoflag',dest='autoflag',default=True,action='store_false',
                           help='Do not use autoflagging in corr2uvfits?')
    uvfitsgroup.add_option('--header',dest='header',default='header.txt',
                           help='Specify the header file [default: %default]')
    uvfitsgroup.add_option('--instr',dest='instrument_config',default='instr_config.txt',
                           help='Specify the instrument configuration file [default: %default]')
    uvfitsgroup.add_option('--antenna',dest='antenna_locations',default='antenna_locations.txt',
                           help='Specify the antenna locations file [default: %default]')
    uvfitsgroup.add_option('--flag',dest='static_flag',default=None,
                           help='Specify a static masking file for the channels [default: %default]')    
    uvfitsgroup.add_option('--timeoffset',dest='timeoffset',default=0,type=int,
                      help='Specify time offset in seconds between the file datetime and the observation starttime [default: %default]')
    uvfitsgroup.add_option('-l','--lock',dest='lock',action='store_true',default=False,
                          help='Use \"-l\" option to corr2uvfits for locked phase center (RTS input)')
    uvfitsgroup.add_option('--clean',dest='clean',action='store_true',default=False,
                          help='Clean intermediary L files? [default: %default]')
    uvfitsgroup.add_option('--update',dest='update',action='store_true',default=True,
                          help='Updated UVFITS header? [default: %default]')
    uvfitsgroup.add_option('--noupdate',dest='update',action='store_false',default=True,
                          help='Updated UVFITS header? [default: %default]')
 

    parser.add_option_group(plotgroup)
    parser.add_option_group(lfilegroup)
    parser.add_option_group(uvfitsgroup)


    (options, args) = parser.parse_args()

    if (options.verbose):
        logger.setLevel(logging.INFO)

    x=db.dsn.split()
    dbname='%s@%s:%s:%s' % (x[1].split('=')[1],
                            x[3].split('=')[1],
                            x[0].split('=')[1],
                            x[4].split('=')[1])
    logger.info('Connecting to database %s'  % dbname)

    if len(args) % _NGPUBOX != 0:
        logger.error('Must supply number of files that is multiply of %d' % _NGPUBOX)
        sys.exit(1)

    if options.uvfits is not None and options.lfile is None:
        options.lfile=options.uvfits

    if options.plot:
        options.auto=options.plot
        options.cross=options.plot

    if options.auto is None and options.cross is None and options.lfile is None:
        logger.error('Must select conversion and/or plotting')
        sys.exit(1)

    observation_num=None
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

    if observation_num is None:
        # try to get the info from the ngas file name
        for arg in args:
            name_parts=convert_ngas.parseNGASfile(arg)
            try:
                observation_num=get_observation_info.find_closest_observation(int(name_parts[0]),
                                                                              maxdiff=options.maxtimediff,db=db)
            except:
                observation_num=None
            if observation_num is None:
                logger.error('No matching observation found for gpstime=%d\n' % (int(name_parts[0])))


            try:
                observation_num=get_observation_info.find_observation_num(name_parts[1],
                                                                          maxdiff=options.maxtimediff, db=db)
            except:
                observation_num=None
            if observation_num is None:
                logger.error('No matching observation found for datetimestring=%s\n' % (name_parts[1]))
            if observation_num is not None:
                break


    # convert arguments into a list of lists
    filenames=[]
    for i in xrange(0,len(args),_NGPUBOX):
        x=[]
        for j in xrange(_NGPUBOX):
            for k in xrange(len(args)):
                name_parts=convert_ngas.parseNGASfile(args[k])
                if not isinstance(name_parts[-1],int):
                    if ('%s%02d' %  (_GPUBOXNAME,j+1)) in name_parts[2] and ('%02d' % (i/_NGPUBOX)) in name_parts[-1]:
                        x.append(args[k])
                        logger.info('Identified file %s as from host %s%02d and time part %02d' % (args[k],_GPUBOXNAME,j+1,i/_NGPUBOX))
                else:
                    # there is only one time part
                    if ('%s%02d' %  (_GPUBOXNAME,j+1)) in name_parts[2]:
                        x.append(args[k])
                        logger.info('Identified file %s as from host %s%02d and time part %02d' % (args[k],_GPUBOXNAME,j+1,i/_NGPUBOX))
                        
                    
        if (len(x) < _NGPUBOX):
            logger.warning('Could only identify %d files for time part %02d when wanted %d' % (len(x),
                                                                                               i/_NGPUBOX,
                                                                                               _NGPUBOX))
        filenames.append(x)
        
    C=convert_ngas.NGAS_Correlator(gpstime=observation_num, filenames=filenames,
                                   center_channel=options.center_channel,
                                   flag=options.autoflag, flagfile=options.static_flag, lock=options.lock,
                                   headername=options.header, antennaname=options.antenna_locations,
                                   instrname=options.instrument_config,timeoffset=options.timeoffset,
                                   adjust_gains=options.adjustgains,
                                   command=command,
                                   db=db)
    if C is not None and str(C) != 'None':
        print C
    if options.auto is not None:
        C.plot_autos(options.auto)
    if options.cross is not None:
        C.plot_crosses(options.cross)

    if options.lfile is not None:
        lfile_root=options.lfile
        try:
            outname_ac,outname_cc=C.make_lfile(lfile_root,
                                               nav_time=options.nav_time,
                                               nav_freq=options.nav_freq,
                                               subbands=options.sub,
                                               quack=options.quack)            
        except:
            logger.error('Error converting to L files')
            sys.exit(1)
        if outname_ac is None or outname_cc is None:
            logger.error('Error converting to L files')
            sys.exit(1)
        if isinstance(outname_ac,str):
            logger.info('Wrote %s and %s' % (outname_ac,outname_cc))
        else:
            for ac,cc in zip(outname_ac,outname_cc):
                logger.info('Wrote %s and %s' % (ac,cc))
    else:
        if options.nav_time > 1 or options.nav_freq > 1:
            logger.warning('Time and/or frequency averaging has been set, but conversion has not been requested')

    if options.uvfits is not None:
        if options.sub > 1:
            logger.error('Cannot create UVFITS files for > 1 subband')
            sys.exit(1)
        uvfitsname=C.make_uvfits(options.uvfits,update=options.update)
        if uvfitsname is None  or not os.path.exists(uvfitsname):
            logger.error('Error writing UVFITS file')
            sys.exit(1)

        if options.clean:
            if isinstance(outname_ac,str):
                os.remove(outname_ac)
            else:
                for ac in outname_ac:
                    os.remove(ac)
                
            if isinstance(outname_cc,str):
                os.remove(outname_cc)
            else:
                for cc in outname_cc:
                    os.remove(cc)
                

######################################################################
if __name__=="__main__":
    main()

