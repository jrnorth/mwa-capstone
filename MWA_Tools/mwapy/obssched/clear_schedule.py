#!/usr/bin/env python

"""
A utility to define single observations for the MWA
can work either on command line or as a package for inclusion in other routines


"""

import getopt, logging, sys, os

import mwaconfig

from mwapy import dbobj, ephem_utils
from mwapy.ephem_utils import GPSseconds_now
from time import sleep
from obssched.base import schedule, tiles


def show(starttime, stoptime, db=None):
  curs=db.cursor()
  command="select starttime,stoptime,obsname from mwa_setting where starttime >= %s and stoptime <= %s"
  curs.execute(command, (starttime,stoptime))
  deleteobses=curs.fetchall()

  command="select starttime,stoptime,obsname from mwa_setting where stoptime > %s and starttime < %s"
  curs.execute(command, (starttime,starttime))
  endtrunkobses=curs.fetchall()

  command="select starttime,stoptime,obsname from mwa_setting where starttime > %s and starttime < %s and stoptime > %s"
  curs.execute(command, (starttime,stoptime,stoptime))
  pretrunkobses=curs.fetchall()

  db.commit()
  
  if len(deleteobses) == 0 and len(endtrunkobses)==0 and len(pretrunkobses)==0:
    print "No observations scheduled in that time range."
    sys.exit(0)

  if deleteobses:
    print "These obses will be deleted:"
    for obs in deleteobses:
      print "%d --> %d : %s" % (obs[0],obs[1],obs[2])

  if endtrunkobses:
    print "These observations will have their stoptime truncated."
    for obs in endtrunkobses:
      print "%d --> %d : %s" % (obs[0],obs[1],obs[2])

  if pretrunkobses:
    print "These observations will have their starttime moved later."
    for obs in pretrunkobses:
      print "%d --> %d : %s" % (obs[0],obs[1],obs[2])


def main():

    ####################
    # parse input options
    try:
        opts, args = getopt.getopt(sys.argv[1:], 
                                   "h",
                                   ["help",
                                    "starttime=",
                                    "stoptime=",
                                    ])
    except getopt.GetoptError, exc:
        # print help information and exit:
        logging.error(exc.msg + "\n")
        usage()
        sys.exit(2)

    # start and stop times in GPS seconds. Default to starttime of now, but stoptime must be given
    starttimelast = ephem_utils.GPSseconds_next()
    starttime = convert_time('++8',starttimelast)
    stoptime =  0

    ####################
    # go through options
    inputresult=True
    for opt,val in opts:
        if opt in ("-h","--help"):
            usage()
            sys.exit(1)
        elif opt.lower() in ('--start','--starttime'):
            starttime=convert_time(val, starttimelast)
            if starttime < starttimelast:
                logging.error('Starttime %d must be in the future, not the past...' % starttime)
                inputresult = False
        elif opt.lower() in ('--stop','--stoptime'):
            stoptime=convert_time(val, starttime)
        else:
            logging.error("Unknown option: %s" % opt)
            usage()
            inputresult=False

    if (not inputresult):
        # parsing failed
        sys.exit(1)

    if stoptime == 0:
      print "Stoptime not given, are you SURE you want to delete all observations after %d?" % starttime
      ans = raw_input("Delete all future observations? (y/N): ")
      if (not ans) or ans.strip()[0].upper()<>'Y':
        print "Aborting clear_schedule."
        sys.exit()
      else:
        stoptime = sys.maxint -10

    starttime = starttime - (starttime % 8)
    if stoptime % 8:
      stoptime = stoptime + 8 - (stoptime % 8)

    if stoptime <= starttime:
      print "Stoptime must be greater than starttime."
      sys.exit(1)

    # open up database connection
    try:
      db = schedule.getdb()
    except:
      logging.error("Unable to open connection to database")
      sys.exit(1)

    show(starttime, stoptime, db=db)

    print "About to clear schedule from %d to %d."  % (starttime, stoptime)

    ans = raw_input("Proceed? (y/N): ")
    if (not ans) or ans.strip()[0].upper()<>'Y':
      print "Aborting clear_schedule."
      sys.exit()

    curs=db.cursor()
    curs.execute('select clear_schedule(%s,%s);', (starttime,stoptime))                
    db.commit()
    print "Schedule cleared."

    sys.exit(0)

        
######################################################################
def convert_time(newtime, lasttime):
    """
    timeout=convert_time(newtime, lasttime)
    converts the timestring given in newtime to a time in GPSseconds, return as timeout
    lasttime is the last time return, used for increments
    formats for newtime:
     ++dt                 - increments lasttime by dt seconds
     yyyy-mm-dd,hh:mm:ss  - UT date/time
     t                    - GPS seconds
    """
    
    timeout=0
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
    


######################################################################
def usage():

    (xdir,xname)=os.path.split(sys.argv[0])
    print "Usage:  %s [-h/--help] <options>" % xname
    print "options from:"
    print "  --starttime=<starttime> - Observation start time in GPSseconds"
    print "                              or yyyy-mm-dd,hh:mm:ss, or ++<dt>[s/m/h] from now"
    print "  --stoptime=<stoptime>   - Observation stop time as above,"
    print "                              or ++<dt>[s/m/h] from starttime"
    print ""
    print "Default starttime is NOW."
    print "Default stoptime is 0, meaning 'All events from startime onwards.' "
    print ""
    
######################################################################

if __name__=="__main__":
    main()



