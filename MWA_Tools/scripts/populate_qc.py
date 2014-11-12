#! /usr/bin/env python

import sys,os,logging,shutil,datetime,re,subprocess,math,tempfile,string,glob,copy
import numpy,ephem
import itertools
from optparse import OptionParser,OptionGroup
from mwapy import ephem_utils, dbobj, get_observation_info, make_metafiles
import psycopg2
import mwapy
import astropy.time,astropy.coordinates.angles
from mwapy.eorpy import qcdb

try:
    from mwapy.eorpy import ionex
    _USE_IONEX=True
except ImportError:
    _USE_IONEX=False

# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('populate_qc')
logger.setLevel(logging.INFO)

try:
    from mwapy.obssched.base import schedule
except:
    logger.error("Unable to open connection to database")
    sys.exit(1)
# open up database connection
try:
    db = schedule.getdb()
except:
    logger.error("Unable to open connection to database")
    sys.exit(1)

try:
    qcdbcon = qcdb.getdb()
    
except:
    logger.error("Unable to open connection to QC database")
    sys.exit(1)


################################################################################

_ionex_files=[]

######################################################################
def main():


    usage="Usage: %prog [options] <obsids>\n"
    usage+="\tPopulates the MWA EOR QC database for a specific observation\n"
    usage+="\tExample:\n\t\tpython ~/mwa/bin/populate_qc.py -v 1061316296\n"
    obsid=None
    parser = OptionParser(usage=usage,version=mwapy.__version__ + ' ' + mwapy.__date__)
    parser.add_option('-c','--clean',action="store_true",dest="clean",default=False,
                      help="Clean temporary IONEX files?")
    parser.add_option('-v','--verbose',action="store_true",dest="verbose",default=False,
                      help="Increase verbosity of output")
    parser.add_option('-q','--quiet',action="store_false",dest="verbose",default=False,
                      help="Decrease verbosity of output")

    (options, args) = parser.parse_args()

    if (options.verbose):
        logger.setLevel(logging.INFO)

    if len(args)==0:
        logger.error('Must supply obsid')
        sys.exit(1)
    x=db.dsn.split()
    dbname='%s@%s:%s:%s' % (x[1].split('=')[1],
                            x[3].split('=')[1],
                            x[0].split('=')[1],
                            x[4].split('=')[1])
    logger.info('Connecting to database %s'  % dbname)
    x=qcdbcon.dsn.split()
    dbname='%s@%s:%s:%s' % (x[1].split('=')[1],
                            x[3].split('=')[1],
                            x[0].split('=')[1],
                            x[4].split('=')[1])

    logger.info('Connecting to QC database %s@%s:%s:%s'  % (x[1].split('=')[1],
                                                            x[3].split('=')[1],
                                                            x[0].split('=')[1],
                                                            x[4].split('=')[1]))
                

    for obsid in map(int,args):
    
        observation_num=get_observation_info.find_closest_observation(obsid,maxdiff=0,db=db)
        if observation_num is None:
            logger.error('No matching observation found for obsid=%d\n' % (obsid))
            sys.exit(1)
        oi=populate_qc(obsid, verbose=options.verbose)
        errors = oi.save(ask=0, force=True, verbose=options.verbose, db=qcdbcon)
        logger.info('Wrote %s' % oi)

    if options.clean and len(_ionex_files)>0:
        for file in set(_ionex_files):
            os.remove(file)


    qcdbcon.close()
    db.close()
    exit(0)
    


