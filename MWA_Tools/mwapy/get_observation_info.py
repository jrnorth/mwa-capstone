"""

Gets fundamental information about an observation

python ~/mwa/software/MWA_Tools/get_observation_info.py --filename='P00_drift_121_20110927161501' -v -i
# INFO:get_observation_info: Found matching observation for GPS time 1001175316 in MWA_Setting database at GPS time=1001175315 (difference=-1 s)

# INFO:get_observation_info: Found delays in RFstream (0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0)

P00_drift_121 at 1001175315 (GPS)
55831 (2011/09/27) 16:15:00, for 300 s (Sun at -61.5 deg)
Channels: 109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128,129,130,131,132 (center=121)
LST=00:26:07 (HA=00:00:38)
(Az,El) = (0.000, 90.000) deg
(RA,Dec) = (6.374, -26.772) deg (J2000)
delays = 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
# INFO:get_observation_info: Creating sky image for 2011/09/27 16:15:00, 154.88 MHz, delays=0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

# INFO:get_observation_info: Wrote 20110927161500_154.88MHz.png


"""


import logging, sys, os, glob, string, re, urllib, math, time
from optparse import OptionParser
import numpy
import psycopg2

import ephem
from mwapy import dbobj, ephem_utils
from mwapy.obssched.base import schedule
try:
    from mwapy.eorpy import ionex
    _USE_IONEX=True
except ImportError:
    _USE_IONEX=False
    

try:
    from mwapy.pb import primarybeammap
    _useplotting=True
except ImportError:
    _useplotting=False    

# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('get_observation_info')
logger.setLevel(logging.WARNING)

# open up database connection
try:
    db = schedule.getdb()
except:
    logger.error("Unable to open connection to database")
    sys.exit(1)

