#!/usr/bin/env python

"""
match_observation.py

matches observations , given frequency and/or delays

example:

margle[~/mwa]% python software/bin/match_observation.py -g 1028717896 --freq
# Starttime  Timediff Filename                  Cal? MJD   Date       Time     Channels                                                                                        Delays
1028717896          0 PKS1932-46_117      	F    56150 2012/08/11 10:58:00 105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128 0,5,10,15,4,9,14,19,8,13,18,23,12,17,22,27
1028718432        536 VirA_117            	F    56150 2012/08/11 11:06:56 105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128 30,23,16,9,27,20,13,6,24,17,10,3,21,14,7,0
1028717352        544 PKS1814-63_117      	F    56150 2012/08/11 10:48:55 105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128 0,2,4,6,5,7,9,11,10,12,14,16,15,17,19,21
...

"""
import logging, sys, os, glob, string, re, urllib, math, time
from optparse import OptionParser
import numpy
#import pgdb

import mwaconfig

import ephem
from mwapy import dbobj, ephem_utils
from mwapy import get_observation_info
from mwapy.obssched.base import schedule
from mwapy.match_observation import *

# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('match_observation')
logger.setLevel(logging.WARNING)

# open up database connection
try:
    db = schedule.getdb()
except:
    logger.error("Unable to open connection to database")
    sys.exit(1)


######################################################################
def main():
    observation_number=None

    usage="Usage: %prog [options]\n"
    usage+='\tMatches specified observation based on frequency and/or delays; can also restrict to calibration observations\n'
    usage+="\tInitial observation  based on a filename, a UT datetime string, or a GPS time\n"
    usage+="\tRequires connection to MandC database through local configuration file\n"
    parser = OptionParser(usage=usage)
    parser.add_option('-f','--filename',dest="filename",
                      help="Search for information on <FILE>",metavar="FILE")
    parser.add_option('-d','--datetime',dest="datetimestring",
                      help="Search for information on <DATETIME> (YYYYMMDDhhmmss)",
                      metavar="DATETIME")
    parser.add_option('-g','--gps',dest="gpstime",
                      help="Search for information on <GPS>",type='int',
                      metavar="GPS")
    parser.add_option('-m','--maxdiff',dest="maxtimediff",type='int',
                      help="Maximum time difference for search (in sec)", default=10)
    parser.add_option('-v','--verbose',action="store_true",dest="verbose",default=False,
                      help="Increase verbosity of output")
    parser.add_option('--delay',action='store_true',dest='delay',default=False,
                      help='Match delays?')
    parser.add_option('--freq',action='store_true',dest='freq',default=False,
                      help='Match frequencies?')
    parser.add_option('--cal',action='store_true',dest='cal',default=False,
                      help='Require calibration observations?')
    parser.add_option('-n','--nmax',dest='nmax',default=None,type='int',
                      help='Maximum number of records to display [default=%default]')
    parser.add_option('--dtmax',dest='dtmax',default=None,type='int',
                      help='Maximum time offset to search in seconds [default=%default]')
    parser.add_option('--min',action='store_true',
                    help='Only return the obsid of the best cal match (useful for scripting).')
    
    

    (options, args) = parser.parse_args()
    if len(args)<1:
        search_subset = None
    else:
        search_subset = args

    if (options.verbose):
        logger.setLevel(logging.DEBUG)

    logger.info('Connecting to database %s@%s' % (mwaconfig.mandc.dbuser,mwaconfig.mandc.dbhost))

    if not (options.delay or options.freq or options.min):
        logger.error('Must match either delays and/or frequencies')
        sys.exit(1)

    if options.filename is not None:
        observation_number=get_observation_info.find_observation_num(options.filename, maxdiff=options.maxtimediff, db=db)
        if observation_number is None:
            logger.error('No matching observation found for filename=%s\n' % (options.filename))
            sys.exit(1)
    elif options.datetimestring is not None:
        observation_number=get_observation_info.find_observation_num(options.datetimestring, maxdiff=options.maxtimediff, db=db)
        if observation_number is None:
            logger.error('No matching observation found for datetimestring=%s\n' % (options.datetimestring))
            sys.exit(1)

    elif options.gpstime is not None:
        observation_number=get_observation_info.find_closest_observation((options.gpstime),maxdiff=options.maxtimediff,db=db)
        if observation_number is None:
            logger.error('No matching observation found for gpstime=%d\n' % (options.gpstime))
            sys.exit(1)

    else:
        logger.error('Must specify one of filename, datetime, or gpstime')
        sys.exit(1)
    if options.min:
        """
        Only print the obsid of the _best_ calibrator. Assumes you want matching frequencies.
        Why would you want anything else?
        """
        print observation_number,find_best_cal(observation_number,cal_dtmax=options.dtmax,
                    available_cals=search_subset,relax=True)
        sys.exit(0)
        
    try:
        observation=get_observation_info.MWA_Observation(observation_number,db=db)
    except:
        logger.error('Unable to retrieve observation information for observation %d' % observation_number)
        sys.exit(0)
    matches=find_matches(observation,search_subset=search_subset, matchdelays=options.delay, matchfreq=options.freq, dtmax=options.dtmax, db=db)
    if (matches is None or len(matches)==0):
        logger.warning('No matches identified for observation %d' % observation_number)
        sys.exit(0)
    s='# Starttime  Timediff Filename                  Cal? MJD   Date       Time     Channels                   '
    s+='                                                                     Delays'
    print s
    if observation.calibration:
        ss='T'
    else:
        ss='F'
    s='%10d %10d %-20s\t%s    %d %04d/%02d/%02d %02d:%02d:%02d' % (observation.observation_number,0,
                                                                   observation.filename,ss,
                                                                   observation.MJD,
                                                                   observation.year,observation.month,observation.day,
                                                                   observation.hour,observation.minute,observation.second)
    s+=' %s' % ((','.join([str(x) for x in observation.channels])))
    s+=' %s' % (','.join([str(x) for x in observation.delays]))
    print s
    nprinted=0
    for match in sorted(matches, key=lambda x: math.fabs(x-observation_number)):
        if match == observation_number:
            continue
        try:
            observation=get_observation_info.MWA_Observation(match,db=db)
        except:
            logger.error('Unable to retrieve observation information for observation %d' % match)
            sys.exit(0)
        if options.cal and not observation.calibration:
            continue
        if observation.calibration:
            ss='T'
        else:
            ss='F'
        s='%10d %10d %-20s\t%s    %d %04d/%02d/%02d %02d:%02d:%02d' % (observation.observation_number,
                                                                       (observation.observation_number-observation_number),
                                                                       observation.filename,ss,
                                                                       observation.MJD,
                                                                       observation.year,observation.month,observation.day,
                                                                       observation.hour,observation.minute,observation.second)
        s+=' %s' % ((','.join([str(x) for x in observation.channels])))
        s+=' %s' % (','.join([str(x) for x in observation.delays]))
        print s
        nprinted+=1
        if options.nmax is not None and nprinted >= options.nmax:
            sys.exit(0)
        if options.dtmax is not None and math.fabs(match-observation_number)>options.dtmax:
            sys.exit(0)

######################################################################
if __name__=="__main__":
    main()
