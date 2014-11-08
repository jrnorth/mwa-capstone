#!/usr/bin/env python

"""
A utility to define single observations for the MWA
can work either on command line or as a package for inclusion in other routines


$Rev: 4123 $:     Revision of last commit
$Author: cwilliams $:  Author of last commit
$Date: 2011-09-23 13:22:15 +0800 (Fri, 23 Sep 2011) $:    Date of last commit

"""

import logging, sys, os, glob, string, re, urllib, math, time
import traceback, cPickle, pwd, optparse
import numpy

import mwaconfig

import ephem
from mwapy import dbobj, ephem_utils
from mwapy.obssched.base import schedule, obssource, tiles

__version__ = "$Rev: 4123 $"

# open up database connection
try:
    db = schedule.getdb()
except:
    logging.error("Unable to open connection to database")
    sys.exit(1)

# load the source tables
Sources=schedule.getdata_andpickle(obssource.MWA_Source.getdict, 'Sources', db=db)
# and the other tables that were already loaded in the schedule module
Log_Types=schedule.Log_Types
Obs_Modes=schedule.Obs_Modes
Gain_Control_Types=schedule.Gain_Control_Types
Frequency_Types=schedule.Frequency_Types
Grid_Points=schedule.Grid_Points
Tile_List=schedule.Tile_List
Projects=schedule.Projects

######################################################################
class ObsConfig:
######################################################################
    """ A class to contain the info for a single observation
    it bundles together the various classes required to define a MWA_Setting object
    functionality is very simple:

    newobs=ObsConfig(starttime=starttime, stoptime=stoptime)
    newobs.creator=xname
    ...set other attributes...
    snew=newobs.single_observation(db=db, verbose=verbose, usedatabase=usedatabase, force=force, clear=clear)
    """        

    # full list of attributes that can be defined for an observation
    attributes=['starttime','stoptime','creator','obsname', 'projectid', 'rfstream','ra','dec','azimuth','elevation','hex','frequencies','frequency_type','vsib_frequency','tileselection','walsh_mode','gain_control_type','gain_control_value','mode','comment','logtype','unpowered','dipex','ra_phase_center','dec_phase_center']
    

    ######################################################################
    def __init__(self,starttime=None, stoptime=None, creator=None, obsname=None, rfstream=None,
                 ra=None, dec=None, azimuth=None, elevation=None, hex=None, frequencies=None, frequency_type=None,
                 tileselection=None, walsh_mode=None, gain_control_type=None,
                 gain_control_value=None, mode=None, unpowered=None, dipex=None,
                 ra_phase_center=None, dec_phase_center=None, projectid = None):
        """
        can specify all the parameters here, but don't have to
        """
        
        if (starttime and stoptime and stoptime <= starttime):
            logging.error("Stoptime (%f) must be > Startime (%f)" % (stoptime,starttime))
            return None
        self.starttime=starttime
        self.stoptime=stoptime
        # defaults:
        if ( walsh_mode is None):
            self.walsh_mode='OFF'
        if ( gain_control_type is None):            
            self.gain_control_type=repr(Gain_Control_Types[schedule.getDefaultGainType(db=db)])
        if ( gain_control_value is None):
            # do not assign the default value here
            # since we want to allow for changing the type later, and seeing what the resulting
            # new default would be
            self.gain_control_value=None
        if ( ra is None):
            self.ra=None
        if ( dec is None):
            self.dec=None
        if ( ra_phase_center is None):
            self.ra_phase_center=None
        if ( dec_phase_center is None):
            self.dec_phase_center=None
        if ( azimuth is None):
            self.azimuth=None
        if ( elevation is None):
            self.elevation=None
        if ( hex is None):
            self.hex=None
        if ( rfstream is None or rfstream==0):
            self.rfstream=0
        if (mode is None):
            self.mode=repr(Obs_Modes[schedule.getDefaultObsMode(db=db)])
        if (unpowered is None):
            self.unpowered='default'
        if (dipex is None):
            self.dipex='default'
            
        self.projectid = projectid
        
    ######################################################################
    def __setattr__(self, name, value):
        # make sure that whatever attribute we are setting is one of the real possibilities
        if (name in self.attributes):
            self.__dict__[name]=value
        else:
            logging.warning('Cannot set parameter \"%s\" for an observation' % name)

    ######################################################################
    def single_observation(self, db=None, mwa_setting=None, verbose=False, usedatabase=False, force=False, clear=None):
        """
        mwa_setting=single_observation(self, db=None, mwa_setting=None, verbose=False, usedatabase=False, force=False, clear=None)
        enters a single observation into the database
        will create a MWA_Setting object if none is passed, otherwise it modifies the passed one in place
        
        
        """
        
        if (db is None):
            logging.error('Must pass database handle')
            return 0
        if (not self.starttime and self.stoptime):
            logging.error('Must specify starttime and stoptime')
            return 0

        if (not mwa_setting):
            if (not clear):
                # pass starttime, so that it will see if there are any existing records in the database
                mwa_setting=schedule.MWA_Setting(self.starttime, db=db)
            else:
                # we want to start off fresh
                mwa_setting=schedule.MWA_Setting(db=db)
                mwa_setting.starttime=self.starttime
                
        # which type of coordinate are we dealing with
        haveradec=(self.ra is not None and self.dec is not None)
        haveazel=(self.azimuth is not None and self.elevation is not None)
        havehex=(self.hex is not None)
        if (not haveradec and not haveazel and not havehex):
            logging.error('Must specify coordinates')
            return 0

        # write the actual entries into the databases
        mwa_setting.stoptime=self.stoptime
        mwa_setting.creator=self.creator
        mwa_setting.obsname=self.obsname 
        mwa_setting.mode=self.mode
        mwa_setting.unpowered_tile_name=self.unpowered
        mwa_setting.ra_phase_center=self.ra_phase_center
        mwa_setting.dec_phase_center=self.dec_phase_center
        mwa_setting.projectid=self.projectid
            
        if self.comment:
            logent = schedule.MWA_Log(keyval=None,db=db)
            logent.referencetime = self.starttime
            logent.endtime = self.stoptime
            logent.comment = self.comment
            logent.creator = self.creator
            if (self.logtype):
                logent.logtype = self.logtype
            mwa_setting.logs.append(logent)

        logent = schedule.MWA_Log(keyval=None,db=db)
        logent.referencetime = self.starttime
        logent.endtime = self.stoptime
        logent.comment = ' '.join(sys.argv)
        logent.creator = self.creator
        logent.logtype = 5
        mwa_setting.logs.append(logent)

        rfstream=schedule.RFstream(keyval=(mwa_setting.starttime,int(self.rfstream)),db=db)
        if (rfstream.new == False and force == False):
            # this is not a new entry: check about overwriting
            logging.error('A RFstream[%d] with starttime=%d already exists and force==False' % (int(self.rfstream), self.starttime))
            return 0

        if (not haveazel and not havehex):
            rfstream.ra=self.ra
            rfstream.dec=self.dec
        elif (haveazel):
            rfstream.azimuth=self.azimuth
            rfstream.elevation=self.elevation
        else:
            rfstream.hex=self.hex

        if (self.frequency_type is None or self.frequency_type == ''):
            # no frequency_type specified: set it from the mode
            #logging.warning('No frequency_type specified: using default')
            self.frequency_type=schedule.MWA_Obs_Modes.getObsMode(name=mwa_setting.mode,db=db).frequency_type
            rfstream.frequency_type=self.frequency_type
        else:
            if (not schedule.MWA_Obs_Modes.getObsMode(name=mwa_setting.mode,db=db).frequency_type == self.frequency_type):
                logging.warning('Frequency type %s specified, but mode %s implies frequency type %s',
                                self.frequency_type,schedule.MWA_Obs_Modes.getObsMode(name=mwa_setting.mode,db=db),
                                schedule.MWA_Obs_Modes.getObsMode(name=mwa_setting.mode,db=db).frequency_type)
            rfstream.frequency_type=self.frequency_type

        if (self.frequencies is not None and len(self.frequencies)>0):
            rfstream.frequencies=self.frequencies
            if (not Frequency_Types[schedule.MWA_Frequency_Types.getKey(rfstream.frequency_type,db=db)].takes_value):
                logging.error('Cannot specify frequency (%s) with frequency type %s',self.frequencies,self.frequency_type)
                return 0
        else:
            if Frequency_Types[schedule.MWA_Frequency_Types.getKey(rfstream.frequency_type,db=db)].takes_value:
                logging.error('Must specify frequencies')
                return 0
        if (self.vsib_frequency is not None):
            if (not self.vsib_frequency in self.frequencies):
                logging.error('vsib_frequency %d must be in frequencies list %s',self.vsib_frequency,self.frequencies)
                return 0
            rfstream.vsib_frequency=self.vsib_frequency
            if (not Frequency_Types[schedule.MWA_Frequency_Types.getKey(rfstream.frequency_type,db=db)].takes_value):
                logging.error('Cannot specify vsib_frequency (%d) with frequency type %s',self.vsib_frequency,self.frequency_type)
                return 0

        else:
            # set it to the middle value by default
            if (self.frequencies):
                rfstream.vsib_frequency=self.frequencies[len(self.frequencies)/2]
        rfstream.creator=self.creator
        if (not self.tileselection):
            logging.error('Must specify a tile selection')
            return 0
        rfstream.tile_selection=self.tileselection
        if (self.walsh_mode is not None):
            rfstream.walsh_mode=self.walsh_mode
        if (self.gain_control_type is not None):
            rfstream.gain_control_type=self.gain_control_type
        else:
            logging.warning('No gain_control_type specified: using default')
            rfstream.gain_control_type=repr(Gain_Control_Types[schedule.getDefaultGainType(db=db)])
        if Gain_Control_Types[schedule.MWA_Gain_Control_Types.getKey(self.gain_control_type,db=db)].takes_value:
            if (self.gain_control_value is not None and self.gain_control_type is not None):
                rfstream.gain_control_value=self.gain_control_value
            else:
                logging.warning('No gain_control_value specified: using default value of %s'%`Gain_Control_Types[schedule.MWA_Gain_Control_Types.getKey(self.gain_control_type,db=db)].default_value`)
                rfstream.gain_control_value=Gain_Control_Types[schedule.MWA_Gain_Control_Types.getKey(self.gain_control_type,db=db)].default_value

        rfstream.tileset=schedule.Tileset(self.tileselection, db=db) 
        rfstream.dipole_exclusion=self.dipex
        mwa_setting.rfstreams[int(self.rfstream)]=rfstream

        if (verbose):
            print "\t%s" % str(mwa_setting).replace('\n','\n\t')
            for logent in mwa_setting.logs:
                print "\t%s" % str(logent).replace('\n','\n\t')
            print "\t%s" % str(mwa_setting.rfstreams[int(self.rfstream)]).replace('\n','\n\t')    

        if (usedatabase):
            print "Writing record:..."
            if (clear):
                curs=db.cursor()
                curs.execute('select clear_schedule(%s,%s);', (self.starttime,self.stoptime))                
                db.commit()
                
            # see if the mwa_setting has overlapping tile selections
            if (not mwa_setting.tilesetsOK()):
                logging.error('Tile selection invalid: RF streams have overlapping tile selections')
                return None

            errors = mwa_setting.save(ask=0,force=force,verbose=verbose,db=db)
            if errors:
              print "\n".join(map(str,errors))

            # DLK 2012-08-08
            # I think the stuff below is not used anymore
            # else:
            #     # no choice but to make it optional, going to be very difficult to group observations for archiving later on.
            #     if self.projectid is not None:
            #         curs=db.cursor()
            #         curs.execute('insert into mwa_observationproject (project_id, settings_id) values (%s, %s)', (self.project_id, mwa_setting.starttime))                
            #         db.commit()
                
        return mwa_setting