######################################################################
class MWA_Observation():
    """
    holds the fundamental data for a MWA observation
    the basic information is based on the observation_number,
    which is the starttime in GPS seconds
    once that is set, it computes all the rest of the times.
    It then queries the MandC database to get other information and determines coordinates

    o=MWA_Observation(observation_number, db=db)
    
    """

    ##################################################
    def __init__(self,observation_number=None,ionex=False, db=None):
        # hours
        self.LST=None
        self.HA=None
        self.MJD=None
        # hours
        self.UT=None
        # seconds
        self.duration=0
        # degrees
        self.sun_elevation=None
        # degrees
        self.azimuth=None
        self.elevation=None
        self.RA=None
        self.Dec=None
        self.filename=''
        self.receivers=[]
        self.delays=[]
        self.center_channel=-1
        self.channels=[]
        self.year=None
        self.month=None
        self.day=None
        self.hour=None
        self.minute=None
        self.second=None
        self.calibration=None
        self.calibrators=[]
        self.epoch=None
        self.mwatime=None
        self.Tsky=None
        self.inttime=None
        self.fine_channel=None
        self.TEC=None
        self.RM=None
        
        self._MWA_Setting=None
        self._RFstream=None
        self._Schedule_Metadata=None
        self.db=db

        self.ionex=ionex

        # this is GPS seconds
        self.observation_number=int(observation_number)


    ##################################################
    def __str__(self):
        if (self.observation_number is None):
            return "None"
        s='%s at %d (GPS)\n' % (self.filename,self.observation_number)
        s+='%d (%04d/%02d/%02d) %02d:%02d:%02d (epoch=%.3f), for %d s (Sun at %.1f deg)\n' % (self.MJD,self.year,
                                                                                              self.month,self.day,
                                                                                              self.hour,self.minute,self.second,
                                                                                              self.epoch,
                                                                                              self.duration,
                                                                                              self.sun_elevation)
        if self.center_channel is not None:
            s+='Channels: %s (center=%d)\n' % ((','.join([str(x) for x in self.channels])),self.center_channel)
        if self.inttime is not None and self.fine_channel is not None:
            s+='IntTime: %.1f s; FreqRes: %d kHz\n' % (self.inttime,
                                                       self.fine_channel)
        if (self.LST is not None and self.HA is not None):
            s+='LST=%.3f deg (HA=%s)\n' % (self.LST,
                                           ephem_utils.dec2sexstring(self.HA,digits=0,roundseconds=1))
        if (self.azimuth is not None):
            s+='(Az,El) = (%.3f, %.3f) deg\n' % (self.azimuth,self.elevation)
        if (self.RA is not None):
            s+='(RA,Dec) = (%.3f, %.3f) deg (J2000)\n' % (self.RA,self.Dec)
        if (len(self.delays)>0 and _useplotting):
            Tx,Ty=primarybeammap.get_skytemp('%04d%02d%02d%02d%02d%02d' % (
                self.year,self.month,self.day,self.hour,self.minute,self.second)
                                             ,self.delays,self.center_channel*1.28,verbose=False)
            s+='Sky Temp (X,Y) = (%.1f, %.1f) K\n' % (Tx,Ty)
        if (len(self.receivers)>0):
            s+='receivers = %s\n' % (','.join([str(x) for x in self.receivers]))
        if (len(self.delays)>0):
            s+='delays = %s\n' % (','.join([str(x) for x in self.delays]))
        if (self.calibration is not None):
            if (self.calibration):
                s+='calibration = True' + ' [' + self.calibrators + ']\n'
            else:
                s+='calibration = False\n'
        if self.TEC is not None:
            s+='Zenith TEC = %.1f TECU\n' % self.TEC
        if self.RM is not None:
            s+='Zenith Rotation Measure = %.2f rad/m^2\n' % self.RM
        return s

    ##################################################
    def __setattr__(self, name, value):
        self.__dict__[name]=value

        if (name == 'observation_number' and value is not None):
            # if the observation_number is set, compute everything else
            
            self._settimes_fromgps()

            if (self.db is None):
                return

            try:
                self._MWA_Setting=schedule.MWA_Setting(self.observation_number,db=self.db)
            except (psycopg2.InternalError, psycopg2.ProgrammingError) , e:
                logger.warning('Database error=%s' % (e.pgerror))
                db.rollback()
            if (self._MWA_Setting.stoptime == 0):
                logger.error('MWA_Setting for %d has stoptime=0' % (self.observation_number))
                             
            self.duration=self._MWA_Setting.stoptime-self._MWA_Setting.starttime
            self.filename=self._MWA_Setting.obsname
            try:
                self.inttime=self._MWA_Setting.int_time
                self.fine_channel=self._MWA_Setting.freq_res
            except:
                pass

            try:
                self._RFstream=schedule.RFstream(self.observation_number,db=self.db)
            except (psycopg2.InternalError, psycopg2.ProgrammingError) , e:
                logger.warning('Database error=%s' % (e.pgerror))
                db.rollback()

            # Set the frequency data here, there's no reason the receiver commands would
            # ever contain different values:    (AW)
            try:
                self.center_channel=self._RFstream.frequencies[len(self._RFstream.frequencies)/2]
                self.channels=self._RFstream.frequencies
            except IndexError:
                self.center_channel=None     

            try:
                self._Schedule_Metadata=schedule.Schedule_Metadata(self.observation_number,db=self.db)
                self.calibration=self._Schedule_Metadata.calibration
                self.calibrators=self._Schedule_Metadata.calibrators
            except (psycopg2.InternalError, psycopg2.ProgrammingError) , e:
                logger.warning('Database error=%s' % (e.pgerror))
                db.rollback()

            mwa=ephem_utils.Obs[ephem_utils.obscode['MWA']]

            if (self._RFstream.ra is not None):
                logger.info('Found (RA,Dec) in RFstream (%.5f,%.5f)\n' % (
                    self._RFstream.ra,self._RFstream.dec))
                self.RA=self._RFstream.ra
                self.Dec=self._RFstream.dec
                mwatime=ephem_utils.MWATime(gpstime=self.observation_number)

                self.azimuth,self.elevation=ephem_utils.radec2azel(self.RA,self.Dec,
                                                                   self.observation_number)
                self.HA=ephem_utils.HA(self.LST,self.RA,self.Dec,self.epoch)/15.0
 
            elif (self._RFstream.azimuth is not None):
                logger.info('Found (Az,El) in RFstream (%.5f,%.5f)\n' % (
                    self._RFstream.azimuth,self._RFstream.elevation))
                self.azimuth=self._RFstream.azimuth
                self.elevation=self._RFstream.elevation
                self.RA,self.Dec=ephem_utils.azel2radec(self.azimuth,self.elevation,
                                                        self.observation_number)
                self.HA=ephem_utils.HA(self.LST,self.RA,self.Dec,self.epoch)/15.0
                
            elif (self._RFstream.hex is not None and len(self._RFstream.hex)>0):
                logger.info('Found delays in RFstream (%s)\n' % (
                    self._RFstream.hex))

                self.delays=[int(x) for x in self._RFstream.hex.split(',')]
                self.azimuth,za=delays2azza(self.delays)
                self.elevation=90-za
                self.RA,self.Dec=ephem_utils.azel2radec(self.azimuth,self.elevation,
                                                        self.observation_number)
                self.HA=ephem_utils.HA(self.LST,self.RA,self.Dec,self.epoch)/15.0
            else:
                logger.warning('No coordinate specified in RFstream:\n %s\n' % self._RFstream)

            if (len(self.delays)==0):
                # still need to get the delays                
                # figure out active receivers
                
                try:
                    active_receivers = dbobj.execute('select receiver_id from receiver_info where active = true and begintime < %d and endtime > %d' % (
                        self.observation_number,self.observation_number), db=db)
                except (psycopg2.InternalError, psycopg2.ProgrammingError) , e:
                    logger.warning('Database error=%s' % (e.pgerror))
                    db.rollback()

                self.receivers=[x[0] for x in active_receivers]
                if (len(active_receivers)==0):
                    logger.warning('Unable to identify active receivers for starttime=%d\n' % (self.observation_number))
                if len(self.receivers)>0:

                    for rx in xrange(len(self.receivers)):
                        recv_cmds=schedule.Obsc_Recv_Cmds(keyval=(self.receivers[rx],self.observation_number,),db=db)
                        if (recv_cmds.stoptime == 0):
                            logger.warning('Unable to get Receiver Commands for Rx=%d, starttime=%d\n' % (
                                self.receivers[rx],self.observation_number))
                            try:
                                new_starttime=dbobj.execute('select starttime from obsc_recv_cmds where rx_id=%d and observation_number=%d' % (
                                    self.receivers[rx],self.observation_number), db=db)[0][0]
                                logger.info('Found Receiver Commands for Rx=%d, starttime=%d\n' % (
                                    self.receivers[rx],new_starttime))

                                if new_starttime != self.observation_number:
                                    recv_cmds=schedule.Obsc_Recv_Cmds(keyval=(self.receivers[rx],new_starttime,),db=db)
                                if (recv_cmds.stoptime == 0):
                                    logger.warning('Unable to get Receiver Commands for Rx=%d, starttime=%d\n' % (
                                        self.receivers[rx],new_starttime))

                                
                            except (psycopg2.InternalError, psycopg2.ProgrammingError) , e:
                                logger.warning('Database error=%s' % (e.pgerror))
                                db.rollback()               
                            except IndexError:
                                logger.warning('Unable to get Receiver Commands for Rx=%d, observation_number=%d\n' % (
                                        self.receivers[rx],self.observation_number))


                        
                        if (recv_cmds.stoptime > 0):
                            try:
                                for i in xrange(len(recv_cmds.xdelaysetting)):
                                    if not (numpy.array(recv_cmds.xdelaysetting[i])==32).any():
                                        self.delays=recv_cmds.xdelaysetting[i]
                                        break
                                    if not (numpy.array(recv_cmds.ydelaysetting[i])==32).any():
                                        self.delays=recv_cmds.ydelaysetting[i]
                                        break

                                if len(self.delays)>0:
                                    logger.info('Found delays in Obsc_Recv_Cmds for Rx %d, Slot %d (%s)\n' % (self.receivers[rx],
                                                                                                              i,
                                                                                                              ','.join([str(x) for x in self.delays])))
                                    break
                            except:
                                logger.warning('Unable to get xdelaysettings from Receiver Commands for Rx=%d, starttime=%d\n' % (self.receivers[rx],self.observation_number))
                                self.delays=[0]*16
                if len(self.delays)==0:
                    logger.warning('Unable to find a valid delay setting')
                    self.delays=[0]*16
                
                
    ##################################################
    def _settimes_fromgps(self):
        """
        _settimes_fromgps(self)
        if the observation number (starttime) is set, determine the rest of the times (MJD, UTC)
        also figure out LST, Sun altitude
        """

        if (self.observation_number is None):
            logger.error('Cannot set times without an observation_number')
        else:
            self.mwatime=ephem_utils.MWATime(gpstime=self.observation_number)
            self.MJD=int(self.mwatime.MJD)
            self.UT=self.mwatime.UT
            self.year=self.mwatime.year
            self.month=self.mwatime.month
            self.day=self.mwatime.day
            self.hour=self.mwatime.hour
            self.minute=self.mwatime.minute
            self.second=self.mwatime.second
            self.LST=float(self.mwatime.LST)
            self.epoch=self.mwatime.epoch

            mwa=ephem_utils.Obs[ephem_utils.obscode['MWA']]
            observer=ephem.Observer()
            # make sure no refraction is included
            observer.pressure=0
            observer.long=mwa.long/ephem_utils.DEG_IN_RADIAN
            observer.lat=mwa.lat/ephem_utils.DEG_IN_RADIAN
            observer.elevation=mwa.elev
            observer.date='%d/%d/%d %s' % (self.year,self.month,self.day,
                                           self.mwatime.strftime("%H:%M:%S"))

            body=ephem.__dict__['Sun']()
            body.compute(observer)
            self.sun_elevation=body.alt*ephem_utils.DEG_IN_RADIAN

            if _USE_IONEX and self.ionex:
                i=ionex.ionexmaps(self.observation_number)
                self.TEC=i(self.observation_number)
                self.RM=i.RM(self.observation_number)

            
        
