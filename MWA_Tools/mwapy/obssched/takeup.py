#!/usr/bin/env python

"""
A utility to define single observations for the MWA
can work either on command line or as a package for inclusion in other routines


"""

import getopt, logging, sys, os

import mwaconfig

from mwapy import dbobj, ephem_utils
from obssched.base import schedule, tiles


def main():

    ####################
    # parse input options
    try:
        opts, args = getopt.getopt(sys.argv[1:], 
                                   "h",
                                   ["help",
                                    "starttime=",
                                    "stoptime=",
                                    "frequency=",
                                    "freq=",
                                    "frequencies=",
                                    "obsname=",
                                    "obsmode=",
                                    "mode=",
                                    "name=",
                                    "nodatabase",
                                    "nodb",
                                    'gain_type=',
                                    'gain_control_type=',
                                    'gain_value=',
                                    'gain_control_value=',
                                    'walsh=',
                                    'walsh_mode=',
                                    ])
    except getopt.GetoptError, exc:
        # print help information and exit:
        logging.error(exc.msg + "\n")
        usage()
        sys.exit(2)

    # start and stop times in GPS seconds. Default to 2 minute observation starting 'now+8s'
    starttimelast = ephem_utils.GPSseconds_next()
    starttime = convert_time('++8',starttimelast)
    stoptime = starttime + 120 
    obsname = ''
    mode = ''
    nodb = False
    tileselection='all_on'
    walsh_mode='OFF'
    gain_control_type='DB_ATTENUATION'
    gain_control_value=10
    (xdir,xname)=os.path.split(sys.argv[0])
    frequencystart=0
    frequencystop=0   #Default to burst mode

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
        elif opt.lower() in ('--frequency','--freq','--frequencies'):
            try:
                if (val.count(':')):
                    # a range
                    [val1,val2]=val.split(':')
                    frequencystart=int(val1)
                    frequencystop=int(val2)
                elif (val.count('-')):
                    # a range
                    [val1,val2]=val.split('-')
                    frequencystart=int(val1)
                    frequencystop=int(val2)                    
                elif (val.count(',')):
                    # center and bandwidth
                    [val1,val2] = map(int,val.split(','))
                    frequencystart = val1 - int(val2/2.0)
                    frequencystop = val1 + int(val2/2.0-0.5)                    
                else:
                    # just a single channel
                    frequencystart=int(val)
                    frequencystop=int(val)
            except:
                logging.error('Unable to parse frequency: %s' % val)
                inputresult=False
        elif opt.lower() in ('--obsname','--name'):
            obsname=val
        elif opt.lower() in ('--mode','--obsmode'):
            mode = val
        elif opt.lower() in ('--walsh','--walsh_mode'):
            if (val.upper() in ('ON','TRUE')):
                walsh_mode='ON'
            elif (val.upper() in ('OFF','FALSE')):
                walsh_mode='OFF'
            else:
                logging.error('Unable to parse walsh mode: %s' % val)
        elif opt.lower() in ('--gain_type','--gain_control_type'):
            if (val.upper() in ('AUTO','DB_ATTENUATION')):
                gain_control_type=val.upper()
            else:
                logging.error('Unrecognized Gain Control Type: %s' % val)
                inputresult=False
        elif opt.lower() in ('--gain_value','--gain_control_value'):
            try:
                gain_control_value=float(val)
            except ValueError:
                logging.error('Unable to parse gain control value: %s' % val)
                inputresult=False
        elif opt.lower() in ('--nodatabase','--nodb'):
            nodb = True
        else:
            logging.error("Unknown option: %s" % opt)
            usage()
            inputresult=False

    if (not inputresult):
        # parsing failed
        sys.exit(1)

    creator = raw_input('Enter Your name: ').strip()

    if (not obsname):
        # if no name supplied, construct one
        obsname = 'Zenith_Freq=%s' % '#'.join(map(str,range(frequencystart,frequencystop+1)))
    print "Observation: ", obsname
    print "  from %d to %d."  % (starttime, stoptime)

    if not mode:
      if frequencystart == frequencystop:
        if frequencystart == 0:
          mode = 'BURST_VSIB'
        else:
          mode = 'SW_COR_VSIB'
      else:
        mode = 'NO_CAPTURE'
        

##################################################
# Schedule the Observation:

    # open up database connection
    try:
      db = schedule.getdb()
    except:
      logging.error("Unable to open connection to database")
      sys.exit(1)

    if not nodb:
      curs=db.cursor()
      curs.execute('select clear_schedule(%s,%s);', (starttime,stoptime))                
      db.commit()

    obs = schedule.MWA_Setting(starttime, db=db)
    obs.stoptime = stoptime
    obs.obsname = obsname
    obs.creator = creator
    obs.mode = mode

    rfs = schedule.RFstream(keyval=(starttime,0), db=db)
    rfs.creator = creator
    rfs.azimuth = 0
    rfs.elevation = 90.0
    rfs.tileset = schedule.Tileset('all_on', db=db)
    rfs.tile_selection = 'all_on'
    rfs.frequencies = range(frequencystart,frequencystop+1)
    rfs.walsh_mode = walsh_mode
    rfs.gain_control_type = gain_control_type
    rfs.gain_control_value = gain_control_value
    obs.rfstreams[0] = rfs

    if not nodb:
      print "Saving new observation."
      errors = obs.save(db=db)
    else:
      print "NOT saving observation."
      errors = obs.check(db=db)
    if errors:
      print "\n".join(map(str,errors))
    
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
    print "Usage:  %s [-h/--help] <main options> <setting options> <other options>" % xname
    print "Main options from:"
    print "\t--starttime=<starttime>   - Observation start time in GPSseconds or yyyy-mm-dd,hh:mm:ss, or ++<dt>[s/m/h] from now"
    print "\t--stoptime=<stoptime>     - Observation stop time as above, or ++<dt>[s/m/h] from starttime"
    print "Setting options from:"        
    print "\t--frequency=<frequency>   - Frequency, either <channel>, <channelstart>:<channelstop>, <centerchannel>,<channelwidth>"
    print "\t--obsname=<obsname>       - Name of observation"
    print "\t--walsh=<walsh_mode>      - Walsh mode [default=OFF]"
    print "\t--gain_control_type=<gain_control_type> - Gain control type (AUTO|DB_ATTENUATION) [default=AUTO]"
    print "\t--gain_control_value=<gain_control_value> - Gain control value"
    print ""
    
######################################################################

if __name__=="__main__":
    main()