######################################################################

def main():

    logging.basicConfig(format='%(levelname)s: %(message)s')    

    ####################
    # parse input options
    usage="usage: %prog [options]"
    usage+="Calculates a list of positions between STARTTIME and STOPTIME for a source"
    usage+="\nSTARTTIME and STOPTIME must be specified, along with FREQUENCY and a target (via SOURCE or coordinates)"
    
    usage+="\nExample: %prog --starttime=++0 --stoptime=++32 --ut --usegrid= --source=SMC --freq=121,24"
    parser=optparse.OptionParser(usage=usage, version="%prog " + __version__)


    ####################
    # default values
    # when dealing with a moving source, what is the distance in arcsec
    # to let the source move before we recalculate the position
    maxshift=60
    # when dealing with a source in (RA,Dec) but also --useazel
    # how often do we recalculate (in sec)
    shifttime=296
    # are we specifying a position in (Az,El)?
    haveazel=False
    # regardless of the input, do we output in (RA,Dec) (default)
    # or (Az,El)
    useazel=False
    # should we use Hex coordinates?
    usehex=False
    # this is only used when calculating when sources satisfy constraints
    # or when they move    
    dt=8
    nextstarttime=False
    # minimum altitude in degrees for a warning
    minaltitude=10
    # minimum altitude in degrees for an error
    horizon=0
    # minimum distance from Sun
    minsundistance=-1
    # minimum distance from Jupiter
    minjupiterdistance=-1
    
    projectid = None
    tileselection='all_on'
    walsh_mode='OFF'
    # the observing mode
    mode=None
    (xdir,xname)=os.path.split(sys.argv[0])
    unpowered='default'
    dipex='default'
    default_projectid='C001'

    pointingparser=optparse.OptionGroup(parser, "Pointing options",
                                        "One must be specified: "
                                        "SOURCE, (RA,DEC), (ALT,AZ), (GALL,GALB), HEX, TLEFILE")
    coordadjustparser=optparse.OptionGroup(parser, "Coordinate adjusting options")
    rfstreamparser=optparse.OptionGroup(parser, "RF Stream settings"
                                        "At least the FREQUENCY must be specified")
    optionparser=optparse.OptionGroup(parser, "General options")
    sourcesparser=optparse.OptionGroup(parser, "Use without a sourcename or position to see which of the known sources are visible at a given time [defaults=now]",
                                       "Known sources: %s" % (", ".join(sorted(Sources.keys()))))



    # starttime and stoptime in GPS seconds
    parser.add_option("--starttime",dest="starttime",default=0,
                      help="Observation start time in GPSseconds or yyyy-mm-dd,hh:mm:ss, or ++<dt>[s/m/h] from now\nif <starttime>=\'next\', then it will search though the schedule for the next gap big enough to accomodate the requested observation.  REQUIRED")
    parser.add_option("--stoptime",dest="stoptime",default=0,
                      help="Observation stop time as above, or ++DT[s/m/h] from starttime. REQUIRED")
    parser.add_option("--obsname","--name", dest="obsname", default='',
                      help="Name of observation")
    parser.add_option("--logtype", dest="logtype",default=None,type="choice",
                      choices=[None] + [str(f) for f in Log_Types.keys()] + [repr(x) for x in Log_Types.itervalues()],
                      help="Either number or name of log type")
    parser.add_option("--comment",default='',dest="comment",
                      help="Text comment for observation")
    parser.add_option("--creator",default=None, dest="creator",
                      help="Default is <user>, but required if <user> is mwa or root")
    parser.add_option("--project","--projectid",default=default_projectid, dest="projectid",
                      choices=[str(f) for f in Projects.keys()],
                      help="Project identifier (%s) [default=%s]" % (Projects,default_projectid))
    parser.add_option("--mode","--obsmode",dest="mode",default=None,type="choice",
                      choices=[str(f) for f in Obs_Modes.keys()] + [repr(x) for x in Obs_Modes.itervalues()],
                      help="Observing mode (%s) [default=%s]" % (Obs_Modes,repr(Obs_Modes[schedule.getDefaultObsMode(db=db)])))


    pointingparser.add_option("--source",dest="sourcename",default=None,
                      help="Name of the source to track (specify no source to get full info)")
    pointingparser.add_option("--tlefile",default=None,dest="tle_filename",
                      help="Read in satellite two-line elements, either specified by local file or URL (see http://celestrak.com/NORAD/elements/)")
    pointingparser.add_option("--ra",default=None,action="callback",callback=position_callback,type='string',
                      help="Source to track by RA,Dec (hh:mm:ss or decimal degrees)")
    pointingparser.add_option("--dec",default=None,action="callback",callback=position_callback,type='string',
                      help="Source to track by RA,Dec (dd:mm:ss or decimal degrees)")
    pointingparser.add_option("--gall",default=None,action="callback",callback=position_callback,type='string',
                      help="Source to track by Galactic l,b (dd:mm:ss or decimal degrees)")
    pointingparser.add_option("--galb",default=None,action="callback",callback=position_callback,type='string',
                      help="Source to track by Galactic l,b (dd:mm:ss or decimal degrees)")
    pointingparser.add_option("--azimuth",dest='az',default=None,action="callback",callback=position_callback,
                      type='string',
                      help="Source to track by Az,El (dd:mm:ss or decimal degrees)")
    pointingparser.add_option("--elevation","--altitude",dest='el',default=None,action="callback",
                      callback=position_callback,type='string',
                      help="Source to track by Az,El (dd:mm:ss or decimal degrees)")
    pointingparser.add_option("--hex",default=None,dest="hex",type=str,
                      help="Source to track by hex delay settings")
    pointingparser.add_option("--calibration",dest='calibration',default=False, action="store_true",
                              help="Does the observation contain a calibrator?")
    pointingparser.add_option("--calibrator","--calibrators",dest='calibrators',default='', 
                              help="Name(s) of the calibrator(s)")
    


    # regardless of the input, do we output in (RA,Dec) (default)
    # or (Az,El)
    #coordadjustparser.add_option("--useazel","--usealtaz",default=useazel,type=str,dest="useazel",
    #                             action="callback",callback=bool_callback,                                 
    #                             help="Do calculations in Az,El? [if no --shifttime supplied, uses %ds]" % shifttime)
    coordadjustparser.add_option("--useazel","--usealtaz",default=False, action="store_true",
                                 help="Do calculations in Az,El? [if no --shifttime supplied, uses %ds]" % shifttime)
    # should (Az,El) positions stick to a grid
    # if so, which grid?
    coordadjustparser.add_option("--grid","--usegrid",default=None,dest="usegrid",type='choice',
                                 choices=[None,'','all'] + list(set([x.name for x in Grid_Points])),
                      help="Use the gridded (Az,El) positions?  If so, can specify grid name")
    # should we restrict the possible grid positions at all?
    coordadjustparser.add_option("--maxgridsigma",default=None,type="float",
                      help="Grid positions must have sigma <= MAXGRIDSIGMA")
    # this is only used when calculating when sources satisfy constraints
    # or when they move    
    coordadjustparser.add_option("--dt",default=dt,type="int",
                      help="Sampling time in sec for moving [default=%default]")
    # when dealing with a moving source, what is the distance in arcsec
    # to let the source move before we recalculate the position
    coordadjustparser.add_option("--move",default=maxshift,type="float",dest="maxshift",
                      help="New position when body has moved by > MAXSHIFT arcsec [default=%default]")
    # when dealing with a source in (RA,Dec) but also --useazel
    # how often do we recalculate (in sec)
    coordadjustparser.add_option("--shifttime",default=shifttime,type="int",
                      help="Time interval (multiple of 8s) on which to recalculate/shift (Az,El) position [default=%default s]")
    coordadjustparser.add_option("--minaltitude","--minelevation", default=minaltitude, type='float', dest='minaltitude',
                      help='Minimum altitude in degrees to be considered good (otherwise issues warning) [default=%default]')
    coordadjustparser.add_option("--horizon",default=horizon, type='float', dest='horizon',
                      help="Minimum altitude in degrees (issues error) [default=%default]")
    coordadjustparser.add_option("--minsundistance", default=minsundistance, type='float', dest='minsundistance',
                      help="Minimum distance from Sun in degrees [default=%default]")
    coordadjustparser.add_option("--minjupiterdistance", default=minjupiterdistance, type='float', dest='minjupiterdistance',
                      help="Minimum distance from Jupiter in degrees [default=%default]")
    # should we adjust the times to fit altitude/Sun/Jupiter constraints?
    coordadjustparser.add_option("--adjusttimes",dest='adjusttimes',default=False, action="store_true",
                      help="Should we adjust the start/stop times to make sure the source is above <minaltitude> and far enough away from Sun/Jupiter? [default=%default]")
    coordadjustparser.add_option("--exactpositions",dest="useaveragepositions", default=True,
                                 action="store_false",
                                 help="Use the exact position at <starttime> instead of the average for the interval?")


    rfstreamparser.add_option("--rfstream",default=0,type="int",
                      help="RF stream number [default=%default]")
    rfstreamparser.add_option("--freq","--frequencies","--frequency",dest="frequencies",type="string",
                      default=[],action="callback",callback=freqs_callback,
                      help="Frequency, some of <channel>, <channelstart>:<channelstop>:[<increment>], <centerchannel>,<channelwidth>,[<increment>], separated by ; (channels are 1.28 MHz coarse channel numbers).  REQUIRED")
    rfstreamparser.add_option("--freq_type","--frequency_type","--freq_mode","--frequency_mode",dest="frequency_type",
                      default='',type="choice",
                      choices=[''] + [str(f) for f in Frequency_Types.keys()] + [repr(x) for x in Frequency_Types.itervalues()],
                      help="Frequency type (%s), in general defined by --mode [default=%s]" % (Frequency_Types,repr(Frequency_Types[schedule.getDefaultFrequencyType(db=db)]))
                      )

    rfstreamparser.add_option("--vsib_frequency", type='int', dest='vsib_frequency', default=None,
                      help="VSIB Frequency, must be one of the channels specified for --frequency [default=<center channel>]")
    rfstreamparser.add_option("--tile", default=tileselection, dest='tileselection',
                      help="Tile selection name")
    rfstreamparser.add_option("--walsh_mode",dest="walsh_mode",default=walsh_mode,type="choice",
                      choices=["ON","TRUE","OFF","FALSE"],
                      help="Walsh mode [default=OFF]")
    rfstreamparser.add_option("--gain_type","--gain_control_type", dest="gain_control_type",
                      default=repr(Gain_Control_Types[schedule.getDefaultGainType(db=db)]), 
                      type="choice",
                      choices=[str(f) for f in Gain_Control_Types.keys()] + [repr(x) for x in Gain_Control_Types.itervalues()],
                      help="Gain control type (%s) [default=%s]" % (Gain_Control_Types,repr(Gain_Control_Types[schedule.getDefaultGainType(db=db)])))
    rfstreamparser.add_option("--gain_value","--gain_control_value", dest="gain_control_value",
                      default=None, type="float",
                      help="Gain control value")
    rfstreamparser.add_option("--unpowered", default=unpowered, dest='unpowered',
                      help='??')
    rfstreamparser.add_option("--dipex", default=dipex, dest='dipex',
                      help='??')

    optionparser.add_option("-v","--verbose",dest="verbose",default=False,action="store_true",
                      help="More verbose output?")
    optionparser.add_option("-q","--quiet",dest="verbose",default=False,action="store_false",
                      help="Less verbose output?")
    # only print GPS times, or also print UT?
    optionparser.add_option("--ut",default=0,dest="printUT",action="store_true",
                      help="Print out UT as well as GPStime?")
    optionparser.add_option("--force",dest='force', default=False, action="store_true",
                      help="Force overwrite of an existing entry?")
    optionparser.add_option("--clear",dest='clear', default=False, action="store_true",
                      help="Force clearing of entire block?")
    optionparser.add_option("--nodb", "--nodatabase", dest="usedatabase", default=True, action="store_false",
                      help="Do not actually write to the database")
    optionparser.add_option("--refresh", dest="refresh", default=False, action="store_true",
                            help="Refresh the local cached copies of the database tables")
    

    parser.add_option_group(pointingparser)
    parser.add_option_group(coordadjustparser)
    parser.add_option_group(rfstreamparser)
    parser.add_option_group(optionparser)
    parser.add_option_group(sourcesparser)

    starttimelast=ephem_utils.GPSseconds_next()
    nextstarttime=False
                      
    (options,args)=parser.parse_args()

    if options.refresh:
        logging.warning('Refreshing cached database tables from remote database.  This might take a minute...')
        schedule.Log_Types=schedule.getdata_andpickle(schedule.MWA_Log_Types.getdict, 'Log_Types',
                                                      timedifference=0, db=db)
        schedule.Obs_Modes=schedule.getdata_andpickle(schedule.MWA_Obs_Modes.getdict, 'Obs_Modes',
                                                      timedifference=0, db=db)
        schedule.Gain_Control_Types=schedule.getdata_andpickle(schedule.MWA_Gain_Control_Types.getdict,
                                                               'Gain_Control_Types', timedifference=0, db=db)
        schedule.Frequency_Types=schedule.getdata_andpickle(schedule.MWA_Frequency_Types.getdict,
                                                            'Frequency_Types', timedifference=0, db=db)
        schedule.Grid_Points=schedule.getdata_andpickle(schedule.MWA_Grid_Points.getall, 'Grid_Points',
                                                        timedifference=0, db=db)
        schedule.Tile_List=schedule.getdata_andpickle(schedule.Tileset.getall, 'Tile_List',
                                                      timedifference=0, db=db)
        schedule.Projects=schedule.getdata_andpickle(schedule.MWA_Project.getdict, 'Projects',
                                                     timedifference=0, db=db)


    # deal with remaining parsing needs
    if (options.sourcename is not None and len(options.sourcename)==0):
        # display full source table info
        print "Available Sources:"
        for s in sorted(Sources.keys()):
            print "\t%s" % Sources[s]
        sys.exit(1)
    if options.starttime>0:
        options.starttime=convert_time(options.starttime, starttimelast)        
    if (isinstance(options.starttime,str) and options.starttime=='next'):
        # this means we need to look for the next gap
        nextstarttime=True
    if options.stoptime>0:
        options.stoptime=convert_time(options.stoptime, options.starttime)
    if (nextstarttime):
        # we need to search for a gap
        options.starttime=get_next_starttime(db=db,observationlength=options.stoptime-options.starttime)
        options.stoptime=convert_time(options.stoptime, options.starttime)
    if (options.usegrid is not None and (len(options.usegrid)==0 or options.usegrid=='all')):
        options.usegrid=True
    if (options.usegrid is not None):
        options.useazel=True
    if (options.frequency_type not in [repr(x) for x in Frequency_Types.itervalues()] and len(options.frequency_type)>0):
        options.frequency_type=repr(Frequency_Types[int(options.frequency_type)])
    if (options.logtype not in [repr(x) for x in Log_Types.itervalues()] and options.logtype is not None):
        options.logtype=repr(Log_Types[int(options.logtype)])
    if (options.gain_control_type not in [repr(x) for x in Gain_Control_Types.itervalues()] and len(options.gain_control_type)>0):
        options.gain_control_type=repr(Gain_Control_Types[int(options.gain_control_type)])
    if (options.walsh_mode == 'FALSE'):
        options.walsh_mode='OFF'
    if (options.walsh_mode == 'TRUE'):
        options.walsh_mode='ON'
    if (options.mode not in [repr(x) for x in Obs_Modes.itervalues()] and options.mode is not None):
        options.mode=repr(Obs_Modes[int(options.mode)])
    if (options.clear):
        options.force=True


