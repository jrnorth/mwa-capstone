#!/usr/bin/env python


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
                                    "inttime=",
                                    "obsname=",
                                    "name=",
                                    "nodatabase",
                                    "nodb",
                                    'gain_type=',
                                    'gain_control_type=',
                                    'gain_value=',
                                    'gain_control_value=',
                                    'singlechannel',
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
    inttime = 8
    obsname = ''
    mode = ''
    nodb = False
    walsh_mode='OFF'
    gain_control_type='DB_ATTENUATION'
    gain_control_value=10
    (xdir,xname)=os.path.split(sys.argv[0])
    singlechannel = False

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
        elif opt.lower() in ('--inttime',):
            try:
              inttime = float(val)
            except:
              logging.error('inttime "%s" must be an integer in seconds.' % val)
              inputresult = False
            if divmod(inttime,8)[1] <> 0:
              logging.error('inttime %d must be a multiple of 8 seconds.' % inttime)
              inputresult = False
        elif opt.lower() in ('--obsname','--name'):
            obsname=val
        elif opt.lower() in ('--singlechannel',):
            singlechannel = True
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

    print "Observation: ", obsname

    if not mode:
      if singlechannel:
        mode = 'SW_COR_VSIB'
      else:
        mode = 'HW_COR_PKTS'

    if singlechannel:
      frlist = []
      for f in range(13,244):
        frlist.append(range(f-12,f+12))
    else:
      frlist = []
      for fl in range(1,218,24):
        frlist.append(range(fl,fl+24))
      frlist.append(range(241,256))


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
      curs.execute('select clear_schedule(%s,%s);', (starttime,starttime+len(frlist)*inttime))                
      db.commit()

    for i in range(len(frlist)):
      obs = schedule.MWA_Setting(starttime+i*inttime, db=db)
      obs.stoptime = starttime+(i+1)*inttime
      if singlechannel:
        obs.obsname = "RFI-scan chan %d" % (frlist[i][12],)
      else:
        obs.obsname = "RFI-scan chan %d-%d" % (frlist[i][0],frlist[i][-1])
      obs.creator = creator
      obs.mode = mode

#      rfs = schedule.RFstream(keyval=(starttime+i*inttime,0), db=db)
#      rfs.creator = creator
#      rfs.azimuth = 0
#      rfs.elevation = 90.0
#      rfs.tileset = schedule.Tileset('rec1', db=db)
#      rfs.tile_selection = 'rec1'
#      rfs.frequencies = [0]
#      rfs.walsh_mode = walsh_mode
#      rfs.gain_control_type = gain_control_type
#      rfs.gain_control_value = gain_control_value
#      obs.rfstreams[0] = rfs

      rfs = schedule.RFstream(keyval=(starttime+i*inttime,0), db=db)
      rfs.creator = creator
      rfs.azimuth = 0
      rfs.elevation = 90.0
      rfs.tileset = schedule.Tileset('all_on', db=db)
      rfs.tile_selection = 'all_on'
      rfs.frequencies = frlist[i]
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
    print "\t--inttime=<stoptime>      - Integration time for each observation in seconds"
    print "\t--singlechannel           - If set, use one channel at a time for software correlator"
    print "\t--obsname=<obsname>       - Name of observation"
    print "\t--walsh=<walsh_mode>      - Walsh mode [default=OFF]"
    print "\t--gain_control_type=<gain_control_type> - Gain control type (AUTO|DB_ATTENUATION) [default=AUTO]"
    print "\t--gain_control_value=<gain_control_value> - Gain control value"
    print ""
    
######################################################################

if __name__=="__main__":
    main()



