"""
matches=find_matches(observation, matchfreq=True, matchdelays=True,db=None)

returns matches from the observation database that match the supplied observation
observation can be specified via observation_number or get_observation_info.MWA_Observation object

matches are via frequency and/or delays

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
def find_matches(observation, search_subset=None, matchfreq=True, matchdelays=True, dtmax=None, db=None):
    """
    matches=find_matches(observation, matchfreq=True, matchdelays=True,dtmax=None, db=None)

    returns matches from the observation database that match the supplied observation
    observation can be specified via observation_number or get_observation_info.MWA_Observation object

    matches are via frequency and/or delays
    """

    if db is None:
        logger.error('Must supply a database object')
        return None
    
    if not matchfreq and not matchdelays:
        logger.error('Must match frequencies and/or delays')
        return None
    if (not isinstance(observation, get_observation_info.MWA_Observation)):
        try:
            o=get_observation_info.MWA_Observation(observation,db=db)
        except:
            logger.error('Unable to retrieve observation information for observation %d' % observation)
            return None
        observation=o
    
    delays=observation.delays
    channels=observation.channels
    #receiver=observation.receivers[0]

    
    s='select observation_number from Obsc_Recv_Cmds where '
    if not search_subset is None:
        s+=' observation_number IN ('+','.join(map(str,search_subset))+') and '
    if matchfreq:
        s+='frequency_values = array[%s]' % (
            ','.join([str(x) for x in channels]))
    if matchfreq and matchdelays:
        s+=' and '
    if matchdelays:
        s+=' xdelaysetting[1:1]=array[array[%s]]' % (
        ','.join([str(x) for x in delays]))
    if dtmax is not None:
        if matchfreq or matchdelays:
            s+=' and '
        s+=' abs(observation_number - %d) < %d' % (observation.observation_number, dtmax)
    logger.debug("SQL = %s"%s)
    res=dbobj.execute(s,db=db)

    return set([xx[0] for xx in res])


def find_best_cal(observation_number,cal_dtmax=6e5,available_cals=None,relax=False):
    # open up database connection
    try:
        db = schedule.getdb()
    except:
        logger.error("Unable to open connection to database")
        sys.exit(1)
    logger.debug("searching db for obsnum %d"%observation_number)
    try:
        observation=get_observation_info.MWA_Observation(observation_number,db=db)
    except:
        logger.error('Unable to retrieve observation information for observation %d' % observation_number)
        sys.exit(0)
    matches=find_matches(observation, matchdelays=True, matchfreq=True, dtmax=cal_dtmax,\
    db=db,search_subset=available_cals) 
    if (matches is None or len(matches)==0):
        if relax:
            #logger.warning("""No matches identified for observation %d, relaxing delay match
            #constraint."""%observation_number)
            #logger.warning('WARNING FLUX CAL WILL BE BOGUS')
            matches=find_matches(observation, matchfreq=True, matchdelays=False,dtmax=cal_dtmax,\
                db=db,search_subset=available_cals) 
    if matches is None:
        logger.warning('No matches identified for observation %d' % observation_number)
        sys.exit(1)
    logger.debug("sorting through %d matches for nearest calibrator"%len(matches))
    for match in sorted(matches, key=lambda x: math.fabs(x-observation_number)):
        if match == observation_number:
            continue
        try:
            observation=get_observation_info.MWA_Observation(match,db=db)
        except:
            logger.error('Unable to retrieve observation information for observation %d' % match)
            sys.exit(0)
        if observation.calibration:
            return observation.observation_number
    logger.error("No cal found for observation %d "%observation_number)
    return None