######################################################################
def find_observation_num(filename, maxdiff=10, suffix='_das1.LACSPC', db=db):
    """
    observation_num=find_observation_num(filename, maxdiff=10, suffix='_das1.LACSPC', db=db)
    finds a scheduled MWA_Setting object at the time nearest the UT date/time
    in filename (YYYYMMDDhhmmss)
    that has a valid stoptime
    will search up to +/-maxdiff seconds
    """
    
    observation_num=return_observation_num(filename,suffix=suffix,db=db)
    if (observation_num is not None):
        # we found it exactly in the database
        logger.info('Found a match to %s%s in the data_files database at time=%d\n' % (filename,suffix,observation_num))
        return observation_num

        

    # otherwise, try to parse
    d=filename.split('_')
    datetimestring=None
    for x in d:
        if (len(x)==14):
            datetimestring=x
            try:
                yr=int(datetimestring[0:4])
                mn=int(datetimestring[4:6])
                dy=int(datetimestring[6:8])
                h=int(datetimestring[8:10])
                m=int(datetimestring[10:12])
                s=int(datetimestring[12:14])
                continue
            except:
                pass
    try:
        mwatime=ephem_utils.MWATime(year=yr,month=mn,day=dy,hour=h,minute=m,second=s)
        oid=mwatime.gpstime
    except:
        logger.warning('Cannot determine GPS time for file=%s\n' % (filename))
        return None
    oid=find_closest_observation(int(oid),maxdiff=maxdiff,db=db)
    return oid