# Here is the way using the different coordinate types
# and flags
# 
#     Coordinate given | shifttime | useazel | Behavior
#     --------------------------------------------------
#     (RA,Dec)	       | 0(default)| 296(def)| uses (RA,Dec)
#     (RA,Dec)         | 296(def)  | 1       | assumes shifttime=296, (Az,El) every shifttime sec
#     (RA,Dec)         | >0        | 296(def)| (RA,Dec) every shifttime sec
#     (RA,Dec)         | >0        | 1       | (Az,El) every shifttime sec
#     source(fixed)    | 0(default)| 296(def)| uses (RA,Dec)
#     source(fixed)    | 296(def)  | 1       | assumes shifttime=296, (Az,El) every shifttime sec
#     source(fixed)    | >0        | 296(def)| (RA,Dec) every shifttime sec
#     source(fixed)    | >0        | 1       | (Az,El) every shifttime sec
#     source(moving)   | 0(default)| 296(def)| (RA,Dec), moves
#     source(moving)   | >0	   | 296(def)| error
#     source(moving)   | 0	   | 1       | assumes shifttime=296, (Az,El), every shifttime sec
#     source(moving)   | >0	   | 1       | (Az,El), every shifttime sec
#     (Az,El)	       | 296(def)  | 296(def)| uses (Az,El)
#     (Az,El)	       | 296(def)  | 1       | uses (Az,El)
#     (Az,El)	       | >0        | 296(def)| (Az,El) every shifttime sec
#     (Az,El)	       | >0        | 1       | (Az,El) every shifttime sec
#     hex              | 296(def)  | 296(def)| uses hex
#     hex              | >0        | 296(def)| uses hex every shifttime sec
#     hex              | 296(def)  | 1       | warning, uses hex
#     hex              | >0        | 1       | warning, uses hex every shifttime sec
    

    ####################
    # check values of input options
    # first, figure out what the coordinate system is
    havelb=False
    haveazel=False
    usehex=False
    #useazel=options.useazel
    if ((options.gall is not None and options.galb is not None)):
        if ((options.ra is None and options.dec is None)):
            [options.ra,options.dec]=ephem_utils.lbtoad(options.gall/ephem_utils.DEG_IN_RADIAN,options.galb/ephem_utils.DEG_IN_RADIAN)
            options.ra*=ephem_utils.DEG_IN_RADIAN
            options.dec*=ephem_utils.DEG_IN_RADIAN
            havelb=True
        else:
            logging.error('Cannot specify both (l,b)=(%f,%f) and (RA,Dec)=(%f,%f)' % (options.gall,options.galb,options.ra,options.dec))
            sys.exit(1)
    if (options.az is not None and options.el is not None):
        haveazel=True
        options.useazel=True
    if (options.hex is not None):
        usehex=True

    # if we are not specifying an (Az,El) position, but simply want to use
    # the (Az,El) of a known source, we need to give it a shifttime
    # if we are not specifying an (Az,El) position, but simply want to use
    # the (Az,El) of a known source, we need to give it a shifttime
    if (not haveazel and not usehex and options.useazel and options.shifttime == 0):
        logging.warning('No shifttime specified; using %ds' % shifttime)
        options.shifttime=shifttime
        
    # initialise the source list
    SatelliteList={}

    # get satellite names, if supplied
    if (options.tle_filename is not None):
        l0=len(SatelliteList)
        try:
            if (not (options.tle_filename.startswith('http') or options.tle_filename.startswith('ftp'))):
                tle_file=open(options.tle_filename,'r')
            else:
                tle_file=urllib.urlopen(options.tle_filename)
            lines=tle_file.readlines()
            tle_file.close()
            # get rid of comments
            lines=[l for l in lines if not l.startswith('#')]
            # and blank lines
            lines=[l for l in lines if len(l)>0]
            lines=[l for l in lines if not l.isspace()]
            # code from D. Mitchell, 2008-04-30
            for lineIndex in range(0, len(lines), 3):  # get 0, 3, 6, ...
                sat_name = string.rstrip(lines[lineIndex])
                line1    = lines[lineIndex+1]
                line2    = lines[lineIndex+2]

                # Do a quick sanity check (I think readtle checks as well).
                array1 = string.split(line1, ' ')
                array2 = string.split(line2, ' ')
                if int(array1[0])!=1 or int(array2[0])!=2:
                    logging.warn("# Error while reading line ", lineIndex, " of TLE file:\n", sat_name, "\n", line1, line2)
                else:
                    # append a source to the list for this satellite
                    name=re.sub(r'\[.\]','',sat_name).rstrip()
                    SatelliteList[name]=ephem.readtle(sat_name, line1, line2) 
                    #sat_list.append( ephem.readtle(sat_name, line1, line2) )
            print "# Read %d satellites from file: %s" % (len(SatelliteList)-l0,options.tle_filename)
        except IOError:
            logging.warn('# Cannot open file %s for reading.' % options.tle_filename)

    ####################
    # make sure we have either a source name or a position
    result=True
    havesourcename=(options.sourcename and (Sources.has_key(options.sourcename) or (SatelliteList.has_key(options.sourcename))))
    haveradec=(options.ra is not None and options.dec is not None)
    haveazel=(options.az is not None and options.el is not None)
    if (not options.sourcename and not haveradec and not haveazel and not usehex):
        logging.error("Must specify a source or a position")
        logging.error("Known sources: %s" % (",".join(sorted(Sources.keys()))))
        if (len(SatelliteList)>0):
            logging.error("Known satellites: %s" % (", ".join(SatelliteList.keys())))

        whatisup(Sources, options.starttime, options.horizon, options.minsundistance, options.minjupiterdistance)
        if (len(SatelliteList)>0):
            whatisup(SatelliteList, options.starttime, options.horizon, options.minsundistance, options.minjupiterdistance)            
        result=False
    # make sure that if we have no position, the source name is valid
    if (not (havesourcename or haveradec or haveazel or usehex)):
        logging.error("Unknown source specified: %s" % options.sourcename)
        logging.error("Known sources: %s" % (",".join(sorted(Sources.keys()))))
        if (len(SatelliteList)>0):
            logging.error("Known satellites: %s" % (", ".join(SatelliteList.keys())))
        result=False
    # make sure we only have one position pair or source name
    if (havesourcename is None):
        havesourcename=False
    if (havesourcename + haveradec + haveazel + usehex > 1):
        logging.error('Can only specify one of sourcename, RA/Dec, Az/El, hex')
        result=False

    # make sure tile selection is present in database
    tilenames=[tile.name for tile in Tile_List]
    if (not options.tileselection in tilenames):
        try:
            tileselectionout = schedule.makeTileset(db=db, tilespec=options.tileselection)
        except:
            logging.error('Tile selection %s not present in database' % options.tileselection)
            logging.error('And unable to create new tile selection')
            logging.error('Existing tile selection entries: %s' % (", ".join(tilenames)))
            result=False
        if (not tileselectionout.name in tilenames):
            logging.warning('Creating new tile selection: %s' % tileselectionout)
            errors = tileselectionout.save(force=force, commit=0, verbose=verbose, db=db)
            if errors:
              print "\n".join(map(str,errors))
        options.tileselection=tileselectionout.name
        
    result*=checktimes(options.starttime,options.stoptime)
    if (options.hex is not None):
        result*=checkhex(options.hex)
    if (not result):
        sys.exit(1)

    # make sure that the time to shift the (Az,El) is a multiple of 8s
    # and that it is specified with --useazel
    if (options.shifttime):
        # DLK: new changes to allow generic use of shifttime        
        if (int(options.shifttime)/8 != float(options.shifttime)/8.0 or options.shifttime<0):
            logging.error('Shifttime %d is not a multiple of 8' % options.shifttime)
            sys.exit(1)    

    # is the source moving?
    movingsource=False
    if (SatelliteList.has_key(options.sourcename) or (Sources.has_key(options.sourcename) and Sources[options.sourcename].moving)):
        if (Sources.has_key(options.sourcename)):
            try:
                source=ephem.__dict__[options.sourcename]()
            except KeyError:
                logging.error('Moving source %s not present in ephemeris database' % options.sourcename)
                sys.exit(1)
        else:
            source=SatelliteList[options.sourcename]
        movingsource=True
        if (options.shifttime>0 and not options.useazel):
            logging.error('Using shifttime>0 and useazel=0 on a moving source is not possible')
            sys.exit(1)
    else:
        # Not a moving source
        if (options.useazel and (havesourcename or haveradec) and options.shifttime==0):
            logging.warn('Using Az/El with shifttime=0 on fixed source is not possible.  Using RA/Dec...')
            options.useazel=False
        if (options.useazel and (usehex)):
            logging.warn('Using Az/El with hex position is not possible.  Using hex...')
            options.useazel=False
        if (options.sourcename is not None):
            source=Sources[options.sourcename]
        else:
            source=obssource.MWA_Source(db=db)
            if (usehex):
                source.name="Hex%s" % (options.hex)
            else:
                if (not havelb and not haveazel):
                    source.name='RADec%03.4f,%02.4f' % (options.ra,options.dec)
                elif (havelb):
                    source.name='lb%03.4f,%02.4f' % (options.gall,options.galb)
                elif (haveazel):
                    source.name='AzEl%03.4f,%02.4f' % (options.az,options.el)
                if (not haveazel):
                    source.ra=options.ra
                    source.dec=options.dec
                else:
                    source.azimuth=options.az
                    source.elevation=options.el
            source.sourceclass='Unknown'
            source.moving=False
            
    [mjdstart,utstart]=ephem_utils.calcUTGPSseconds(options.starttime)
    [yrstart,mnstart,dystart]=ephem_utils.mjd_cal(mjdstart)
    timestart=ephem_utils.dec2sexstring(utstart,digits=0,roundseconds=1)
    [mjdstop,utstop]=ephem_utils.calcUTGPSseconds(options.stoptime)
    [yrstop,mnstop,dystop]=ephem_utils.mjd_cal(mjdstop)
    timestop=ephem_utils.dec2sexstring(utstop,digits=0,roundseconds=1)
    mwa=ephem_utils.Obs[ephem_utils.obscode['MWA']]
    startTime=ephem_utils.Time(mwa)
    startTime.init(mjdstart, utstart, islt=0)
    stopTime=ephem_utils.Time(mwa)
    stopTime.init(mjdstop, utstop, islt=0)

    if (not options.adjusttimes or (haveazel or usehex)):
        # take the times as given - do not adjust
        # this also applies if we are given an Az/El or Hex coordinate
        # make sure it's above the horizon
        if (not haveazel and not usehex):
            if (not movingsource):
                #[alt,az]=ephem_utils.pyephem_altaz(source.ra/15,source.dec,mwa.lat,mwa.long,mjdstart+utstart/24.0)
                az,alt=ephem_utils.radec2azel(source.ra, source.dec, options.starttime)
            else:
                observer=ephem.Observer()
                # make sure no refraction is included
                observer.pressure=0
                observer.long=mwa.long/ephem_utils.DEG_IN_RADIAN
                observer.lat=mwa.lat/ephem_utils.DEG_IN_RADIAN
                observer.elevation=mwa.elev
                observer.date='%d/%d/%d %s' % (yrstart,mnstart,dystart,ephem_utils.dec2sexstring(utstart))
                source.compute(observer)
                alt=source.alt*ephem_utils.DEG_IN_RADIAN
            if (alt < options.minaltitude):
                logging.warning('Source %s below warning limit (%d degrees) at start: altitude=%.1d degrees' % (source.name, options.minaltitude, alt))
            if (alt < options.horizon):
                logging.error('Source %s below horizon (%d degrees) at start: altitude=%.1d degrees' % (source.name, options.horizon, alt))
                sys.exit(1)
            if (not movingsource):
                #[alt,az]=ephem_utils.pyephem_altaz(source.ra/15,source.dec,mwa.lat,mwa.long,mjdstop+utstop/24.0)
                az,alt=ephem_utils.radec2azel(source.ra, source.dec, options.stoptime)
            else:
                observer.date='%d/%d/%d %s' % (yrstop,mnstop,dystop,ephem_utils.dec2sexstring(utstop))
                source.compute(observer)
                alt=source.alt*ephem_utils.DEG_IN_RADIAN
  
            if (alt < options.minaltitude):
                logging.warning('Source %s below warning limit (%d degrees) at stop: altitude=%.1d degrees' % (source.name, options.minaltitude, alt))
            if (alt < options.horizon):
                logging.error('Source %s below horizon (%d degrees) at stop: altitude=%.1d degrees' % (source.name, options.horizon, alt))
                sys.exit(1)
        elif (haveazel):
            if (options.el < options.minaltitude):
                logging.warning('Source %s below warning limit (%d degrees): altitude=%.1d degrees' % (source.name, options.minaltitude, el))
            if (options.el < options.horizon):
                logging.error('Source %s below horizon (%d degrees): altitude=%.1d degrees' % (source.name, options.horizon, el))
                sys.exit(1)
                            
        try:
            # make sure it's far enough away from Jupiter and the Sun
            if (movingsource):
                sundistance=sourcedistance(Sources[options.sourcename],Sources['Sun'],options.starttime)
            else:
                sundistance=sourcedistance(source,Sources['Sun'],options.starttime)
            if (sundistance < options.minsundistance):
                logging.warning("Source %s is too close to Sun at start: %d degrees away" % (source.name,sundistance))
            if (movingsource):
                jupiterdistance=sourcedistance(Sources[options.sourcename],Sources['Jupiter'],options.starttime)
            else:
                jupiterdistance=sourcedistance(source,Sources['Jupiter'],options.starttime)
            if (jupiterdistance < options.minjupiterdistance):
                logging.warning("Source %s is too close to Jupiter at start: %d degrees away" % (source.name,jupiterdistance))
            if (movingsource):
                sundistance=sourcedistance(Sources[options.sourcename],Sources['Sun'],options.stoptime)
            else:
                sundistance=sourcedistance(source,Sources['Sun'],options.stoptime)
            if (sundistance < options.minsundistance):
                logging.warning("Source %s is too close to Sun at stop: %d degrees away" % (source.name,sundistance))
            if (movingsource):
                jupiterdistance=sourcedistance(Sources[options.sourcename],Sources['Jupiter'],options.stoptime)
            else:
                jupiterdistance=sourcedistance(source,Sources['Jupiter'],options.stoptime)
            if (jupiterdistance < options.minjupiterdistance):
                logging.warning("Source %s is too close to Jupiter at stop: %d degrees away" % (source.name,jupiterdistance))
        except (TypeError,AttributeError):
            logging.warning('Unable to check Sun and Jupiter distances for Source %s' % (source.name))

    else:
        # We have celestial coords
        # adjust the times to fit the time constraints
        [newstarttime,newstoptime]=adjusttime(source, options.starttime, options.stoptime,
                                              options.minaltitude, options.minsundistance,
                                              options.minjupiterdistance,increment=options.dt)

        if (newstarttime==0 and newstoptime==0):
            s='altitude'
            if (options.minsundistance > 0):
                s+=',Sun'
            if (options.minjupiterdistance > 0):
                s+=',Jupiter'
            logging.error('No valid times found that satisfy %s constraints' % s)
            sys.exit(1)
        if (newstarttime != options.starttime):
            startchange=newstarttime-options.starttime
            options.starttime=newstarttime
            [mjdstart,utstart]=ephem_utils.calcUTGPSseconds(options.starttime)
            [yrstart,mnstart,dystart]=ephem_utils.mjd_cal(mjdstart)
            timestart=ephem_utils.dec2sexstring(utstart,digits=0,roundseconds=1)
            startTime.init(mjdstart, utstart, islt=0)
            logging.warning('Start time adjusted to:  %d (%04d-%02d-%02d,%s UT, %s LMST, MJD %d); change=%d sec' %
                            (options.starttime, yrstart, mnstart, dystart, timestart,
                             ephem_utils.dec2sexstring(startTime.LST,digits=0,roundseconds=1), mjdstart,startchange))
        if (newstoptime != options.stoptime):
            stopchange=options.stoptime-newstoptime
            stoptime=newstoptime
            [mjdstop,utstop]=ephem_utils.calcUTGPSseconds(options.stoptime)
            [yrstop,mnstop,dystop]=ephem_utils.mjd_cal(mjdstop)
            timestop=ephem_utils.dec2sexstring(utstop,digits=0,roundseconds=1)
            stopTime.init(mjdstop, utstop, islt=0)
            logging.warning('Stop time adjusted to:  %d (%04d-%02d-%02d,%s UT, %s LMST, MJD %d); change=%d sec' %
                            (options.stoptime, yrstop, mnstop, dystop, timestop,
                             ephem_utils.dec2sexstring(stopTime.LST,digits=0,roundseconds=1), mjdstop,stopchange))
    # figure out what the source name should be
    # if it's supplied as a Source, or just coordinates
    if (isinstance(source,obssource.MWA_Source)):
        if (not haveazel and not usehex):
            print "# Result for %s: (%s, %s)" % (source.name,ephem_utils.dec2sexstring(source.ra/15),
                                                 ephem_utils.dec2sexstring(source.dec,includesign=1))
        elif (haveazel):
            print "# Result for %s: (%s, %s)" % (source.name,ephem_utils.dec2sexstring(source.azimuth),
                                                 ephem_utils.dec2sexstring(source.elevation))
        else:
            print "# Result for %s: (%s)" % (source.name,hex)
    else:
        print "# Result for %s" % (source.name)

    # print information about time of observation
    # print information about time of observation
    if (options.printUT):
        print "# Observation from %d (%04d-%02d-%02d,%s UT, %s LMST, MJD %d) to %d (%04d-%02d-%02d,%s UT, %s LMST, MJD %d)" % (
            options.starttime, yrstart, mnstart, dystart, timestart,
            ephem_utils.dec2sexstring(startTime.LST,digits=0,roundseconds=1),
            mjdstart, options.stoptime, yrstop, mnstop, dystop, timestop,
            ephem_utils.dec2sexstring(stopTime.LST,digits=0,roundseconds=1), mjdstop)
    else:
        print "# Observation from %d to %d" % (options.starttime, options.stoptime)

    # fill the arrays T[],X[],Y[]
    # with the times and coordinates to observe
    # also save the desired phase center
    ra_phase_center=[]
    dec_phase_center=[]

    # position is fixed
    # we only need one entry
    if (isinstance(source,obssource.MWA_Source) and not options.shifttime):
        T=[options.starttime]
        if (not haveazel and not usehex):            
            X=[source.ra]
            Y=[source.dec]
            ra_phase_center=[source.ra]
            dec_phase_center=[source.dec]
        elif (haveazel):
            X=[options.az]
            Y=[options.el]
        else:
            X=[options.hex]
            Y=[options.hex]
    # a fixed source but we are calculating multiple positions
    elif (options.shifttime>0):
        if (options.shifttime > (options.stoptime-options.starttime)):
            logging.warning('Specified shifttime (%d) greater than observation length (%d): new shifttime=%d',
                            options.shifttime,options.stoptime-options.starttime,options.stoptime-options.starttime)
            options.shifttime=options.stoptime-options.starttime
        if (havesourcename or haveradec):
            if (options.useazel):
                [T,X,Y]=find_whereitmoves(source,options.starttime,options.stoptime,options.shifttime)
                if (isinstance(source,obssource.MWA_Source)):
                    ra_phase_center=[source.ra]*len(T)
                    dec_phase_center=[source.dec]*len(T)
                else:
                    for t,x,y in zip(T,X,Y):
                        r,d=ephem_utils.azel2radec(x,y, t)
                        ra_phase_center.append(r)
                        dec_phase_center.append(d)
            else:
                if (isinstance(source,obssource.MWA_Source)):
                    T=range(options.starttime,options.stoptime,options.shifttime)
                    X=[source.ra]*len(T)
                    Y=[source.dec]*len(T)
                    ra_phase_center=[source.ra]*len(T)
                    dec_phase_center=[source.dec]*len(T)
                else:
                    logging.error('Do not know how to handle shifttime>0 and useazel=0 for a moving source')
                    sys.exit(1)
        elif (haveazel):
            T=range(options.starttime,options.stoptime,options.shifttime)
            X=[options.az]*len(T)
            Y=[options.el]*len(T)        
        elif (usehex):
            T=range(options.starttime,options.stoptime,options.shifttime)
            X=[options.hex]*len(T)
            Y=[options.hex]*len(T)                
        else:
            # somehow haveradec and usehex and havehex are all not defined
            logger.error('Must specify a source or a position')
            logging.error("Known sources: %s" % (",".join(Sources.keys())))
            if (len(SatelliteList)>0):
                logging.error("Known satellites: %s" % (", ".join(SatelliteList.keys())))
            whatisup(Sources, options.starttime, options.horizon, options.minsundistance, options.minjupiterdistance)
            if (len(SatelliteList)>0):
                whatisup(SatelliteList, options.starttime, options.horizon, options.minsundistance, options.minjupiterdistance)
            sys.exit(1)
        print "# Calculations for %s from %s to %s; shift every %d s" % (source.name,options.starttime,
                                                                         options.stoptime,options.shifttime)
    # a moving source
    else:        
        [T,X,Y]=find_whenitmoves(source,options.starttime,options.stoptime,options.dt,options.maxshift,
                                 useazel=options.useazel,minaltitude=options.minaltitude,horizon=options.horizon)
        if (options.useaveragepositions and len(T)>1):
            # now get the average positions for the intervals
            [T,X,Y]=find_averagepositions(source,T,useazel=options.useazel)

        print "# Calculations for %s from %s to %s; maximum shift is %.1f arcsec" % (sourcename,
                                                                                     options.starttime,
                                                                                     options.stoptime,
                                                                                     options.maxshift)
    
    # make use of the default mode settings
    if options.mode is None:
        logging.warning('No mode specified: using default')
        options.mode=repr(Obs_Modes[schedule.getDefaultObsMode(db=db)])

    # Now we have all information
    # time to put it all in the newobs object and output it
    newobs=ObsConfig()
    #newobs.creator=xname
    # default will be username
    if (options.creator is None):
        newobs.creator=os.environ['USER']
        if newobs.creator in ('root','mwa'):
            logging.error("Unable to run with creator=%s: must specify --creator=<creator> option",newobs.creator)
            sys.exit(1)
    else:
        newobs.creator=options.creator
    newobs.rfstream=options.rfstream                
    newobs.frequencies=options.frequencies
    newobs.frequency_type=options.frequency_type
    newobs.vsib_frequency=options.vsib_frequency
    newobs.tileselection=options.tileselection
    newobs.walsh_mode=options.walsh_mode
    newobs.gain_control_type=options.gain_control_type
    newobs.gain_control_value=options.gain_control_value
    newobs.mode=options.mode
    newobs.unpowered=options.unpowered
    newobs.dipex=options.dipex
    newobs.comment=options.comment
    newobs.logtype=options.logtype
    newobs.projectid =options.projectid

    metadata=schedule.Schedule_Metadata(db=db)
    metadata.calibration=options.calibration
    metadata.calibrators=options.calibrators
    if (len(options.calibrators)>0):
        metadata.calibration=True
        
    titles="# GPSsec[s]"
    if (options.printUT):
        titles+=" Date[UT]\t\t\t"
        
    if (not options.useazel and not usehex):
        titles+="\tRA[deg]\t\tDec[deg]"
    elif (usehex):
        titles+="\tHex"
    else:
        titles+="\tAz[deg]\t\tEl[deg]"
    if (len(T)>1):
        print titles

    if (not options.obsname):
        # if no name supplied, construct one
        options.obsname=source.name
        if (len(newobs.frequencies)==1):
            options.obsname+="_%s" % (list(newobs.frequencies)[0])

    for i in xrange(len(T)):
        if (len(T)>1 and T[i]==options.stoptime):
            continue
        newobs.starttime=T[i]
        metadata.observation_number=newobs.starttime

        if (i < len(T)-1):
            newobs.stoptime=T[i+1]
        else:
            newobs.stoptime=options.stoptime

        if (not options.useazel and not usehex):
            # use RA, Dec
            newobs.ra=float(X[i])
            newobs.dec=float(Y[i])
            metadata.ra_pointing, metadata.dec_pointing=newobs.ra, newobs.dec
            metadata.azimuth_pointing, metadata.elevation_pointing=ephem_utils.radec2azel(
                newobs.ra,newobs.dec,newobs.starttime)
        if (options.useazel):
            if (options.usegrid is not None):
                grid_position,grid_separation=find_closest_grid_pointing(options.usegrid,X[i],Y[i],
                                                                         options.maxgridsigma)
                if grid_position is None:
                    sys.exit(1)
                print "# Selecting grid pointing %s (%.1f,%.1f) instead of (%.1f,%.1f), %.1f degrees away" % (
                    repr(grid_position),grid_position.azimuth,grid_position.elevation,
                    float(X[i]),float(Y[i]),grid_separation)
                metadata.gridpoint_name=grid_position.name
                metadata.gridpoint_number=grid_position.number                
                X[i]=grid_position.azimuth
                Y[i]=grid_position.elevation
            newobs.azimuth=float(X[i])
            newobs.elevation=float(Y[i])
            metadata.azimuth_pointing, metadata.elevation_pointing=newobs.azimuth, newobs.elevation
            metadata.ra_pointing, metadata.dec_pointing=ephem_utils.azel2radec(
                newobs.azimuth, newobs.elevation, newobs.starttime)

        newobs.hex=options.hex


        if (metadata.ra_pointing is not None and metadata.dec_pointing is not None):            
            try:
                metadata.sky_temp=get_Tsky(metadata.ra_pointing, metadata.dec_pointing, newobs.frequencies[len(newobs.frequencies)/2]*1.28)
            except:
                metadata.sky_temp=0
                
        if (metadata.azimuth_pointing is not None and metadata.elevation_pointing is not None):
            metadata.sun_pointing_distance,metadata.sun_elevation=get_elevation_separation_azel(
                metadata.azimuth_pointing, metadata.elevation_pointing, metadata.observation_number, object='Sun')
            metadata.jupiter_pointing_distance=get_elevation_separation_azel(
                metadata.azimuth_pointing, metadata.elevation_pointing, metadata.observation_number, object='Jupiter')[0]
            metadata.moon_pointing_distance=get_elevation_separation_azel(
                metadata.azimuth_pointing, metadata.elevation_pointing, metadata.observation_number, object='Moon')[0]

        if (len(ra_phase_center)>0 and len(dec_phase_center)>0):
            newobs.ra_phase_center=float(ra_phase_center[i])
            newobs.dec_phase_center=float(dec_phase_center[i])
        else:
            if (not options.useazel and not usehex):
                # should be from moving bodies, where we defined the RA and Dec
                newobs.ra_phase_center=float(X[i])
                newobs.dec_phase_center=float(Y[i])


        if not usehex:
            stringX=[ephem_utils.dec2sexstring(x,digits=0) for x in X]
            stringY=[ephem_utils.dec2sexstring(y,includesign=1,digits=0) for y in Y]
        else:
            stringX=X
            stringY=['' for y in Y]

        # DLK: Ed doesn't think we need completely unique obsnames
        newobs.obsname=options.obsname
        
        if (len(T)>1):
            if (options.printUT):
                [MJD,UT]=ephem_utils.calcUTGPSseconds(T[i])
                [yr,mn,dy]=ephem_utils.mjd_cal(MJD)
                UTs=ephem_utils.dec2sexstring(UT,digits=0,roundseconds=1)
                print "%d %04d-%02d-%02d (MJD %d) %s UT\t%s\t%s" % (T[i],yr,mn,dy,MJD,UTs,stringX[i],stringY[i])
            else:
                print "%d\t%s\t%s" % (T[i],stringX[i],stringY[i])
        s=newobs.single_observation(db=db, verbose=options.verbose, usedatabase=options.usedatabase,
                                    force=options.force, clear=options.clear)
        if (not s):
            logging.error('Error in entering the observation')

        mwa=ephem_utils.Obs[ephem_utils.obscode['MWA']]
        [mjd,ut]=ephem_utils.calcUTGPSseconds(metadata.observation_number)
        [yr,mn,dy]=ephem_utils.mjd_cal(mjd)
        UTs=ephem_utils.dec2sexstring(ut,digits=0,roundseconds=1)
        observer=ephem.Observer()
        # make sure no refraction is included
        observer.pressure=0
        observer.long=mwa.long/ephem_utils.DEG_IN_RADIAN
        observer.lat=mwa.lat/ephem_utils.DEG_IN_RADIAN
        observer.elevation=mwa.elev
        observer.date='%d/%d/%d %s' % (yr,mn,dy,UTs)
        metadata.local_sidereal_time_deg=observer.sidereal_time()*ephem_utils.DEG_IN_RADIAN
        try:
            freq=1.28*newobs.frequencies[len(newobs.frequencies)/2]
        except:
            freq=1.28*newobs.vsib_frequency
        try:
            skytemp=add_sky_temperature(metadata=metadata, frequency=freq,db=db)
        except:
            logging.warning('Unable to compute sky temperature')
            skytemp=0
        
        if options.usedatabase:
            errors = metadata.save(ask=0,force=options.force,verbose=options.verbose,db=db)

        if options.verbose:
            print metadata
            if skytemp is not None:
                print skytemp

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
    
