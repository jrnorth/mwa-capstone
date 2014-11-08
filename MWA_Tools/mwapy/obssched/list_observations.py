import logging, sys, os, glob, string, re, urllib, math, time
from optparse import OptionParser
import numpy

import mwapy
from mwapy import ephem_utils, dbobj
from mwapy import get_observation_info
from mwapy.obssched.base import schedule

# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('list_observations')
logger.setLevel(logging.WARNING)


# open up database connection
try:
    db = schedule.getdb()
except:
    logger.error("Unable to open connection to database")
    sys.exit(1)

##################################################
def get_observations(starttime, stoptime, db=None):
    """
    data=get_observations(starttime, stoptime, db=None)
    data is list of (starttime, stoptime, obsname, projectid, calibration)
    """

    if db is None:
        logger.error('Must supply database connection')
        return None

    logger.info('Searching for observations between %d and %d' % (starttime,
                                                                  stoptime))
    
    try:
        observations=dbobj.execute('select starttime from mwa_setting where starttime>=%d and starttime<%d order by starttime' % (starttime, stoptime),
                                   db=db)
    except (psycopg2.InternalError, psycopg2.ProgrammingError) , e:
        logger.warning('Database error=%s' % (e.pgerror))
        db.rollback()
        return None

    logger.info('%d observations found' % (len(observations)))
    starttimes=[]
    stoptimes=[]
    obsnames=[]
    calibrators=[]
    projects=[]
    for observation in observations:
        try:
            s=schedule.MWA_Setting(observation[0], db=db)
        except (psycopg2.InternalError, psycopg2.ProgrammingError) , e:
            logger.warning('Database error=%s' % (e.pgerror))
            db.rollback()
            return None

        starttimes.append(s.starttime)
        stoptimes.append(s.stoptime)
        obsnames.append(s.obsname)
        projects.append(s.projectid)
        try:
            m=schedule.Schedule_Metadata(observation[0], db=db)
        except (psycopg2.InternalError, psycopg2.ProgrammingError) , e:
            logger.warning('Database error=%s' % (e.pgerror))
            db.rollback()
            return None
            
        calibrators.append(m.calibration)

    return zip(starttimes, stoptimes, obsnames, projects, calibrators)

######################################################################
def convert_time(newtime, lasttime):
    """
    timeout=convert_time(newtime, lasttime)
    converts the timestring given in newtime to a time in GPSseconds, return as timeout
    lasttime is the last time return, used for increments
    formats for newtime::

      ++dt                 - increments lasttime by dt seconds
      yyyy-mm-dd,hh:mm:ss  - UT date/time
      t                    - GPS seconds


    :param newtime: new time to parse
    :param lasttime: previous time passed, used for parsing increments
    :return: GPStime

    """
    
    timeout=0
    if not isinstance(newtime,str):
        return newtime
    if (newtime.startswith('++')):
        try:
            dt_string=newtime.replace('++','')
            if (dt_string.count('s')):
                # seconds
                dt=int(dt_string.replace('s',''))
            elif (dt_string.count('m')):
                # minutes
                dt=int(60*float(dt_string.replace('m','')))
            elif (dt_string.count('h')):
                # hours
                dt=int(3600*float(dt_string.replace('h','')))
            else:
                # assume seconds
                dt=int(dt_string)
        except ValueError:
            logging.warn('Unable to interpret time increment: %s' % newtime)
            return timeout
        timeout=ephem_utils.GPSseconds_next(lasttime+dt-8)
    elif (newtime.count(':')>0):
        try:
            [date,tm]=newtime.split(',')
            [yr,mn,dy]=date.split('-')
            UT=ephem_utils.sexstring2dec(tm)
            MJD=ephem_utils.cal_mjd(int(yr),int(mn),int(dy))
            timeout=ephem_utils.GPSseconds_next(ephem_utils.calcGPSseconds(MJD,UT)-8)
        except:
            logging.warn('Unable to interpret timestamp: %s' % newtime)
            return timeout
    else:
        try:
            timeout=ephem_utils.GPSseconds_next(int(newtime)-8)
        except ValueError:
            logging.warn('Unable to interpret GPStime: %s' % newtime)
            return timeout

    return timeout