######################################################################
def return_observation_num(filename,suffix='_das1.LACSPC',db=db):
    """
    observation_num=return_observation_num(filename,suffix='_das1.LACSPC',db=db)
    searches for exact matches in MWA_Data_Files table
    """
    file=schedule.MWA_Data_Files(keyval=(filename + suffix),db=db)
    if (file.size == 0):
        return None
    else:
        return file.observation_num

######################################################################
def find_closest_observation(gpstime, maxdiff=10,db=db):
    """
    observation_num=find_closest_observation(gpstime, maxdiff=10,db=db)
    finds a scheduled MWA_Setting object at the time nearest the gpstime
    that has a valid stoptime
    will search up to +/-maxdiff seconds
    """
    if schedule.MWA_Setting(int(gpstime),db=db).stoptime > 0:
        logger.info('Found matching observation in MWA_Setting database at GPS time=%d\n' % (gpstime))
        return gpstime
    for searchtime in xrange(int(gpstime)-maxdiff, int(gpstime)+maxdiff+1):
        if schedule.MWA_Setting(int(searchtime),db=db).stoptime > 0:
            logger.info('Found matching observation for GPS time %d in MWA_Setting database at GPS time=%d (difference=%d s)\n' % (
                gpstime,searchtime,searchtime-gpstime))
            return searchtime
    return None




