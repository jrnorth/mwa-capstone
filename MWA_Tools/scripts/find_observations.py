#!/usr/bin/env python
"""
Finds MWA observations based on a project code and date range
DJacobs

Sept. 12 2012

Updated for new web service queries
D Kaplan
"""

import logging, sys, os, glob, string, re, urllib, math, time, datetime
import optparse
import numpy

import ephem
import mwapy
from mwapy import ephem_utils, metadata

from astropy.time import Time
from astropy.coordinates.angles import Angle
#from astropy.coordinates.errors import UnitsError
from astropy.units.core import UnitsError
from astropy import units as u

# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('metadata')
logger.setLevel(logging.WARNING)



##################################################
def tokenize(input):
    """
    web queries use different wildcards than normal people
    turn ? to _
    turn % to *
    """
    
    if input is not None:
        input=input.replace('_','\_')
        return input.replace('?','_').replace('*','%')
    else:
        return input

##################################################
def parse_time(input):
    """
    parse input time (GPStime or datetime string)
    """
    try:
        return int(input)
    except ValueError:
        # try to parse it as a date
        try:
            t=Time(input, scale='utc')
        except ValueError,e:
            try:
                t=Time(datetime.datetime.strptime(options.datetimestring, '%Y%m%d%H%M%S'), scale='utc')
            except ValueError,e:                                
                logger.error('Unable to parse input time %s: %s' % (input,
                                                                    e))
                return None
        return int(t.gps)
    