######################################################################
def find_whenitmoves(body,GPSseconds_start,GPSseconds_end,dt,maxshift,useazel=0,minaltitude=10,horizon=0):
    """
    [T,X,Y]=find_whenitmoves(body,GPSseconds_start,GPSseconds_end,dt,maxshift,useazel=0,minaltitude=10,horizon=0)
    gets the (RA,Dec) or (Az,El) pairs for a moving body, using the routines in ephem
    taking all of the times GPSseconds_start:dt:GPSseconds_end, it computes when the body has moved
    more then maxshift arcseconds
    at that point it inserts a new value into T (time values) and X/Y.
    if (useazel==1), then X and Y will be Az and El
    else RA, Dec
    all coordinates are in decimal degrees

    """
    x=[]
    y=[]
    X=[]
    Y=[]
    T=[]
    alt=[]
    Alt=[]
    observer=ephem.Observer()
    # make sure no refraction is included
    observer.pressure=0
    mwa=ephem_utils.Obs[ephem_utils.obscode['MWA']]
    observer.long=mwa.long/ephem_utils.DEG_IN_RADIAN
    observer.lat=mwa.lat/ephem_utils.DEG_IN_RADIAN
    observer.elevation=mwa.elev

    for t in xrange(GPSseconds_start,GPSseconds_end+dt,dt):
        [mjd,ut]=ephem_utils.calcUTGPSseconds(t)
        [yr,mn,dy]=ephem_utils.mjd_cal(mjd)
        time=ephem_utils.dec2sexstring(ut)
        observer.date='%d/%d/%d %s' % (yr,mn,dy,time)
        body.compute(observer)
        alt.append(body.alt*ephem_utils.DEG_IN_RADIAN)
        if (useazel):
            x.append(body.az*ephem_utils.DEG_IN_RADIAN)
            y.append(body.alt*ephem_utils.DEG_IN_RADIAN)
        else:
            x.append(body.ra*ephem_utils.DEG_IN_RADIAN)
            y.append(body.dec*ephem_utils.DEG_IN_RADIAN)
        if (len(x)>1 and len(X)>0):
            # distance in arcseconds
            d=3600*ephem_utils.DEG_IN_RADIAN*ephem_utils.angulardistance(x[-1]/15,y[-1],X[-1]/15,Y[-1])
        if (len(X)==0 or d>maxshift):
            X.append(x[-1])
            Y.append(y[-1])
            T.append(t)
            Alt.append(alt[-1])
    return [T,X,Y]

