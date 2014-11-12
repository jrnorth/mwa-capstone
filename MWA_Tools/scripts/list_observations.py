import logging, sys, os, glob, string, re, urllib, math, time
from optparse import OptionParser
import numpy

import mwapy
from mwapy import ephem_utils, dbobj
from mwapy import get_observation_info
from mwapy.obssched.base import schedule
from mwapy.obssched import list_observations

# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('get_sched')
logger.setLevel(logging.WARNING)


# open up database connection
try:
    db = schedule.getdb()
except:
    logger.error("Unable to open connection to database")
    sys.exit(1)


######################################################################
def main():


    usage="Usage: %prog [options]\n"
    parser = OptionParser(usage=usage,version=mwapy.__version__ + ' ' + mwapy.__date__)
    parser.add_option('--starttime',dest="starttime",type='int',default=0,
                      help='Starting GPStime of search window')
    parser.add_option('--stoptime',dest="stoptime",type='str',default='++8s',
                      help='Ending GPStime of search window or increment on <starttime> [default=%default]')
    parser.add_option('-v','--verbose',action="store_true",dest="verbose",default=False,
                      help="Increase verbosity of output")
    parser.add_option('-q','--quiet',action="store_false",dest="verbose",default=False,
                      help="Decrease verbosity of output")

    (options, args) = parser.parse_args()

    if (options.verbose):
        logger.setLevel(logging.INFO)

    if options.starttime == 0:
        logger.error('Must supply starttime')
        sys.exit(1)
    options.stoptime=list_observations.convert_time(options.stoptime, options.starttime)
                             
    data=list_observations.get_observations(options.starttime, options.stoptime, db=db)
    if data is None:
        sys.exit(0)
    if len(data)>0:
        print '# Start\t\tStop\t\tProject\tCalibration?\tName'
        for d in data:
            print '%d\t%d\t%s\t%s\t\t%s' % (d[0], d[1], d[3], d[4], d[2])
    
######################################################################

if __name__=="__main__":
    main()