##################################################
def main():

    usage="Usage: %prog [options]\n"
    usage+="\tFinds MWA Observations based on a set of query parameters\n"
    usage+="\tWill return just the obsids(default) or more information (if verbose)\n"
    o = optparse.OptionParser(usage=usage,version=mwapy.__version__ + ' ' + mwapy.__date__)
    o.add_option('--limit', type='int', default=100,
                 help='Limit on number of results returned [default=%default]')
    o.add_option('--proj', type='str', default=None,
                 help = 'Project ID')
    #o.add_option('--list_projects', action='store_true',
    #             help = 'List available project ids and exit')
    o.add_option('--start', type='str', default=None,
                 help='Start time (GPSseconds or ISO UT date)')
    o.add_option('--stop', type='str', default=None,
                 help='Stop time (GPSseconds or ISO UT date)')
    o.add_option('--racenter', type='str', default=None,
                 help='Center RA for search (decimal degrees or hms)')
    o.add_option('--deccenter', type='str', default=None,
                 help='Center Dec for search (decimal degrees or dms)')
    o.add_option('--rawidth', type='str', default='10d',
                 help='Width of RA search box (degrees assumed; will not handle 360d boundary) [default=%default]')
    o.add_option('--decwidth', type='str', default='10d',
                 help='Width of Dec search box (degrees) [default=%default]')
    o.add_option('--chan',type='int', default=None,
                 help='Center channel')
    o.add_option('--anychan',type='int',default=None,
                 help='Match to any channel')
    o.add_option('--contiguous', action='store_true',dest='contiguous',default=None,
                 help='Only include observations with contiguous frequency channels')
    o.add_option('--discontiguous', action='store_false',dest='contiguous',default=None,
                 help='Only include observations with discontiguous frequency channels')
    o.add_option('--inttime', type='int', default=None,
                 help='Integration time (s)')
    o.add_option('--freqres', type='int', default=None,
                 help='Frequency resolution (kHz)')
    #o.add_option('--withdata*',action='store_true',
    #             help="Only include observations with data.")
    o.add_option('--cal',action='store_true', default=None,dest='withcal',
                 help="Only get data that are marked as calibrations")
    o.add_option('--nocal',action='store_false', default=None,dest='withcal',
                 help="Only get data that are not marked as calibrations")
    o.add_option('--future',action='store_true', default=None,dest='future',
                 help="Only get observations that are in the future")
    o.add_option('--past',action='store_false', default=None,dest='future',
                 help="Only get observations that are in the past")
    o.add_option('--creator',type='str',default=None,
                 help='Creator')
    o.add_option('--mode',type='str',default=None,
                 help='Observation mode')
    o.add_option('--obsname',type='str',
                 help='Match any part of an observation name')
    o.add_option('--close',default=False, action='store_true',
                 help='Sort by observations closest in time')
    o.add_option('--maxdiff',default='1d',
                 help='Maximum time difference for proximity search [default=%default]')
    o.add_option('-v','--verbose',action="store_true",dest="verbose",default=False,
                 help="Increase verbosity of output")
    o.add_option('--full',action="store_true",dest="full",default=False,
                 help="Print full info for each observation")
    o.add_option('-u','--url',default=metadata._BASEURL,
                 help="URL for metadata retrieval [default=%default]")

    options, args = o.parse_args()

    if (options.verbose):
        logger.setLevel(logging.INFO)

    cal=None
    if options.withcal is not None:
        if options.withcal:
            cal=1
        else:
            cal=0

    contiguous=None
    if options.contiguous is not None:
        if options.contiguous:
            contiguous=1
        else:
            contiguous=0

    future=None
    if options.future is not None:
        if options.future:
            future=1
        else:
            future=0

    if options.start is not None:
        GPSstart=parse_time(options.start)
        if GPSstart is None:
            sys.exit(1)
    else:
        GPSstart=None
    if options.stop is not None:
        GPSstop=parse_time(options.stop)
        if GPSstop is None:
            sys.exit(1)
    else:
        GPSstop=None

    racenter,deccenter=None,None
    rawidth,decwidth=None,None
    if options.racenter is not None:
        try:
            racenter=Angle(options.racenter)
        except UnitsError:
            try:
                racenter=Angle(float(options.racenter), unit=u.degree)
            except ValueError:
                try:
                    racenter=Angle(options.racenter, unit=u.hourangle)
                except:
                    logger.error('Unable to parse input RA %s' % options.racenter)
                    sys.exit(1)
        except:
            print 'othererror'
            logger.error('Unable to parse input RA %s' % options.racenter)
            sys.exit(1)

    if options.deccenter is not None:
        try:
            deccenter=Angle(options.deccenter, unit=u.degree)
        except:
            logger.error('Unable to parse input Dec %s' % options.deccenter)
            sys.exit(1)
    
    if options.rawidth is not None:
        try:
            rawidth=Angle(options.rawidth)
        except UnitsError:
            try:
                rawidth=Angle(options.rawidth, unit=u.degree)
            except:
                logger.error('Unable to parse RA width %s' % options.rawidth)
                sys.exit(1)
        except:
            logger.error('Unable to parse RA width %s' % options.rawidth)
            sys.exit(1)

    if options.decwidth is not None:
        try:
            decwidth=Angle(options.decwidth, unit=u.degree)
        except:
            logger.error('Unable to parse input Dec %s' % options.decwidth)
            sys.exit(1)

    maxdiff=None
    if options.maxdiff is not None:
        # try seconds
        try:
            maxdiff=int(options.maxdiff)
        except ValueError:
            if options.maxdiff[-1]=='s':
                maxdiff=int(options.maxdiff[:-1])
            elif options.maxdiff[-1]=='m':
                maxdiff=int(float(options.maxdiff[:-1])*60)
            elif options.maxdiff[-1]=='h':
                maxdiff=int(float(options.maxdiff[:-1])*60*60)
            elif options.maxdiff[-1]=='d':
                maxdiff=int(float(options.maxdiff[:-1])*86400)
            else:
                logger.error('Unable to parse time difference %s' % options.maxdiff)
                sys.exit(1)
                
    if GPSstart is not None and GPSstop is not None:
        logger.info('Searching from %d to %d...' % (GPSstart,GPSstop))
    elif GPSstart is not None:
        logger.info('Searching from %d...' % (GPSstart))
    elif GPSstop is not None:
        logger.info('Searching until %d...' % (GPSstop))
    if options.proj is not None:
        logger.info('Require projectid=%s' % options.proj)
    if options.withcal is not None:
        if options.withcal:
            logger.info('Require calibrator observations')
        else:
            logger.info('Require noncalibrator observations')
    if options.creator is not None:
        logger.info('Require creator=%s' % options.creator)
    if options.mode is not None:
        logger.info('Require mode=%s' % options.mode)
    if options.chan is not None:
        logger.info('Require center channel=%d' % options.chan)
    if options.anychan is not None:
        logger.info('Require any channel=%d' % options.anychan)
    if options.contiguous is not None:
        if options.contiguous:
            logger.info('Require contiguous frequency channels')
        else:
            logger.info('Require discontiguous frequency channels')
    if options.inttime:
        logger.info('Require integration time=%d s' % options.inttime)
    if options.freqres:
        logger.info('Require frequency resolution=%d kHz' % options.freqres)
    if racenter is not None:
        ramin=(max(racenter-rawidth/2,Angle(0,unit=u.degree))).degree
        ramax=(min(racenter+rawidth/2,Angle(360,unit=u.degree))).degree
        logger.info('Require %.1fd < RA < %.1fd' % (ramin,
                                                    ramax))
    else:
        ramin,ramax=None,None
    if deccenter is not None:
        decmin=(max(deccenter-decwidth/2,Angle(-90,unit=u.degree))).degree
        decmax=(min(deccenter+decwidth/2,Angle(90,unit=u.degree))).degree
        logger.info('Require %.1fd < Dec < %.1fd' % (decmin,
                                                     decmax))
    else:
        decmin,decmax=None,None

    if options.obsname is not None:
        logger.info('Require obsname=%s' % options.obsname)

    if options.future is not None:
        if options.future:
            logger.info('Require observation in the future')
        else:
            logger.info('Require observation in the past')
    if options.close:
        if GPSstart is None:
            logger.error('Require start time with --close')
            sys.exit(1)
        logger.info('Will sort observations within %ds of %d...' % (
            maxdiff,
            GPSstart))

    
    if not options.close:
        results=metadata.fetch_observations(URL=options.url,
                                            mintime=GPSstart,
                                            maxtime=GPSstop,
                                            minra=ramin,
                                            maxra=ramax,
                                            mindec=decmin,
                                            maxdec=decmax,
                                            limit=options.limit,
                                            projectid=tokenize(options.proj),
                                            calibration=cal,
                                            contigfreq=contiguous,
                                            cenchan=options.chan,
                                            anychan=options.anychan,
                                            int_time=options.inttime,
                                            freq_res=options.freqres,
                                            creator=tokenize(options.creator),
                                            mode=tokenize(options.mode),
                                            obsname=tokenize(options.obsname),
                                            future=future)

                                       
        if results is None or len(results)==0:
            print 'Query return no results'
            sys.exit(0)
        if options.verbose:
            print metadata.MWA_Observation_Summary.string_header()
        else:
            print '# starttime'
        for item in results:
            o=metadata.MWA_Observation_Summary(item)
            if options.verbose:
                print o
            else:
                print o.obsid

            if options.full:
                observation=metadata.MWA_Observation(o.obsid,
                                                     rfstream=0,
                                                     ionex=False, url=options.url)
                print observation

    else:
        GPSstop=GPSstart+maxdiff

        results1=metadata.fetch_observations(URL=options.url,
                                             mintime=GPSstart,
                                             maxtime=GPSstop,
                                             minra=ramin,
                                             maxra=ramax,
                                             mindec=decmin,
                                             maxdec=decmax,
                                             limit=options.limit/2,
                                             projectid=tokenize(options.proj),
                                             calibration=cal,
                                             contigfreq=contiguous,
                                             cenchan=options.chan,
                                             anychan=options.anychan,
                                             int_time=options.inttime,
                                             freq_res=options.freqres,
                                             creator=tokenize(options.creator),
                                             mode=tokenize(options.mode),
                                             obsname=tokenize(options.obsname),
                                             future=future)
        GPSstop=GPSstart-maxdiff

        try:
            results2=metadata.fetch_observations(URL=options.url,
                                                 mintime=GPSstop,
                                                 maxtime=GPSstart,
                                                 minra=ramin,
                                                 maxra=ramax,
                                                 mindec=decmin,
                                                 maxdec=decmax,
                                                 limit=options.limit/2,
                                                 projectid=tokenize(options.proj),
                                                 calibration=cal,
                                                 contigfreq=contiguous,
                                                 cenchan=options.chan,
                                                 anychan=options.anychan,
                                                 int_time=options.inttime,
                                                 freq_res=options.freqres,
                                                 creator=tokenize(options.creator),
                                                 mode=tokenize(options.mode),
                                                 obsname=tokenize(options.obsname),
                                                 future=future)[::-1]
            results=results2+results1
        except:
            results=results1

        if results is None or len(results)==0:
            print 'Query return no results'
            sys.exit(0)
        if options.verbose:
            print metadata.MWA_Observation_Summary.string_header()
        else:
            print '# starttime'
        last=None
        for item in results:            
            o=metadata.MWA_Observation_Summary(item)
            if (last is None or last < GPSstart) and o.obsid >= GPSstart:
                print '# ***** %d\t%s' % (GPSstart,
                                          Time(GPSstart,format='gps',
                                               scale='utc').datetime.strftime('%Y-%m-%dT%H:%M:%S'))
            if options.verbose:
                print o
            else:
                print o.obsid
            last=o.obsid
            if options.full:
                observation=metadata.MWA_Observation(o.obsid,
                                                     rfstream=0,
                                                     ionex=False, url=options.url)
                print observation

        

        
    sys.exit(0)
################################################################################
    
if __name__=="__main__":
    main()