######################################################################
def find_whereitmoves(body,GPSseconds_start,GPSseconds_end,dt):
    """
    [T,X,Y]=find_whereitmoves(body,GPSseconds_start,GPSseconds_end,dt)
    gets the (Az,El) pairs for a body (moving or fixed), using the routines in ephem
    taking all of the times GPSseconds_start:dt:GPSseconds_end,
    it returns a new position every dt seconds
    at that point it inserts a new value into T (time values) and X/Y.
    X and Y will be Az and El
    all coordinates are in decimal degrees

    """

    X=[]
    Y=[]
    T=[]
    observer=ephem.Observer()
    # make sure no refraction is included
    observer.pressure=0
    mwa=ephem_utils.Obs[ephem_utils.obscode['MWA']]
    observer.long=mwa.long/ephem_utils.DEG_IN_RADIAN
    observer.lat=mwa.lat/ephem_utils.DEG_IN_RADIAN
    observer.elevation=mwa.elev

    #for t in xrange(GPSseconds_start,GPSseconds_end+dt,dt):
    # calculate for the middle of the interval
    for t in xrange(GPSseconds_start+dt/2,GPSseconds_end+dt+dt/2,dt):
        [mjd,ut]=ephem_utils.calcUTGPSseconds(t)
        [yr,mn,dy]=ephem_utils.mjd_cal(mjd)
        time=ephem_utils.dec2sexstring(ut)
        observer.date='%d/%d/%d %s' % (yr,mn,dy,time)
        if (t-dt/2 <= GPSseconds_end):
            T.append(t-dt/2)
            if (isinstance(body,obssource.MWA_Source)):
                # it's a fixed object, do it simply
                #[alt,az]=ephem_utils.pyephem_altaz(body.ra/15,body.dec,mwa.lat,mwa.long,mjd+ut/24.0)
                az,alt=ephem_utils.radec2azel(body.ra,body.dec,t)
                X.append(az)
                Y.append(alt)
            else:
                # it's a moving object
                body.compute(observer)
                X.append(body.az*ephem_utils.DEG_IN_RADIAN)
                Y.append(body.alt*ephem_utils.DEG_IN_RADIAN)
    return [T,X,Y]