##################################################
def delays2azza(xx):
    """
    # From Chris Williams
    # receiverStatusPy/StatusTools.py
    ################################
    # delays2azza(xx)
    #
    # This takes a 16-element integer array of delay settings (each element of the array xx should be an integer from 0 to 31 in
    # units of the delay step on the delay boards).  It uses several triangles of elements to determine roughly what the pointing
    # direction is from the delay settings that the beamformer has
    #
    # It returns a tuple containing (average azimuth, average zenith angle) determined by averaging the angles determined by the
    # selected triangles
    """
    dip_sep=1.10
    delaystep=435 # delay in picoseconds
    dtor=0.0174532925
    
    azs=[]
    zas=[]

    #choose triangles to back out the delays...

    ii=[0,0,3,0]
    jj=[15,15,12,3]
    kk=[12,3,15,12]

    for a in range(len(ii)):

        i=ii[a]
        j=jj[a]
        k=kk[a]
        
        d1=delaystep*xx[i]
        ox1=(-1.5+(i%4)*1.0)*dip_sep
        oy1=(1.5-math.floor(i/4))*dip_sep
        
        d2=delaystep*xx[j]
        ox2=(-1.5+(j%4)*1.0)*dip_sep
        oy2=(1.5-math.floor(j/4))*dip_sep
        
        d3=delaystep*xx[k]
        ox3=(-1.5+(k%4)*1.0)*dip_sep
        oy3=(1.5-math.floor(k/4))*dip_sep
        
        az,za=triangulate(d1,ox1,oy1,d2,ox2,oy2,d3,ox3,oy3)
        
        if az is not None:
            azs.append(az)
            zas.append(za)
        else:
            #Bad triangle...
            #logging.warning("Bad delay triangle: %i %i %i"%(i,j,k))
            pass
    if len(azs)==0 or len(zas)==0:
        logging.warning("Can't triangulate a pointing...")
        return None,None
    else:
        azavg=sum(azs)/len(azs)
        zaavg=sum(zas)/len(zas)

    return azavg,zaavg

##################################################
def triangulate(d1,ox1,oy1,d2,ox2,oy2,d3,ox3,oy3):
    """
    ################################
    # triangulate(d1,ox1,oy1,d2,ox2,oy2,d3,ox3,oy3)
    #
    # This function triangulates the azimuth and zenith angle from 3 positions/delays of dipoles on a tile
    #
    # d1,d2,d3 are the delays (in picoseconds) between the three elements
    # ox[1,2,3] are the x position offsets between the 3 elements
    # oy[1,2,3] are the y position offsets between the 3 elements
    #
    # It returns a tuple which contains the (azimuth, zenith angle) in degrees
    # that is pointed at by the combination of 3 elements (its the intersection of 3 great circles)
    # It will return (None,None) if the triangle is colinear (i.e. not a triangle!)
    """

    dtor=0.0174532925
    c=0.000299798 # c in m/picosecond

    try:
        # take the arctan to get the azimuth
        az=math.atan2((d3-d1)*(oy2-oy1)-(d2-d1)*(oy3-oy1),(d2-d1)*(ox3-ox1)-(d3-d1)*(ox2-ox1))

        if d1-d2 == 0 and d1-d3 == 0:
            return 0.0,0.0

        if abs((ox2-ox3)*math.sin(az)+(oy2-oy3)*math.cos(az)) > 1e-15: #check if the triangle is bad (if its colinear)
            za=math.asin((d2-d3)*c/((ox2-ox3)*math.sin(az)+(oy2-oy3)*math.cos(az)))
        elif abs((ox1-ox3)*math.sin(az)+(oy1-oy3)*math.cos(az)) > 1e-15:
            za=math.asin((d1-d3)*c/((ox1-ox3)*math.sin(az)+(oy1-oy3)*math.cos(az)))
        else:
            return None,None
        azd=az/dtor
        zad=za/dtor
    except:
        #if there are math range errors, return None
        return None,None

    if zad < 0:
        zad*=-1
        azd+=180
    while azd <0:
        azd+=360
    while azd >= 360:
        azd-=360
    return azd,zad

    
