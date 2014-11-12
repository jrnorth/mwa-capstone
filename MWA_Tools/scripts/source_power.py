"""
Returns relative power compared to pointing center for an observation and a source

Can look up source based on RA,Dec, l,b, or name

plock[schedule]% python ~/mwa/bin/source_power.py -g 1070384384 -v --source='PSR J0437-4715'
# WARNING:mwapy.pb.mwapb: This module 'mwapy.pb.mwapb' is deprecated and does not use the up-to-date beam models. Use the new primary beam model instead in mwa_tile.
# INFO:source_power: Observation at gpstime=1070384384, 154 MHz, delays=[0, 0, 0, 0, 4, 4, 4, 4, 8, 8, 8, 8, 12, 12, 12, 12]
# INFO:source_power: Calculating for RA,Dec=4:37:15.8 -47:15:08.6
Separation: 18.99 deg
Power: 0.42
"""

import logging, sys, os, glob, string, re, urllib, math, time
from optparse import OptionParser
import numpy

import mwapy
from mwapy import ephem_utils, dbobj
from mwapy import get_observation_info
from mwapy.pb import primary_beam
from mwapy.obssched.base import schedule
from astropy.coordinates import ICRS, Galactic
from astropy import units as u
import ephem

# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('source_power')
logger.setLevel(logging.WARNING)


# open up database connection
try:
    db = schedule.getdb()
except:
    logger.error("Unable to open connection to database")
    sys.exit(1)


usage="Usage: %prog [options]\n"
usage+='\tReturns relative power compared to pointing center for an observation and a source\n'
parser = OptionParser(usage=usage,version=mwapy.__version__ + ' ' + mwapy.__date__)
parser.add_option('-g','--gps',dest="gpstime",default=None,
                  help="Search for information on <GPS>",type='int',
                  metavar="GPS")
parser.add_option('--ra',dest='ra', default=None,
                  help='RA for calculation')
parser.add_option('--dec',dest='dec', default=None,
                  help='Dec for calculation')
parser.add_option('--l',dest='l', default=None,
                  help='Galactic l for calculation')
parser.add_option('--b',dest='b', default=None,
                  help='Galactic b for calculation')
parser.add_option('--source',dest='source', default=None,
                  help='Source name for calculation')
parser.add_option('-v','--verbose',action="store_true",dest="verbose",default=False,
                  help="Increase verbosity of output")
parser.add_option('-q','--quiet',action="store_false",dest="verbose",default=False,
                  help="Decrease verbosity of output")

(options, args) = parser.parse_args()

if (options.verbose):
    logger.setLevel(logging.INFO)


observationid=options.gpstime
if observationid is None:
    logger.error('Must supply gpstime')
    sys.exit(1)
    

coord=None
if options.ra is not None and options.dec is not None:
    ra,dec=options.ra,options.dec
    if 'h' in ra or ':' in ra:
        coord=ICRS(ra=ra,dec=dec,unit=(u.hour, u.degree))
    else:
        coord=ICRS(ra=ra,dec=dec,unit=(u.degree, u.degree))
if options.l is not None and options.b is not None:
    coord=Galactic(l=options.l, b=options.b, unit=(u.degree, u.degree)).transform_to(ICRS)
if options.source is not None:
    try:
        coord=ICRS.from_name(options.source)
    except:
        logger.error("Unable to find coordinates for '%s'" % options.source)
        sys.exit(1)

if coord is None:
    logger.error('Must supply one of (RA,Dec), (l,b), source')
    sys.exit(1)

observation_num=get_observation_info.find_closest_observation(observationid, maxdiff=0, db=db)
if observation_num is None:
    logger.error('Observation not found for gpstime=%d' % observationid)
    sys.exit(1)
obs=get_observation_info.MWA_Observation(observationid, db=db)
Az,El=ephem_utils.radec2azel(coord.ra.degree, coord.dec.degree, obs.observation_number)
# first go from altitude to zenith angle
theta=numpy.radians((90-El))
phi=numpy.radians(Az)
# this is the response for XX and YY
try:
    respX,respY=primary_beam.MWA_Tile_analytic(theta,phi,
                                               freq=obs.center_channel*1.28e6,
                                               delays=obs.delays)
except:
    logger.error('Error creating primary beams\n')
    sys.exit(1)
    
rX=numpy.real(numpy.conj(respX)*respX)
rY=numpy.real(numpy.conj(respY)*respY)
# make a pseudo-I beam
r=(rX+rY)

# and for the pointing center
# first go from altitude to zenith angle
theta0=numpy.radians((90-obs.elevation))
phi0=numpy.radians(obs.azimuth)
# this is the response for XX and YY
try:
    respX,respY=primary_beam.MWA_Tile_analytic(theta0,phi0,
                                               freq=obs.center_channel*1.28e6,
                                               delays=obs.delays)
except:
    logger.error('Error creating primary beams\n')
    sys.exit(1)
rX=numpy.real(numpy.conj(respX)*respX)
rY=numpy.real(numpy.conj(respY)*respY)
# make a pseudo-I beam
r0=(rX+rY)

coord_pointing=ICRS(ra=obs.RA, dec=obs.Dec, unit=(u.degree, u.degree))
separation=coord.separation(coord_pointing).degree

logger.info('Observation at gpstime=%d, %d MHz, delays=%s' % (obs.observation_number,
                                                              obs.center_channel*1.28,
                                                              obs.delays))
logger.info('Calculating for RA,Dec=%s' % (coord.to_string(precision=1, sep=':')))
print 'Separation: %.2f deg' % separation
print 'Power: %.2f' % (r/r0)