######################################################################
def find_averagepositions(body, T, useazel=0):
    """
    [T,X,Y]=find_averagepositions(body, T, useazel=0)
    computes positions (X,Y)= (RA,Dec) or (Az,El) for the middle of each interval T[i]->T[i+1]
    """
    X=[]
    Y=[]
    
    observer=ephem.Observer()
    # make sure no refraction is included
    observer.pressure=0
    mwa=ephem_utils.Obs[ephem_utils.obscode['MWA']]
    observer.long=mwa.long/ephem_utils.DEG_IN_RADIAN
    observer.lat=mwa.lat/ephem_utils.DEG_IN_RADIAN
    observer.elevation=mwa.elev

    for i in xrange(len(T)-1):
        [mjd,ut]=ephem_utils.calcUTGPSseconds(0.5*(T[i]+T[i+1]))
        [yr,mn,dy]=ephem_utils.mjd_cal(mjd)
        time=ephem_utils.dec2sexstring(ut)
        observer.date='%d/%d/%d %s' % (yr,mn,dy,time)
        body.compute(observer)
        if (useazel):
            X.append(body.az*ephem_utils.DEG_IN_RADIAN)
            Y.append(body.alt*ephem_utils.DEG_IN_RADIAN)
        else:
            X.append(body.ra*ephem_utils.DEG_IN_RADIAN)
            Y.append(body.dec*ephem_utils.DEG_IN_RADIAN)
    
    return [T[:-1],X,Y]

######################################################################
def checktimes(starttime,stoptime):
    """ result=checktimes(starttime,stoptime)
    checks to make sure starttime and stoptime are both valid
    """
    if (starttime==0 or stoptime==0 or starttime is None or stoptime is None):
        logging.error('Both starttime (%d) and stoptime (%d) must be non-zero' % (starttime,stoptime))
        sys.exit(1)
    if (stoptime<=starttime):
        logging.error('stoptime (%d) must be > starttime (%d)'  %(stoptime,starttime))
        sys.exit(1)
    return 1
######################################################################
def checkfrequencies(frequencystart, frequencystop, nchannels=24):
    """result=checkfrequencies(frequencystart, frequencystop, nchannels=25)
    makes sure the frequency ranges are valid

    this is now deprecated (replaced by parse_frequencies)
    """
    if (frequencystart is None or frequencystop is None):
        if frequencystart is None:
            logging.error('frequencystart must be defined')
        if frequencystop is None:
            logging.error('frequencystop must be defined')            
        return 0
    if (frequencystop < frequencystart):
        logging.error('frequencystop (%d) must be >= frequencystart (%d)' % (frequencystop,frequencystart))
        return 0
    if (frequencystop - frequencystart >= nchannels):
        logging.error('Must have <= %d frequency channels (currently have %d, %d:%d)' % (nchannels,frequencystop-frequencystart+1,frequencystart,frequencystop))
        return 0
    return 1

######################################################################
def checkhex(hexcode, nwords=16, separator=","):
    """
    checks whether the hexcode is valid
    the hexcode should be <nwords> * 6-bit words, separated by <separator>
    """
    maxvalue=int('111111',2)
    hexcodes=re.split(separator + '\s*',hexcode)
    hexcodedecvals=[int(y,16) for y in hexcodes]
    if ((len(hexcodes) != nwords) or (max(hexcodedecvals)>maxvalue) or (min(hexcodedecvals)<0)):
        logging.error('Hexcode %s is not valid' % hexcode)
        return 0
    return 1

######################################################################
def whatisup(sources, GPStime=0, minaltitude=0, minsundistance=-1, minjupiterdistance=-1):
    """ whatisup(sources, GPStime=0, minaltitude=0, minsundistance=-1, minjupiterdistance=-1)
    prints out the altitudes of the sources at the specified time
    also sees if they are far enough away from Jupiter & the Sun
    """

    mwa=ephem_utils.Obs[ephem_utils.obscode['MWA']]
    if (not GPStime):
        GPStime=ephem_utils.GPSseconds_next()
    [mjd,ut]=ephem_utils.calcUTGPSseconds(GPStime)
    [yr,mn,dy]=ephem_utils.mjd_cal(mjd)
    UTs=ephem_utils.dec2sexstring(ut,digits=0,roundseconds=1)
    observer=ephem.Observer()
    # make sure no refraction is included
    observer.pressure=0
    observer.long=mwa.long/ephem_utils.DEG_IN_RADIAN
    observer.lat=mwa.lat/ephem_utils.DEG_IN_RADIAN
    observer.elevation=mwa.elev
    observer.date='%d/%d/%d %s' % (yr,mn,dy,UTs)
    LST=ephem_utils.dec2sexstring(observer.sidereal_time()*ephem_utils.HRS_IN_RADIAN,digits=0,roundseconds=1)
    
    s={}
    for source in sources.keys():
        if (not isinstance(sources[source],ephem.EarthSatellite) and not sources[source].moving):
            #[alt,az]=ephem_utils.pyephem_altaz(sources[source].ra/15,sources[source].dec,mwa.lat,mwa.long,mjd+ut/24.0)
            az,alt=ephem_utils.radec2azel(sources[source].ra,sources[source].dec,GPStime)
            ra=sources[source].ra
            dec=sources[source].dec
        else:
            if (not isinstance(sources[source],ephem.EarthSatellite)):
                body=ephem.__dict__[source]()
                body.compute(observer)
                alt=body.alt*ephem_utils.DEG_IN_RADIAN
                ra=body.ra*ephem_utils.DEG_IN_RADIAN
                dec=body.dec*ephem_utils.DEG_IN_RADIAN
            else:
                sources[source].compute(observer)
                alt=sources[source].alt*ephem_utils.DEG_IN_RADIAN
                ra=sources[source].ra*ephem_utils.DEG_IN_RADIAN
                dec=sources[source].dec*ephem_utils.DEG_IN_RADIAN
        x=math.fabs(alt)
        sundistance=sourcedistance(sources[source],sources['Sun'],GPStime)
        jupiterdistance=sourcedistance(sources[source],sources['Jupiter'],GPStime)

        xs='+'
        flag=''
        if (alt < 0):
           xs='-'
        if (alt > minaltitude and sundistance>minsundistance and jupiterdistance > minjupiterdistance):
            flag='***'
        xs+='%04.1f' % x
        sourcename=source
        if (len(sourcename)<8):
            sourcename+="\t"
        xs2='%d' % sundistance
        if (sundistance<100):
            xs2=' ' + xs2
        if (sundistance<10):
            xs2=' ' + xs2
        xs3='%d' % jupiterdistance
        if (jupiterdistance<100):
            xs3=' ' + xs3
        if (jupiterdistance<10):
            xs3=' ' + xs3
        s[ra]="%s\t\t%s %s\t%s\t%s\t\t%s    \t\t%s" % (sourcename,ephem_utils.dec2sexstring(ra/15,digits=0,roundseconds=1),ephem_utils.dec2sexstring(dec,includesign=1,digits=0,roundseconds=1),xs,xs2,xs3,flag)
    print "\n# Altitudes of sources at %d %04d-%02d-%02d (MJD %d) %s UT = %s LST" % (GPStime,yr,mn,dy,mjd,UTs,LST)
    print "# Source\t\tRA [h]   Dec [d]\tAlt [d]\tSunDist [d]\tJupDist [d]\tVisible?"
    ras=sorted(s.keys())
    for ra in ras:
        print s[ra]
    print ""

