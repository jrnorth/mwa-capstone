#!/usr/bin/env python
"""
primarybeammap.py --freq=202.24 --beamformer=0,0,0,1,3,3,3,3,6,6,6,6,8,9,9,9 --datetimestring=20110926210616

main task is:
make_primarybeammap()

This is the script interface to the functions and modules defined in MWA_Tools/src/primarybeamap.py

"""
from mwapy import ephem_utils
from mwapy.pb import primary_beam
import sys
import pyfits,numpy,math
import os,time
from optparse import OptionParser
import ephem
import logging
import matplotlib
if not 'matplotlib.backends' in sys.modules:
    matplotlib.use('agg')
import matplotlib.pyplot as pylab
from mwapy.pb.primarybeammap import *
#import primarybeammap

def main():

    usage="Usage: %prog [options]\n"
    usage+="\tCreates an image of the 408 MHz sky (annoted with sources) that includes contours for the MWA primary beam\n"
    usage+="\tThe beam is monochromatic, and is the sum of the XX and YY beams\n"
    usage+="\tThe date/time (UT) and beamformer delays must be specified\n"
    usage+="\tBeamformer delays should be separated by commas\n"
    usage+="\tFrequency is in MHz, or a coarse channel number (can also be comma-separated list)\n"
    usage+="\tDefault is to plot centered on RA=0, but if -r/--racenter, will center on LST\n"
    usage+="\tContours will be plotted at %s of the peak\n" % contourlevels
    usage+="\tExample:\tpython primarybeammap.py -c 98 --beamformer=1,0,0,0,3,3,3,3,6,6,6,6,9,9,9,8 --datetimestring=20110926211840\n\n"
    
    parser = OptionParser(usage=usage)
    parser.add_option('-d','--datetimestring',dest="datetimestring",default=None,
                      help="Compute for <DATETIMESTRING> (YYYYMMDDhhmmss)",
                      metavar="DATETIMESTRING")
    parser.add_option('-c','--channel',dest='channel',default=None,
                      help='Center channel(s) of observation')
    parser.add_option('-f','--frequency',dest='frequency',default=None,
                      help='Center frequency(s) of observation [MHz]')
    parser.add_option('-b','--beamformer',dest='delays',default=None,
                      help='16 beamformer delays separated by commas')
    parser.add_option('-D','--date',dest='date',default=None,
                      help='UT Date')
    parser.add_option('-t','--time',dest='time',default=None,
                      help='UT Time')
    parser.add_option('-g','--gps',dest='gps',default=None,
                      help='GPS time')
    parser.add_option('--title',dest='title',default=None,
                      help='Plot title')
    parser.add_option('-e','--ext',dest='extension',default='png',
                      help='Plot extension [default=%default]')
    parser.add_option('-r','--racenter',action="store_true",dest="center",default=False,
                      help="Center on LST?")
    parser.add_option('-s','--sunline',dest="sunline",default="1",choices=['0','1'],
                      help="Plot sun [default=%default]")
    parser.add_option('--tle',dest='tle',default=None,
                      help='Satellite TLE file')
    parser.add_option('--duration',dest='duration',default=300,type=int,
                      help='Duration for plotting satellite track')

    parser.add_option('-v','--verbose',action="store_true",dest="verbose",default=False,
                      help="Increase verbosity of output")

    (options, args) = parser.parse_args()
    datetimestring=options.datetimestring
    if options.frequency is not None:
        if (',' in options.frequency):
            try:
                frequency=map(float,options.frequency.split(','))
            except ValueError:
                logger.error("Could not parse frequency %s\n" % options.frequency)
                sys.exit(1)
        else:
            try:
                frequency=float(options.frequency)
            except ValueError:
                logger.error("Could not parse frequency %s\n" % options.frequency)
                sys.exit(1)
    else:
        frequency=options.frequency
    if options.channel is not None:
        if (',' in options.channel):
            try:
                channel=map(float,options.channel.split(','))
            except ValueError:
                logger.error("Could not parse channel %s\n" % options.channel)
                sys.exit(1)
        else:
            try:
                channel=float(options.channel)
            except ValueError:
                logger.error("Could not parse channel %s\n" % options.channel)
                sys.exit(1)
    else:
        channel=options.channel
    if options.delays is not None:
        try:
            if (',' in options.delays):
                delays=map(int,options.delays.split(','))
            else:
                delays=16*[int(options.delays)]
        except:
            logger.error("Could not parse beamformer delays %s\n" % options.delays)
            sys.exit(1)
    else:
        delays=options.delays
    extension=options.extension
    verbose=options.verbose
    title=options.title
    center=options.center
    sunline=int(options.sunline)
    datestring=options.date
    timestring=options.time
    gpsstring=options.gps
               
    if (datetimestring is None):
        if (datestring is not None and timestring is not None):
            datetimestring=datestring.replace('-','') + timestring.replace(':','')
    if gpsstring is not None:
        try:
            mjd,ut=ephem_utils.calcUTGPSseconds(int(gpsstring))
        except:
            logger.error('Cannot convert gpsstring %s to a date/time' % gpsstring)
            sys.exit(1)
        yr,mn,dy=ephem_utils.mjd_cal(mjd)
        datetimestring=('%04d%02d%02d' % (yr,mn,dy))+ ephem_utils.dec2sexstring(ut,digits=0,roundseconds=1).replace(':','')
    if (datetimestring is None):
        logger.error("Must supply a date/time\n")
        sys.exit(1)
    if len(datetimestring) != 14:
        logger.error('Format of date/time is YYYYMMDDhhmmss; %s is not valid\n' % datetimestring)
        sys.exit(1)
        
    if (len(delays)<16):
        logger.error("Must supply 1 or 16 delays\n")
        sys.exit(1)
    if (frequency is None):
        if (channel is not None):
            if (isinstance(channel,list)):
                frequency=list(1.28*numpy.array(channel))
            else:
                frequency=1.28*channel
    if frequency is None:
        logger.error("Must supply frequency or channel\n")
        sys.exit(1)

    result=make_primarybeammap(datetimestring, delays, frequency, center, sunline=sunline,
                               extension=extension, title=title,
                               tle=options.tle, duration=options.duration,
                               verbose=verbose)
    if (result is not None):
        print "Wrote %s" % result

if __name__ == "__main__":
    main()