################################################################################
def populate_qc(obsid, verbose=False):
    """
    populate_qc(obsid, verbose=False)
    actually does the population
    """
    try:
        observation_info=get_observation_info.MWA_Observation(obsid, db=db)
    except:
        logger.error('Cannot retrieve observation info for %d' % obsid)
        return None
        
    if verbose:
        print '\nFound observation:'
        print observation_info
            
    
    oi=qcdb.Observation_Info(db=qcdbcon)
    oi.obsid=obsid
    oi.lst_deg=observation_info.LST
    if isinstance(observation_info.HA,numpy.ndarray):
        oi.hourangle_deg=observation_info.HA[0]*15
    else:
        oi.hourangle_deg=observation_info.HA*15        
    oi.obsname=observation_info.filename
    oi.gridname=observation_info._Schedule_Metadata.gridpoint_name
    oi.gridnum=observation_info._Schedule_Metadata.gridpoint_number
    oi.creator=observation_info._MWA_Setting.creator
    oi.mode=observation_info._MWA_Setting.mode
    oi.project=observation_info._MWA_Setting.projectid
    oi.calibrator=observation_info.calibration
    oi.center_coarse_channel=observation_info.center_channel
    oi.azimuth_deg=observation_info.azimuth
    oi.altitude_deg=observation_info.elevation
    oi.ra_pointing_deg=observation_info.RA
    oi.dec_pointing_deg=observation_info.Dec
    oi.coarse_channels=list(observation_info.channels)
    oi.beamformer_delays=list(observation_info.delays)
    oi.active_rx=list(observation_info.receivers)
    oi.exposure_time_sec=observation_info.duration
    oi.corr_int_time=observation_info.inttime
    oi.corr_int_freq=observation_info.fine_channel
    # DIGITAL_GAINS: are per tile
    corr2uvfitsheader=make_metafiles.Corr2UVFITSHeader(obsid,
                                                       db=db)
    corr2uvfitsheader.make_header()
    nav_freq=int(corr2uvfitsheader.fine_channel/10)
    oi.center_freq=make_metafiles.channel2frequency(corr2uvfitsheader.channel)+(nav_freq-1)*0.005,
    oi.bandwidth=corr2uvfitsheader.bandwidth
    oi.corr_ninputs=corr2uvfitsheader.n_inputs
    oi.corr_n_time_outs=corr2uvfitsheader.n_scans
    oi.n_fine_channels=corr2uvfitsheader.n_chans
    # need to calculate these
    oi.sun_dist,oi.sun_alt=qcdb.get_elevation_separation_azel(oi.azimuth_deg,
                                                              oi.altitude_deg,
                                                              obsid,
                                                              'Sun')
    oi.moon_dist,oi.moon_alt=qcdb.get_elevation_separation_azel(oi.azimuth_deg,
                                                                oi.altitude_deg,
                                                                obsid,
                                                                'Moon')
    oi.jupiter_dist,oi.jupiter_alt=qcdb.get_elevation_separation_azel(oi.azimuth_deg,
                                                                      oi.altitude_deg,
                                                                      obsid,
                                                                      'Jupiter')
    
    # Get sky temp from Schedule_Metadata
    schedule_metadata=observation_info._Schedule_Metadata
    oi.tsys=schedule_metadata.sky_temp

    # Get schedule command from Mwa_Log
    mwa_setting=observation_info._MWA_Setting
    for i in xrange(len(mwa_setting.logs)):
        if mwa_setting.logs[i].referencetime==obsid:
            oi.schedule_command=mwa_setting.logs[i].comment
            
    # do some time/date conversions
    t=astropy.time.Time(obsid,format='gps',scale='utc')
    oi.mjd=t.mjd
    # 0 is Monday
    oi.day_of_week=t.datetime.weekday()
    oi.day_of_year=t.datetime.timetuple().tm_yday
    oi.date=list(t.datetime.timetuple()[:6])

    if _USE_IONEX:
        #i=ionex.ionexmaps(t)
        oi.site_tec=observation_info.TEC
        #_ionex_files.append(i.filename)
    
    # don't know how to do:
    # 'site_rms_tec'
    # 'rx_outside_temp'
    # 'humidity'
    # 'wind_speed'
    # 'wind_dir'
    # 'solar_problem'
    # 'holiday'
    # 'FIBRFACT'

    return oi
    

######################################################################

if __name__=="__main__":
    main()
    