######################################################################
def sourcedistance(source1, source2, GPStime=0):
    """distance=sourcedistance(source1, source2, GPStime=0)
    returns distance in degrees between two MWA_source sources
    if unable to get compatible coordinates for the two objects (either Az,El or RA,Dec)
    will return 99
    """

    mwa=ephem_utils.Obs[ephem_utils.obscode['MWA']]
    if (not GPStime):
        GPStime=ephem_utils.GPSseconds_next()
    [mjd,ut]=ephem_utils.calcUTGPSseconds(GPStime)
    [yr,mn,dy]=ephem_utils.mjd_cal(mjd)
    UTs=ephem_utils.dec2sexstring(ut,digits=0,roundseconds=1)
    observer=ephem.Observer()
    # make sure no refraction is included
    observer.pressure=0
    observer.long=mwa.long/ephem_utils.DEG_IN_RADIAN
    observer.lat=mwa.lat/ephem_utils.DEG_IN_RADIAN
    observer.elevation=mwa.elev
    observer.date='%d/%d/%d %s' % (yr,mn,dy,UTs)
    LST=ephem_utils.dec2sexstring(observer.sidereal_time()*ephem_utils.HRS_IN_RADIAN,digits=0,roundseconds=1)
    # should we do the calculations in (Az,El) or (RA,Dec)?
    useazel=False
    if (hasattr(source1,"azimuth") and source1.azimuth != None and (not hasattr(source1,"ra") or source1.ra == None)):
            useazel=True
    if (hasattr(source2,"azimuth") and source2.azimuth != None and (not hasattr(source2,"ra") or source2.ra == None)):
            useazel=True
    if (not useazel):
        # position of source1
        if (not isinstance(source1,ephem.EarthSatellite) and not source1.moving):
            ra1=source1.ra
            dec1=source1.dec
        else:
            if (not isinstance(source1,ephem.EarthSatellite)):
                body=ephem.__dict__[source1.name]()
                body.compute(observer)
                alt=body.alt*ephem_utils.DEG_IN_RADIAN
                ra1=body.ra*ephem_utils.DEG_IN_RADIAN
                dec1=body.dec*ephem_utils.DEG_IN_RADIAN
            else:
                source1.compute(observer)
                alt=source1.alt*ephem_utils.DEG_IN_RADIAN
                ra1=source1.ra*ephem_utils.DEG_IN_RADIAN
                dec1=source1.dec*ephem_utils.DEG_IN_RADIAN
        # position of source2
        if (not isinstance(source2,ephem.EarthSatellite) and not source2.moving):
            ra2=source2.ra
            dec2=source2.dec
        else:
            if (not isinstance(source2,ephem.EarthSatellite)):                
                body=ephem.__dict__[source2.name]()
                body.compute(observer)
                alt=body.alt*ephem_utils.DEG_IN_RADIAN
                ra2=body.ra*ephem_utils.DEG_IN_RADIAN
                dec2=body.dec*ephem_utils.DEG_IN_RADIAN
            else:
                source2.compute(observer)
                alt=source2.alt*ephem_utils.DEG_IN_RADIAN
                ra2=source2.ra*ephem_utils.DEG_IN_RADIAN
                dec2=source2.dec*ephem_utils.DEG_IN_RADIAN
                
        # distance in degrees
        distance=ephem_utils.angulardistance(ra1/15.0,dec1,ra2/15.0,dec2)*ephem_utils.DEG_IN_RADIAN
    else:
        # use Az,El
        # position of source1
        if (hasattr(source1,"elevation") and hasattr(source1,"azimuth")):
            # just get directly
            alt1=source1.elevation
            az1=source1.azimuth            
        else:
            try:
                if (not isinstance(source1,ephem.EarthSatellite) and not source1.moving):
                    #[alt1,az1]=ephem_utils.pyephem_altaz(source1.ra/15.0,source1.dec,mwa.lat,mwa.long,mjd+ut/24.0)
                    az1,alt1=ephem_utils.radec2azel(source1.ra, source1.dec, GPStime)
                else:
                    if (not isinstance(source1,ephem.EarthSatellite)):
                        body=ephem.__dict__[source1.name]()
                        body.compute(observer)
                        alt1=body.alt*ephem_utils.DEG_IN_RADIAN
                        az1=body.az*ephem_utils.DEG_IN_RADIAN
                    else:
                        source1.compute(observer)
                        alt1=source1.alt*ephem_utils.DEG_IN_RADIAN
                        az1=source1.az*ephem_utils.DEG_IN_RADIAN
            except (AttributeError,TypeError):
                # unable to get a good set of coords
                return 99
        # position of source2
        if (hasattr(source2,"elevation") and hasattr(source2,"azimuth")):
            # just get directly
            alt2=source2.elevation
            az2=source2.azimuth            
        else:
            try:
                if (not isinstance(source2,ephem.EarthSatellite) and not source2.moving):
                    #[alt2,az2]=ephem_utils.pyephem_altaz(source2.ra/15.0,source2.dec,mwa.lat,mwa.long,mjd+ut/24.0)
                    az1,alt1=ephem_utils.radec2azel(source2.ra, source2.dec, GPStime)
                else:
                    if (not isinstance(source2,ephem.EarthSatellite)):
                        body=ephem.__dict__[source2.name]()
                        body.compute(observer)
                        alt2=body.alt*ephem_utils.DEG_IN_RADIAN
                        az2=body.az*ephem_utils.DEG_IN_RADIAN
                    else:
                        source2.compute(observer)
                        alt2=source2.alt*ephem_utils.DEG_IN_RADIAN
                        az2=source2.az*ephem_utils.DEG_IN_RADIAN
            except (AttributeError,TypeError):
                # unable to get a good set of coords
                return 99
                      
        # distance in degrees
        distance=ephem_utils.angulardistance(az1/15.0,alt1,az2/15.0,alt2)*ephem_utils.DEG_IN_RADIAN

    return distance

######################################################################
def get_next_starttime(db=None, observationlength=8):
    """
    starttime=get_next_starttime(db=None, observationlength=8)
    goes through the entries in MWA_Setting
    finds the next possible starttime such that an observation of length <observationlength>
    will fit, beginning with now

    returns the appropriate time (in GPS seconds)

    """

    if (db is None):        
        logging.error('Must pass database handle')
        return 0

    now=ephem_utils.GPSseconds_next()
    padding=8
    # get the starttime and stoptime for all events that are either ongoing or in the future
    starttimes,stoptimes=schedule.getStartstoptimes(db=db, mintime=now-padding,key='stoptime',sort=True)
    if (len(starttimes)==0):
        # nothing scheduled
        return now
    gap_starttimes=[now]
    gap_stoptimes=[]
    # go through the scheduled observations
    # figure out when the gaps are
    # deal with whether the first one is ongoing or future
    startstoptimes=zip(starttimes,stoptimes)
    for starttime,stoptime in startstoptimes:
        if ((starttime <= now and stoptime >= now)):
            # it is ongoing
            gap_starttimes[0]=stoptime
        else:
            # it is in the future
            gap_stoptimes.append(starttime)
            gap_starttimes.append(stoptime)
    # very very future
    gap_stoptimes.append(2147483647)

    new_starttimes=[]    
    # identify all of the possible gaps
    for i in xrange(len(gap_starttimes)):
        if (gap_stoptimes[i] - gap_starttimes[i] >= observationlength):
            # DLK: test
            # this would be faster, but will it always work?
            #return gap_starttimes[i]
            new_starttimes.append(gap_starttimes[i])

    if (len(new_starttimes)>0):
        # return the first one
        return min(new_starttimes)
                
    # no good gaps exist
    logging.error('No suitable space found in future schedule')
    return 0

######################################################################
def adjusttime(source,starttime,stoptime,minaltitude=0,minsundistance=-1,minjupiterdistance=-1,increment=8):
    """
    [newstarttime,newstoptime]=adjusttime(source,starttime,stoptime,minaltitude=0,minsundistance=-1,minjupiterdistance=-1,increment=8):
    goes between the times [starttime,stoptime] in increments of <increment>
    checks to see that the given source is above <minaltitude> and
    more than <minsundistance> degrees from the Sun and
    more than <minjupiterdistance> degrees from Jupiter
    it selects the single interval that fulfill that condition
    """
    goodtimes=[]
    mwa=ephem_utils.Obs[ephem_utils.obscode['MWA']]
    observer=ephem.Observer()
    # make sure no refraction is included
    observer.pressure=0
    observer.long=mwa.long/ephem_utils.DEG_IN_RADIAN
    observer.lat=mwa.lat/ephem_utils.DEG_IN_RADIAN
    observer.elevation=mwa.elev
    for time in xrange(starttime,stoptime,increment):
        [mjd,ut]=ephem_utils.calcUTGPSseconds(time)
        [yr,mn,dy]=ephem_utils.mjd_cal(mjd)
        if (isinstance(source,obssource.MWA_Source)):
            sundistance=sourcedistance(source,Sources['Sun'],time)
            jupiterdistance=sourcedistance(source,Sources['Jupiter'],time)
            #[alt,az]=ephem_utils.pyephem_altaz(source.ra/15.0,source.dec,mwa.lat,mwa.long,mjd+ut/24.0)
            az,alt=ephem_utils.radec2azel(source.ra, source.dec, time)
        else:
            sundistance=sourcedistance(Sources[source.name],Sources['Sun'],time)
            jupiterdistance=sourcedistance(Sources[source.name],Sources['Jupiter'],time)
            observer.date='%d/%d/%d %s' % (yr,mn,dy,ephem_utils.dec2sexstring(ut))
            source.compute(observer)
            alt=source.alt*ephem_utils.DEG_IN_RADIAN            

        if (alt>=minaltitude and sundistance >= minsundistance and jupiterdistance >= minjupiterdistance):
            goodtimes.append(time)
    if (len(goodtimes)==0):
        return [0,0]
    actualstarttime=min(goodtimes)
    actualstoptime=max(goodtimes)
    
    return [actualstarttime, actualstoptime]

