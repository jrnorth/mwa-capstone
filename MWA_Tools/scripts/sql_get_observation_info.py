#!/usr/bin/env python
"""

Gets fundamental information about an observation

python ~/mwa/software/MWA_Tools/get_observation_info.py --filename='P00_drift_121_20110927161501' -v -i
# INFO:get_observation_info: Found matching observation for GPS time 1001175316 in MWA_Setting database at GPS time=1001175315 (difference=-1 s)

# INFO:get_observation_info: Found delays in RFstream (0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0)

P00_drift_121 at 1001175315 (GPS)
55831 (2011/09/27) 16:15:00, for 300 s (Sun at -61.5 deg)
Channels: 109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128,129,130,131,132 (center=121)
LST=00:26:07 (HA=00:00:38)
(Az,El) = (0.000, 90.000) deg
(RA,Dec) = (6.374, -26.772) deg (J2000)
delays = 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
# INFO:get_observation_info: Creating sky image for 2011/09/27 16:15:00, 154.88 MHz, delays=0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

# INFO:get_observation_info: Wrote 20110927161500_154.88MHz.png

wraps get_observation_info module in 
"""


import logging, sys, os, glob, string, re, urllib, math, time
from optparse import OptionParser
import numpy

import ephem
import mwapy
from mwapy import ephem_utils
from mwapy.get_observation_info import *
from mwapy.obssched.base import schedule

try:
    from mwapy.pb import primarybeammap
    _useplotting=True
except ImportError:
    _useplotting=False    

# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('get_observation_info')
logger.setLevel(logging.WARNING)

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
    usage+="\tDetermines observation information (frequencies, pointing information)\n"
    usage+="\tCan search based on a filename, a UT datetime string, or a GPS time\n"
    usage+="\tRequires connection to MandC database through local configuration file\n"
    parser = OptionParser(usage=usage,version=mwapy.__version__ + ' ' + mwapy.__date__)
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
    parser.add_option('-i','--image',action="store_true",dest="image",default=False,
                      help="Generate an image for this pointing?")
    parser.add_option('--tle',dest='tle',default=None,
                      help='Satellite TLE file for overplotting on image')
    parser.add_option('--ionex',dest='ionex',default=False,action='store_true',
                      help='Compute IONEX quantities?')
    parser.add_option('-v','--verbose',action="store_true",dest="verbose",default=False,
                      help="Increase verbosity of output")
    parser.add_option('-q','--quiet',action="store_false",dest="verbose",default=False,
                      help="Decrease verbosity of output")

    (options, args) = parser.parse_args()

    if (options.verbose):
        logger.setLevel(logging.INFO)

    
    x=db.dsn.split()
    dbname='%s@%s:%s:%s' % (x[1].split('=')[1],
                            x[3].split('=')[1],
                            x[0].split('=')[1],
                            x[4].split('=')[1])
    logger.info('Connecting to database %s'  % dbname)

    if options.filename is not None:
        observation_num=find_observation_num(options.filename, maxdiff=options.maxtimediff, db=db)
        if observation_num is None:
            observation_num=find_observation_num(options.filename, suffix='', maxdiff=options.maxtimediff, db=db)
        if observation_num is None:
            logger.error('No matching observation found for filename=%s\n' % (options.filename))
            sys.exit(1)
    elif options.datetimestring is not None:
        observation_num=find_observation_num(options.datetimestring, maxdiff=options.maxtimediff, db=db)
        if observation_num is None:
            logger.error('No matching observation found for datetimestring=%s\n' % (options.datetimestring))
            sys.exit(1)

    elif options.gpstime is not None:
        observation_num=find_closest_observation((options.gpstime),maxdiff=options.maxtimediff,db=db)
        if observation_num is None:
            logger.error('No matching observation found for gpstime=%d\n' % (options.gpstime))
            sys.exit(1)

    else:
        logger.error('Must specify one of filename, datetime, or gpstime')
        sys.exit(1)
        

    if observation_num is not None:
        observation=MWA_Observation(observation_num,ionex=options.ionex, db=db)
        print observation
        if (options.image):
            if (not _useplotting):
                logger.warning('Unable to import primarybeammap to generate image\n')
                return
            datetimestring='%04d%02d%02d%02d%02d%02d' % (observation.year,observation.month,
                                                         observation.day,
                                                         observation.hour,observation.minute,
                                                         observation.second)


            logger.info('Creating sky image for %04d/%02d/%02d %02d:%02d:%02d, %.2f MHz, delays=%s\n' % (
                observation.year,observation.month,observation.day,
                observation.hour,observation.minute,observation.second,
                1.28*observation.center_channel,
                ','.join([str(x) for x in observation.delays])))
            result=primarybeammap.make_primarybeammap(datetimestring, observation.delays,
                                                      frequency=1.28*observation.center_channel,
                                                      center=True,
                                                      title=observation.filename,tle=options.tle,
                                                      duration=observation.duration)
            if (result is not None):
                logger.info("Wrote %s" % result)

    
    sys.exit(0)
################################################################################
    
if __name__=="__main__":
    main()