######################################################################
def parse_freqs(input,maxfreqs=24, separator=";"):
    """
    freqs=parse_freqs(input,maxfreqs=24, separator=";")

    will parse the frequency specification given on the command line
    that can take the form of:

    <channel>
    <center>,<width>,<increment>
    <start>:<stop>:<increment>

    where the increments default to 1.  Multiple entries can be given separated by <separator>,
    which defaults to ;
    if using ;, entries should be enclosed in quotes

    """
    freqs=[]
    atoms=input.split(separator)
    for atom in atoms:
        if not (":" in atom or "," in atom or "-" in atom):
            # just a number
            try:
                freqs.append(int(atom))
            except ValueError:
                logging.error('Unable to parse frequency channel: %s' % atom)
                return freqs
        elif (":" in atom):
            # assumes <channelstart>:<channelstop>:<increment>
            increment=1
            res=atom.split(":")
            if (len(res)>2):
                try:
                    increment=int(res[2])
                except ValueError:
                    logging.error('Unable to parse frequency increment: %s' % res[2])                    
                    return freqs
            try:
                freqstart=int(res[0])
            except ValueError:
                logging.error('Unable to parse frequency start: %s' % res[0])                    
                return freqs            
            try:
                freqstop=int(res[1])
            except ValueError:
                logging.error('Unable to parse frequency stop: %s' % res[1])                    
                return freqs
            for freq in xrange(freqstart,freqstop+1,increment):
                freqs.append(freq)
        elif ("-" in atom):
            # assumes <channelstart>-<channelstop>-<increment>
            increment=1
            res=atom.split("-")
            if (len(res)>2):
                try:
                    increment=int(res[2])
                except ValueError:
                    logging.error('Unable to parse frequency increment: %s' % res[2])                    
                    return freqs
            try:
                freqstart=int(res[0])
            except ValueError:
                logging.error('Unable to parse frequency start: %s' % res[0])                    
                return freqs            
            try:
                freqstop=int(res[1])
            except ValueError:
                logging.error('Unable to parse frequency stop: %s' % res[1])                    
                return freqs
            for freq in xrange(freqstart,freqstop+1,increment):
                freqs.append(freq)

        elif ("," in atom):
            # assumes <center>,<width>,<increment>
            increment=1
            res=atom.split(",")
            if (len(res)>2):
                try:
                    increment=int(res[2])
                except ValueError:
                    logging.error('Unable to parse frequency increment: %s' % res[2])                    
                    return freqs
            try:
                freqcenter=int(res[0])
            except ValueError:
                logging.error('Unable to parse frequency center: %s' % res[0])                    
                return freqs            
            try:
                freqwidth=int(res[1])
            except ValueError:
                logging.error('Unable to parse frequency width: %s' % res[1])                    
                return freqs
            for freq in xrange(freqcenter-int(freqwidth/2.0),freqcenter+int(freqwidth/2.0+0.5),increment):
                freqs.append(freq)
    

    # remove duplicates
    origfreqs=freqs
    freqs=list(set(freqs))
    if (len(freqs) < len(origfreqs)):
        logging.warning("Removed duplicate items from frequency list")
    # sort
    freqs.sort()
    # trim if necessary
    if maxfreqs > 0 and len(freqs)>maxfreqs:
        logging.warning("Removed excess items from frequency list: %s",freqs[maxfreqs:])
        freqs=freqs[:maxfreqs]

    if (0 in freqs):
        logging.warning("Frequency channel 0 specified: this no longer implies BURST_VSIB")
    if (min(freqs) < 0):
        while (min(freqs)<0):
            del freqs[0]
        logging.warning("Removed negative frequencies from list")

    if (len(freqs)==1):
        # only a single frequency
        logging.warning('--freq=%d requested, but interpreting it as --freq=%d,24' % (freqs[0],freqs[0]))
        freqcenter=freqs[0]
        freqwidth=24
        increment=1
        freqs=range(freqcenter-int(freqwidth/2.0),freqcenter+int(freqwidth/2.0+0.5),increment)
                        
    return freqs

######################################################################
def find_closest_grid_pointing(grid=None,az=0,el=0,maxsigma=None):
    """
    closest,closest_distance=find_closest_grid_pointing(grid=None,az=0,el=0,maxsigma=None)
    returns the grid pointing that is closest to the requested position (az,el) in degrees
    along with the distance to that point.  In addition, filtering can be done on the "sigma" column
    with a maximum allowed value specified.
    """

    closest=None
    # in degrees
    closest_distance=180
    for g in Grid_Points:
        if ((not isinstance(grid,str) and grid) or g.name==grid):
            if (maxsigma is None or g.sigma <= maxsigma):
                x1 = math.cos(az/ephem_utils.DEG_IN_RADIAN)*math.cos(el/ephem_utils.DEG_IN_RADIAN)
                y1 = math.sin(az/ephem_utils.DEG_IN_RADIAN)*math.cos(el/ephem_utils.DEG_IN_RADIAN)
                z1 = math.sin(el/ephem_utils.DEG_IN_RADIAN)
                x2 = math.cos(g.azimuth/ephem_utils.DEG_IN_RADIAN)*math.cos(g.elevation/ephem_utils.DEG_IN_RADIAN)
                y2 = math.sin(g.azimuth/ephem_utils.DEG_IN_RADIAN)*math.cos(g.elevation/ephem_utils.DEG_IN_RADIAN)
                z2 = math.sin(g.elevation/ephem_utils.DEG_IN_RADIAN)
                arg=x1*x2+y1*y2+z1*z2
                if (arg>1):
                    arg=1
                if (arg<-1):
                    arg=-1
                theta = math.acos(arg)*ephem_utils.DEG_IN_RADIAN
                if (theta < closest_distance):
                    closest_distance=theta
                    closest=g
    if (closest is None):
        if (maxsigma is None):
            logging.error('No grid pointings matched grid specification %s' % (grid))
        else:        
            logging.error('No grid pointings matched grid specification %s with maxsigma=%.1e' % (grid,maxsigma))
    return closest,closest_distance

######################################################################
def add_sky_temperature(metadata=None, frequency=150, db=db):
    """
    adds the sky temperature to the metadata entry
    for the given frequency in MHz
    assumes nominal frequency is 150 MHz and spectral index is -2.6
    """
    skytemp=None
    if metadata.local_sidereal_time_deg is None:
        logging.error('Cannot compute sky temperature without valid LST')
        return None
    # convert the LST in hours to an integer for 1/100h
    LST_index=int((metadata.local_sidereal_time_deg/15)*100+0.5)
    # and round to the nearest 0.2h
    LST_index=int(round(LST_index/20.0)*20)
    # index by gridpoint if possible:
    if metadata.gridpoint_number is not None and metadata.gridpoint_name=='sweet':
        skytemp=schedule.MWA_Skytemp((metadata.gridpoint_number,LST_index),db=db)
        metadata.sky_temp=(0.5*(skytemp.T1+skytemp.T2))*(frequency/150.0)**-2.6
    elif metadata.azimuth_pointing is not None and metadata.elevation_pointing is not None:
        # need to find the gridpoints ourself        
        grid_position,grid_separation=find_closest_grid_pointing('sweet',metadata.azimuth_pointing, metadata.elevation_pointing)
        skytemp=schedule.MWA_Skytemp((grid_position.number,LST_index),db=db)
        metadata.sky_temp=(0.5*(skytemp.T1+skytemp.T2))*(frequency/150.0)**-2.6
        
    return skytemp
                                     

######################################################################
def parse_bool(value):
    """
    parses boolean input as a string
    True is: [True, true, yes, Yes, 1]
    False is: [False, false, no, No, 0]
    """
    try:
        if (int(value)==1):
            return True
        elif (int(value)==0):
            return False
        else:
            raise ValueError
    except ValueError:
        if (value.upper()[0]=='T' or value.upper()[0]=='Y'):
            return True
        if (value.upper()[0]=='F' or value.upper()[0]=='N'):
            return False
        raise ValueError

    
######################################################################
def bool_callback(option, opt, value, parser):
    try:
        setattr(parser.values, option.dest, parse_bool(value))
    except:
        raise optparse.OptionValueError("Could not parse choice %s" % value)
######################################################################
def position_callback(option, opt, value, parser):

    if (value.count(':')>0):
        try:
            x=ephem_utils.sexstring2dec(value)
            if (opt == '--ra'):
                x*=15.0
        except:
            raise OptionValueError("Could not parse %s: %s" % (opt,value))
    else:
        try:
            x=float(value)
        except:
            raise OptionValueError("Could not parse %s: %s" % (opt,value))
        
    setattr(parser.values, option.dest, x)


######################################################################
def freqs_callback(option, opt, value, parser):

    try:
        setattr(parser.values, option.dest, parse_freqs(value))
    except:
        raise OptionValueError("Could not parse frequencies %s" % value)
######################################################################
def get_elevation_separation_azel(azimuth, elevation, GPStime, object='Sun'):
    mwa=ephem_utils.Obs[ephem_utils.obscode['MWA']]
    [mjd,ut]=ephem_utils.calcUTGPSseconds(GPStime)
    [year,month,day]=ephem_utils.mjd_cal(mjd)
    hour,minute,second=ephem_utils.dec2sex(ut)
    UTs='%02d:%02d:%02d' % (hour,minute,second)
    observer=ephem.Observer()
    # make sure no refraction is included
    observer.pressure=0
    observer.long=mwa.long/ephem_utils.DEG_IN_RADIAN
    observer.lat=mwa.lat/ephem_utils.DEG_IN_RADIAN
    observer.elevation=mwa.elev
    observer.date='%d/%d/%d %s' % (year,month,day,UTs)
    body=ephem.__dict__[object]()
    body.compute(observer)
    output_elevation=body.alt*ephem_utils.DEG_IN_RADIAN
    output_separation=ephem_utils.DEG_IN_RADIAN*ephem_utils.angulardistance(azimuth/15.0,elevation,
                                                                            body.az*ephem_utils.HRS_IN_RADIAN,
                                                                            body.alt*ephem_utils.DEG_IN_RADIAN)
    return output_separation, output_elevation
    
######################################################################
def get_Tsky(ra, dec, frequency):
    """
    Tsky=get_Tsky(ra,dec,frequency)
    ra,dec in degrees
    frequency in MHz

    returns sky temperature in K

    for now, just a placeholder
    """

    return 0
######################################################################

if __name__=="__main__":
    main()



