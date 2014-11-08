#!/usr/bin/env python

"""
ephem_utils.py

python classes/routines to implement various ephemeris/source position related routines

-) Make sure hourangle definition is correct
   should be HA=LST-RA
   or RA=LST-HA


$Rev$:     Revision of last commit
$Author$:  Author of last commit
$Date$:    Date of last commit


"""


import os, sys, string, re, types, math, copy, logging
import getopt,datetime,pytz
import time
import numpy
import ephem
#####################################################################
# Constants    

dow={0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri', 5: 'Sat', 6: 'Sun'}
# J2000.0 in MJD
J2000=51544.5
DEG_IN_RADIAN=180/math.pi
HRS_IN_RADIAN=180/math.pi/15
# equatorial radius of earth, meters
EQUAT_RAD=6378137.0
SEC_IN_DAY=86400
# flattening of earth, 1/298.257
FLATTEN=0.003352813
# GPS seconds defined as seconds since Jan 06, 1980
# this is MJD 44244
# what about leap seconds?
GPSseconds_MJDzero=44244.0

# from time.sql
# written by EHM
# data for GPSseconds to UTC conversion
# containing the UTC dates that various leapseconds occured
# updated by CW
# updated 2012-08-22 by DLK
MJD_Start=[49169, 49534, 50083, 50630, 51179, 53736,54832, 56109]
MJD_End=[49534, 50083, 50630, 51179, 53736, 54832, 56109, 99999]
GPSseconds_Start=[425520008, 457056009, 504489610, 551750411, 599184012, 820108813,914803214,1025136016]
GPSseconds_End=[457056009, 504489610, 551750411, 599184012,820108813, 914803214, 1025136016,9223372036854775807]
Offset_seconds=[315964791, 315964790, 315964789, 315964788, 315964787, 315964786, 315964785,315964784]


"""
New routines to convert to/from gps time
uses only the list of leap seconds and built-in python utilities

dates of leap seconds
http://en.wikipedia.org/wiki/Leap_second
Updated 2012-09-18
"""
Leapseconds=[datetime.datetime(1972, 06, 30,0,0,0,0,pytz.utc),
             datetime.datetime(1972, 12, 31,0,0,0,0,pytz.utc),
             datetime.datetime(1973, 12, 31,0,0,0,0,pytz.utc),
             datetime.datetime(1974, 12, 31,0,0,0,0,pytz.utc),
             datetime.datetime(1975, 12, 31,0,0,0,0,pytz.utc),
             datetime.datetime(1976, 12, 31,0,0,0,0,pytz.utc),
             datetime.datetime(1977, 12, 31,0,0,0,0,pytz.utc),
             datetime.datetime(1978, 12, 31,0,0,0,0,pytz.utc),
             datetime.datetime(1979, 12, 31,0,0,0,0,pytz.utc),
             datetime.datetime(1981, 06, 30,0,0,0,0,pytz.utc),
             datetime.datetime(1982, 06, 30,0,0,0,0,pytz.utc),
             datetime.datetime(1983, 06, 30,0,0,0,0,pytz.utc),
             datetime.datetime(1985, 06, 30,0,0,0,0,pytz.utc),
             datetime.datetime(1987, 12, 31,0,0,0,0,pytz.utc),
             datetime.datetime(1989, 12, 31,0,0,0,0,pytz.utc),
             datetime.datetime(1990, 12, 31,0,0,0,0,pytz.utc),
             datetime.datetime(1992, 06, 30,0,0,0,0,pytz.utc),
             datetime.datetime(1993, 06, 30,0,0,0,0,pytz.utc),
             datetime.datetime(1994, 06, 30,0,0,0,0,pytz.utc),
             datetime.datetime(1995, 12, 31,0,0,0,0,pytz.utc),
             datetime.datetime(1997, 06, 30,0,0,0,0,pytz.utc),
             datetime.datetime(1998, 12, 31,0,0,0,0,pytz.utc),
             datetime.datetime(2005, 12, 31,0,0,0,0,pytz.utc),
             datetime.datetime(2008, 12, 31,0,0,0,0,pytz.utc),
             datetime.datetime(2012, 06, 30,0,0,0,0,pytz.utc)]
# this is when GPStime=0 is defined
GPSzero=datetime.datetime(1980,1,6,0,0,0,0,pytz.utc)
Leapinterval_Start=[datetime.datetime(1960,1,1,0,0,0,0,pytz.utc)]
Leapinterval_End=[]
SumLeapseconds=[0]
for ls in Leapseconds:
    Leapinterval_End.append(ls)
    SumLeapseconds.append(SumLeapseconds[-1]+1)
    Leapinterval_Start.append(ls)

Leapinterval_End.append(datetime.datetime(2015,1,1,0,0,0,0,pytz.utc))
# number of leap seconds that had already elapsed at GPStime=0
GPSzero_leapseconds=SumLeapseconds[numpy.where(numpy.array(Leapinterval_Start)<=GPSzero)[0][-1]]
Leapinterval_Start_GPS=[]
Leapinterval_End_GPS=[]
ls=0
for i in xrange(len(Leapinterval_Start)):
    dt=Leapinterval_Start[i]-GPSzero+datetime.timedelta(seconds=ls-GPSzero_leapseconds)
    Leapinterval_Start_GPS.append(dt.days*86400 + dt.seconds)
    dt=Leapinterval_End[i]-GPSzero+datetime.timedelta(seconds=ls-GPSzero_leapseconds)
    Leapinterval_End_GPS.append(dt.days*86400 + dt.seconds)
    ls=SumLeapseconds[i]        


##################################################
def mjd_datetime(mjd,ut=0):
    """
    datetime=mjd_datetime(mjd,ut=0)
    """
    y,m,d=mjd_cal(mjd)
    [hr,min,sec]=dec2sex(ut)
    return datetime.datetime(int(y),int(m),int(d),int(hr),int(min),int(sec),int(1e6*(sec-int(sec))),pytz.utc)
##################################################
def datetime_mjd(dt):
    """
    mjd,ut=datetime_mjd(dt)
    """
    mjd=cal_mjd(dt.year,dt.month,dt.day)
    ut=dt.hour + dt.minute/60.0 + dt.second/3600.0
    return mjd,ut
##################################################
def datetime_gps(t):
    """
    gps=datetime_gps(t)
    converts from datetime.datetime t to gps seconds
    """
    ls=SumLeapseconds[numpy.where(numpy.array(Leapinterval_Start)<=t)[0][-1]]
    dt=t-GPSzero+datetime.timedelta(seconds=(ls-GPSzero_leapseconds))
    return 86400*dt.days + dt.seconds
##################################################
def gps_datetime(gps):
    """
    datetime=gps_datetime(gps)
    converts from gps seconds to datetime.datetime
    """
    ls=SumLeapseconds[numpy.where(numpy.array(Leapinterval_Start_GPS)<=gps)[0][-1]]
    dt=datetime.timedelta(seconds=gps-(ls-GPSzero_leapseconds))
    return GPSzero + dt

######################################################################
# OBJECT DEFINITIONS
######################################################################



######################################################################
class Observatory(object):

    def __init__(self,code='NULL',name='None',long=0,lat=0,elev=0,stdtz=0,use_dst=0,stcode="X"):
        self.lat=checksex(lat)
        self.long=checksex(long)
        self.name=name
        self.code=code
        self.elev=elev
        self.stdtz=stdtz
        self.use_dst=use_dst
        self.year=0
        self.tz=stdtz
        self.stcode=stcode
        # now compute derived quantity "horiz" = depression of horizon
        self.horiz=math.sqrt(2*self.elev/EQUAT_RAD)*DEG_IN_RADIAN

    ##################################################
    def __str__(self):
        s="Observatory %s: %s at (%s,%s)\n" % (self.code,self.name,dec2sexstring(self.long,digits=-1),dec2sexstring(self.lat,1,digits=-1))
        if (self.tz > 0):
            tzsign='-'
            tzval=self.tz
        else:
            tzsign='+'
            tzval=-self.tz
        s2="\tElev=%d m, Time=UT%s%d h, DST_Conv=%s (DST=%d)" % (self.elev,tzsign,tzval,self.dst_string(),not self.tz==self.stdtz)
        return "%s %s" % (s,s2)

    ##################################################
    def dst_string(self):
        if (self.use_dst==1):
            return 'US'
        if (self.use_dst==-1):
            return 'Chile'
        if (self.use_dst==0):
            return 'None'
        if (self.use_dst==-2):
            return 'Australia'

######################################################################
class Time(Observatory):

    def __init__(self,obs=None):
        self.isinit=0
        self.obs=obs
        self.MJD=0
        self.LST=0
        self.utmlt=0
        self.isdst=0
        self.UT=0
        self.LT=0
        self.__dict__['GPSseconds']=0
        self.epoch=mjd_to_epoch(self.MJD)
        if (self.obs==None):
            self.LTtype="XST"
        else:
            self.LTtype="%sST" % (self.obs.stcode)

    ##################################################
    def __str__(self):
        s=str(self.obs)
        [yr,mn,dy]=mjd_cal(self.MJD)
        s+="\nMJD %.1f %d-%02d-%02d UT=%s %s=%s LMST=%s GPSseconds=%.1f" % (self.MJD+self.UT/24.0,yr,mn,dy,dec2sexstring(self.UT),self.LTtype,dec2sexstring(self.LT),dec2sexstring(self.LST),self.GPSseconds)
        if (not self.isinit):
            s+="\nTime not initialized!"
        return s

    ##################################################
    def __repr__(self):
        return str(self)

    ##################################################
    def calctz(self):
        [yr,mn,dy]=mjd_cal(self.MJD)
        [mjdb,mjde]=find_dst_bounds(yr,self.obs.stdtz,self.obs.use_dst)
        self.utmlt=zonetime(self.obs.use_dst,self.obs.stdtz,self.MJD,mjdb,mjde)
        if (self.utmlt != self.obs.stdtz):
            self.isdst=1
            self.LTtype="%sDT" % (self.obs.stcode)
        self.obs.year=yr
        self.obs.tz=self.utmlt
        self.isinit=1

    ##################################################
    def __getattr__(self,name):
        if (not self.__dict__.has_key(name)):
            try:
                return self.obs.__dict__[name]
            except (AttributeError,TypeError):
                logging.warning("Attribute %s not defined for class Time" % name)
                return None
        else:
            return self.__dict__[name]

        
    ##################################################
    def __setattr__(self,name,value):
        if (name == "UT"):
            # if we assign a value to UT
            # update LT, MJD (if necessary), epoch, and LST
            self.__dict__[name]=putrange(value)
            #while (value<0):
            #    self.MJD-=1
            #    value+=24
            #while (value>=24):
            #    self.MJD+=1
            #    value-=24
            self.epoch=mjd_to_epoch(self.MJD+value/24.0)
            if (self.obs != None):
                self.__dict__["LT"]=putrange(value-self.utmlt)
                self.LST=utc_lmst(self.MJD+value/24.0,self.obs.long)
            if (self.isinit):
                self.setGPSseconds()
        elif (name == "LT"):
            # if we assign a value to LT
            # update UT and thereby LST
            self.__dict__[name]=putrange(value)
            self.UT=value+self.utmlt
            if (self.isinit):
                self.setGPSseconds()
        elif (name == "GPSseconds"):
            # if we assign a time in GPS seconds
            self.__dict__[name]=value
            self.setutGPS()
        else:
            self.__dict__[name]=value



    ##################################################
    def init(self,MJD,time,islt=1):
        """ initialize a time instance
        this involves setting the date (MJD) and time (local or UT)
        then determining the appropriate time zone
        then resetting the date & time
        then calculating LST
        """
        self.MJD=MJD
        if (islt):
            self.LT=time
        else:
            self.UT=time        
        self.calctz()
        self.MJD=MJD
        if (islt):
            self.LT=time
        else:
            self.UT=time        
        self.setGPSseconds()

    ##################################################
    def init_datetime(self,d):
        """
        initializes the Time data from the information
        in the datetime.datetime object d
        """
        if (not d.tzinfo):
            # the timezone info is null: assume UT
            # (I think this is not always true: often the TZ info is just
            # not properly set, even if it's not UT)
            self.init(cal_mjd(d.year,d.month,d.day),d.hour+d.minute/60.0+d.second/3600.0+d.microsecond/3600.0/1e6,islt=0)
        else:
            # don't know how to handle it
            logging.warning("Unknown timezone information for datetime %s: %s...\n" % (d,d.tzinfo))
                          
    ##################################################
    def datetime(self):
        """
        returns the date/time information in self as a datetime.datetime object
        gives data in UT
        """
        [yr,mn,dy]=mjd_cal(self.MJD)
        [hr,min,sec]=dec2sex(self.UT)
        usec=int(sec*1e6)        
        d=datetime.datetime(yr,mn,dy,hr,min,int(sec),usec,None)
        return d
    

    ##################################################
    def setGPSseconds(self):
        """
        set GPSseconds based on a MJD and UT time
        """
        self.__dict__["GPSseconds"]=calcGPSseconds(self.MJD,self.UT)

    ##################################################
    def setutGPS(self):
        """
        set UT time based on GPS seconds
        """
        [MJD,UT]=calcUTGPSseconds(self.GPSseconds)
        self.setut(MJD,UT)
        
    ##################################################
    def setut(self,mjd,ut):
        self.MJD=mjd
        self.UT=ut
        if (self.UT<0):
            self.MJD-=1
            self.UT+=24
        if (self.UT>=24):
            self.MJD+=1
            self.UT-=24
        self.LT=self.UT-self.utmlt
        self.LT=putrange(self.LT)
        self.LST=utc_lmst(self.MJD+self.UT/24.0,self.obs.long)
        self.epoch=mjd_to_epoch(self.MJD)
        self.setGPSseconds()

    ##################################################        
    def setlt(self,mjd,lt):
        self.MJD=mjd
        self.LT=lt
        self.UT=self.LT+self.utmlt
        if (self.UT<0):
            self.MJD-=1
            self.UT+=24
        if (self.UT>=24):
            self.MJD+=1
            self.UT-=24
        if (self.LT<0):
            self.LT+=24
        if (self.LT>=24):
            self.LT-=24            

        self.LST=utc_lmst(self.MJD+self.UT/24.0,self.obs.long)
        self.epoch=mjd_to_epoch(self.MJD)
        self.setGPSseconds()


    ##################################################
    def zenith(self):
        """
        zenith=zenith()
        returns an Object containing the  RA(hrs) and Dec(deg) of the zenith
        """
        s="Zenith for %s at MJD %.1f (UT)" % (self.obs.name,self.MJD+self.UT/24.0)
        return Object(s,self.LST,self.lat)

    ##################################################
    def copy(self):
        t=Time(self.obs)
        t.init(self.MJD,self.UT,islt=0)
        return t

######################################################################
# COORDINATE ROUTINES
######################################################################


######################################################################
def xyz_cel(x,y,z):
    """ cartesian coordinate triplet 
    returns corresponding right ascension and declination,
    in decimal hours & degrees.
    """

    mod=math.sqrt(x*x+y*y+z*z)
    if (mod>0):
        x/=mod
        y/=mod
        z/=mod
    else:
        return (0,0)
    xy=math.sqrt(x*x+y*y)
    if (xy<1e-11):
        # on the pole
        ra=0
        dec=math.pi/2
        if (z<0):
            z*=-1
    else:
        dec=math.asin(z)
        ra=math.atan2(y,x)

    ra*=(180/math.pi)/15
    ra=putrange(ra)
    dec*=180/math.pi

    return (ra,dec)    

######################################################################
def angulardistance(ra1,dec1,ra2,dec2):
    """ input in decimal hours,degrees
    angle separating by two positions in the sky --
    return value is in radians.  Hybrid algorithm works down
    to zero separation except very near the poles.
    
    from skycalcv5"""

    if (not isinstance(ra1,numpy.ndarray) and not isinstance(dec1,numpy.ndarray) and not isinstance(ra2,numpy.ndarray) and not isinstance(dec2,numpy.ndarray)):
        ra1 = ra1 / HRS_IN_RADIAN
        dec1 = dec1 / DEG_IN_RADIAN
        ra2 = ra2 / HRS_IN_RADIAN
        dec2 = dec2 / DEG_IN_RADIAN
        x1 = math.cos(ra1)*math.cos(dec1)
        y1 = math.sin(ra1)*math.cos(dec1)
        z1 = math.sin(dec1)
        x2 = math.cos(ra2)*math.cos(dec2)
        y2 = math.sin(ra2)*math.cos(dec2)
        z2 = math.sin(dec2)
        arg=x1*x2+y1*y2+z1*z2
        if (arg>1):
            arg=1
        if (arg<-1):
            arg=-1
        theta = math.acos(arg)
        # use flat Pythagorean approximation if the angle is very small
        # *and* you're not close to the pole; avoids roundoff in arccos.
        if (theta<1e-5):
            if (math.fabs(dec1)<(math.pi/2-1e-3) and (math.fabs(dec2)<math.pi/2-1e-3)):
                x1=(ra2-ra1)*math.cos(0.5*(dec1+dec2))
                x2=dec2-dec1
                theta=math.sqrt(x1*x1+x2*x2)
        return theta
    else:
        # numpy version
        # promote all elements as necessary
        ra1 = numpy.array(ra1) / HRS_IN_RADIAN
        dec1 = numpy.array(dec1) / DEG_IN_RADIAN
        ra2 = numpy.array(ra2) / HRS_IN_RADIAN
        dec2 = numpy.array(dec2) / DEG_IN_RADIAN
        x1 = numpy.cos(ra1)*numpy.cos(dec1)
        y1 = numpy.sin(ra1)*numpy.cos(dec1)
        z1 = numpy.sin(dec1)
        x2 = numpy.cos(ra2)*numpy.cos(dec2)
        y2 = numpy.sin(ra2)*numpy.cos(dec2)
        z2 = numpy.sin(dec2)
        arg=x1*x2+y1*y2+z1*z2
        arg[arg>1]=1
        arg[arg<-1]=-1
        theta = numpy.arccos(arg)
        x1=(ra2-ra1)*numpy.cos(0.5*(dec1+dec2))
        x2=dec2-dec1
        theta2=numpy.sqrt(x1*x1+x2*x2)

        # use flat Pythagorean approximation if the angle is very small
        # *and* you're not close to the pole; avoids roundoff in arccos.
        condition=(theta<1e-5)*(numpy.abs(dec1)<(math.pi/2-1e-3))*(numpy.abs(dec2)<(math.pi/2-1e-3))
        d=numpy.where(condition,theta2,theta)

        #for i in xrange(len(self)):
        #    d[i]=self[i].distance(obj)
        return d


######################################################################
def azel2radec(Az,El,gpstime):
    """
    [RA,Dec]=azel2radec(Az,El,gpstime)
    horizon coords to equatorial
    all decimal degrees
    The sign convention for azimuth is north zero, east +pi/2.
    positions are J2000
    """

    mwa=Obs[obscode['MWA']]
    [MJD,UT]=calcUTGPSseconds(gpstime)
    [yr,mn,dy]=mjd_cal(MJD)
    UTs=dec2sexstring(UT,digits=0,roundseconds=1)
    observer=ephem.Observer()
    # make sure no refraction is included
    observer.pressure=0
    observer.long=mwa.long/DEG_IN_RADIAN
    observer.lat=mwa.lat/DEG_IN_RADIAN
    observer.elevation=mwa.elev
    observer.date='%d/%d/%d %s' % (yr,mn,dy,UTs)
    observer.epoch=ephem.J2000
    
    ra,dec=observer.radec_of(Az/DEG_IN_RADIAN,El/DEG_IN_RADIAN)
    return ra*DEG_IN_RADIAN,dec*DEG_IN_RADIAN

######################################################################
def radec2azel(RA,Dec,gpstime):
    """
    Az,El=radec2azel(RA,Dec,gpstime)
    equatorial to horizon coords 
    all decimal degrees
    The sign convention for azimuth is north zero, east +pi/2.
    positions are J2000
    """

    mwa=Obs[obscode['MWA']]
    [MJD,UT]=calcUTGPSseconds(gpstime)
    [yr,mn,dy]=mjd_cal(MJD)
    UTs=dec2sexstring(UT,digits=0,roundseconds=1)
    observer=ephem.Observer()
    # make sure no refraction is included
    observer.pressure=0
    observer.long=mwa.long/DEG_IN_RADIAN
    observer.lat=mwa.lat/DEG_IN_RADIAN
    observer.elevation=mwa.elev
    observer.date='%d/%d/%d %s' % (yr,mn,dy,UTs)
    observer.epoch=ephem.J2000

    body=ephem.FixedBody()
    body._ra=RA/DEG_IN_RADIAN
    body._dec=Dec/DEG_IN_RADIAN
    body._epoch=ephem.J2000
    body.compute(observer)

    return body.az*DEG_IN_RADIAN,body.alt*DEG_IN_RADIAN

######################################################################
def horz2eq(Az,El,lat):
    """
    [HA,Dec]=horz2eq(Az,El,lat)
    horizon coords to equatorial
    all decimal degrees
    The sign convention for azimuth is north zero, east +pi/2.
    from slalib sla_h2e
    https://starlink.jach.hawaii.edu/viewvc/trunk/libraries/sla/h2e.f?view=markup
    """

    if (isinstance(Az,numpy.ndarray)):
        sa=numpy.sin(Az*math.pi/180)
        ca=numpy.cos(Az*math.pi/180)
        se=numpy.sin(El*math.pi/180)
        ce=numpy.cos(El*math.pi/180)
        sl=numpy.sin(lat*math.pi/180)
        cl=numpy.cos(lat*math.pi/180)
        
        # HA,Dec as (x,y,z)
        x=-ca*ce*sl+se*cl
        y=-sa*ce
        z=ca*ce*cl+se*sl
        
        r=numpy.sqrt(x*x+y*y)
        ha=numpy.arctan2(y,x)
        ha[numpy.where(r==0)]=0

        dec=numpy.arctan2(z,r)

    else:
        sa=math.sin(Az*math.pi/180)
        ca=math.cos(Az*math.pi/180)
        se=math.sin(El*math.pi/180)
        ce=math.cos(El*math.pi/180)
        sl=math.sin(lat*math.pi/180)
        cl=math.cos(lat*math.pi/180)
        
        # HA,Dec as (x,y,z)
        x=-ca*ce*sl+se*cl
        y=-sa*ce
        z=ca*ce*cl+se*sl
        
        r=math.sqrt(x*x+y*y)
        if (r==0):
            ha=0
        else:
            ha=math.atan2(y,x)
        dec=math.atan2(z,r)
        
    return [ha*180/math.pi, dec*180/math.pi]
    
######################################################################
def eq2horz(HA, Dec, lat):
    """
    [Az,Alt]=eq2horz(HA,Dec,lat)
    equatorial to horizon coords
    all decimal degrees
    The sign convention for azimuth is north zero, east +pi/2.

    from slalib sla_e2h
    https://starlink.jach.hawaii.edu/viewvc/trunk/libraries/sla/e2h.f?revision=11739&view=markup
    https://starlink.jach.hawaii.edu/viewvc/trunk/libraries/sla/

    azimuth here is defined with N=0
    """
    
    if (isinstance(HA,numpy.ndarray)):
        sh=numpy.sin(HA*math.pi/180)
        ch=numpy.cos(HA*math.pi/180)
        sd=numpy.sin(Dec*math.pi/180)
        cd=numpy.cos(Dec*math.pi/180)
        sl=math.sin(lat*math.pi/180)
        cl=math.cos(lat*math.pi/180)
        
        # (Az,El) as (x,y,z)
        x=-ch*cd*sl+sd*cl
        y=-sh*cd
        z=ch*cd*cl+sd*sl
        
        # to spherical
        r=numpy.sqrt(x*x+y*y)
        a=numpy.arctan2(y,x)
        a[numpy.where(r==0)]=0
        a[numpy.where(a<0)]+=math.pi*2
        el=numpy.arctan2(z,r)
    else:
        sh=math.sin(HA*math.pi/180)
        ch=math.cos(HA*math.pi/180)
        sd=math.sin(Dec*math.pi/180)
        cd=math.cos(Dec*math.pi/180)
        sl=math.sin(lat*math.pi/180)
        cl=math.cos(lat*math.pi/180)
        
        # (Az,El) as (x,y,z)
        x=-ch*cd*sl+sd*cl
        y=-sh*cd
        z=ch*cd*cl+sd*sl
        
        # to spherical
        r=math.sqrt(x*x+y*y)
        if (r==0):
            a=0
        else:
            a=math.atan2(y,x)
        a=putrange(a,2*math.pi)
        el=math.atan2(z,r)

    return [a*180/math.pi, el*180/math.pi]

######################################################################
def calc_parang(ha,dec,lat):
    """ finds the parallactic angle.  This is a little
    complicated (see Filippenko PASP 94, 715 (1982)

    now supports numpy.ndarray as arguments, although it doesn't do it intelligently

    from skycalc
    """

    if (isinstance(ha,float) or isinstance(ha,int)):
        ha = ha / HRS_IN_RADIAN
        dec = dec / DEG_IN_RADIAN
        lat = lat / DEG_IN_RADIAN

        # Filippenko eqn 10 follows -- guarded against division by zero
        # at the exact zenith .... 
        denom =math.sqrt(1.-math.pow((math.sin(lat)*math.sin(dec)+math.cos(lat)*math.cos(dec)*math.cos(ha)),2.))
           
        if(denom != 0.):
            sineta = math.sin(ha)*math.cos(lat)/denom
        else:
            sineta = 0.
            
        if (lat >= 0.):
            # northern hemisphere case 
        
            # If you're south of zenith, no problem. 
        
            if(dec<lat):
                return (math.asin(sineta)*DEG_IN_RADIAN)

            else:
                # find critical hour angle -- where parallactic
                # angle becomes 90 deg.  After that,
                # take another root of expression. 
                colat = math.pi /2. - lat
                codec = math.pi /2. - dec
                hacrit = 1.-math.pow(math.cos(colat),2.)/math.pow(math.cos(codec),2.)
                hacrit = math.sqrt(hacrit)/math.sin(colat)
                if (abs(hacrit) <= 1.00):
                    hacrit = math.asin(hacrit)
                if (abs(ha) > abs(hacrit)):
                    # comes out ok at large hour angle */
                    return(math.asin(sineta)*DEG_IN_RADIAN)            
                else:
                    if (ha > 0):
                        return((math.pi - math.asin(sineta))*DEG_IN_RADIAN)
                    else:
                        return((-1.* math.pi - math.asin(sineta))*DEG_IN_RADIAN)
        else:
            # Southern hemisphere case follows 
            # If you're north of zenith, no problem. 
            if(dec>lat):
                if (ha >= 0):
                    return ((math.pi - math.asin(sineta))*DEG_IN_RADIAN)
                else:
                    return(-1*(math.pi + math.asin(sineta)) * DEG_IN_RADIAN)            
            else:
                # find critical hour angle -- where parallactic
                # angle becomes 90 deg.  After that,
                # take another root of expression. 
                colat = -1*math.pi/2. - lat
                codec = math.pi/2. - dec
                hacrit = 1.-math.pow(math.cos(colat),2.)/math.pow(math.cos(codec),2.)
                hacrit = math.sqrt(hacrit)/math.sin(colat)
                if (abs(hacrit) <= 1.00):
                    hacrit = math.asin(hacrit)
                if(abs(ha) > abs(hacrit)):
                    if(ha >= 0):
                        return((math.pi - math.asin(sineta))*DEG_IN_RADIAN)
                    else:
                        return(-1. * (math.pi + math.asin(sineta))*DEG_IN_RADIAN)
                else:
                    return(math.asin(sineta)*DEG_IN_RADIAN)
    elif (isinstance(ha,numpy.ndarray)):
        parang=numpy.zeros(ha.shape)
        for i in xrange(len(ha)):
            parang[i]=calc_parang(ha[i],dec[i],lat)
        return parang

    else:
        raise TypeError

           


######################################################################
def ha_alt(dec,lat,alt):
    """ returns hour angle at which object at dec is at altitude alt.
    If object is never at this altitude, signals with special
    return values 1000 (always higher) and -1000 (always lower).

    from skycalcv5
    """

    [min,max]=min_max_alt(lat,dec)
    if (alt<min):
        # always higher than asked
        return 1000
    if (alt>max):
        # always lower than asked
        return -1e3
    dec=math.pi/2-dec/DEG_IN_RADIAN
    lat=math.pi/2-lat/DEG_IN_RADIAN
    coalt=math.pi/2-alt/DEG_IN_RADIAN
    x=(math.cos(coalt)-math.cos(dec)*math.cos(lat))/(math.sin(dec)*math.sin(lat))
    if (math.fabs(x)<=1):
        return (math.acos(x)*HRS_IN_RADIAN)
    else:
        printerr("Error in ha_alt -- arccos(>1)\n")
        return 1e3
    
    
######################################################################
def min_max_alt(lat,dec):
    """ computes minimum and maximum altitude for a given dec and
    latitude.

    from skycalcv5
    """

    lat/=DEG_IN_RADIAN
    dec/=DEG_IN_RADIAN
    x=math.cos(dec)*math.cos(lat)+math.sin(dec)*math.sin(lat)
    if (math.fabs(x)<=1):
        max=math.asin(x)*DEG_IN_RADIAN
    else:
        printerr("Error in min_max_alt -- arcsin(>1)\n")
    x=math.sin(dec)*math.sin(lat)-math.cos(dec)*math.cos(lat)
    if (math.fabs(x)<=1):
        min=math.asin(x)*DEG_IN_RADIAN
    else:
        printerr("Error in min_max_alt -- arcsin(>1)\n")

    return (min,max)


######################################################################
def eclrot(mjd,x,y,z):
    """ rotates ecliptic rectangular coords x, y, z to
    equatorial (all assumed of date.)
    from skycalcv5
    """

    jd=mjd+2400000.5
    T=(mjd-J2000)/36525
    # 1992 Astron Almanac, p. B18, dropping the
    # cubic term, which is 2 milli-arcsec!
    incl = (23.439291 + T * (-0.0130042 - 0.00000016 * T))/DEG_IN_RADIAN
    ypr = math.cos(incl) * y - math.sin(incl) * z
    zpr = math.sin(incl) * y + math.cos(incl) * z
    # x remains the same
    return (x,ypr,zpr)

######################################################################
def geocent(geolong,geolat,height):
    """
    computes the geocentric coordinates from the geodetic
    (standard map-type) longitude, latitude, and height.
    These are assumed to be in decimal hours, decimal degrees, and
    meters respectively.  Notation generally follows 1992 Astr Almanac,
    p. K11

    from skycalcv5
    """

    geolat = geolat / DEG_IN_RADIAN
    geolong = geolong / HRS_IN_RADIAN
    denom = (1. - FLATTEN) * math.sin(geolat)
    denom = math.cos(geolat) * math.cos(geolat) + denom*denom
    C_geo = 1. / math.sqrt(denom)
    S_geo = (1. - FLATTEN) * (1. - FLATTEN) * C_geo
    # deviation from almanac notation -- include height here. 
    C_geo = C_geo + height / EQUAT_RAD
    S_geo = S_geo + height / EQUAT_RAD

    x_geo=C_geo * math.cos(geolat) * math.cos(geolong)
    y_geo=C_geo * math.cos(geolat) * math.sin(geolong)
    z_geo=S_geo * math.sin(geolat)

    return (x_geo,y_geo,z_geo)

######################################################################
# CALENDAR ROUTINES
######################################################################
    
    
######################################################################
def utc_gmst(ut):
    """ *  Conversion from universal time to sidereal time (double precision)
    given input time ut expressed as MJD
    result is GMST in hours

    DEPRECATED

    """

    ut1=ut

    D2PI=6.283185307179586476925286766559
    S2R=7.272205216643039903848711535369e-5

    #  Julian centuries from fundamental epoch J2000 to this UT
    TU=(ut1-51544.5)/36525

    # GMST at this UT
    gmst=math.modf(ut1)[0]*D2PI+(24110.54841+(8640184.812866+(0.093104-6.2-6*TU)*TU)*TU)*S2R
    gmst=gmst*24/D2PI

    gmst=putrange(gmst)

    return gmst

################################################################################
def utc_lmst(ut, longitude):
    """ returns the LMST given the UT date/time (expressed as MJD),
    and longitude (degrees, + going to east)
    LMST is in hours
    """
    observer=ephem.Observer()
    observer.long=longitude/DEG_IN_RADIAN
    observer.lat=0.0/DEG_IN_RADIAN
    observer.elevation=0.0
    yr,mn,dy=mjd_cal(ut)
    UT=24*(dy-int(dy))
    dy=int(dy)

    UTs=dec2sexstring(UT,digits=0,roundseconds=0)
    observer.date='%d/%d/%d %s' % (yr,mn,dy,UTs)
    lst=observer.sidereal_time()*HRS_IN_RADIAN
    return lst


######################################################################
def mjd_to_epoch(mjd):
    """ convert date (in MJD) to epoch (fractional year)
    """
    
    epoch=2000+(mjd-J2000)/365.25
    return epoch
    

######################################################################
def cal_mjd(yr,mn,dy):
    """ convert calendar date to MJD
    year,month,day (may be decimal) are normal parts of date (Julian)"""
    
    m=mn
    if (yr<0):
        y=yr+1
    else:
        y=yr
    if (m<3):
        m+=12
        y-=1
    if (yr<1582 or (yr==1582 and (mn<10 or (mn==10 and dy<15)))):
        b=0
    else:
        a=int(y/100)
        b=int(2-a+a/4)
    
    jd=int(365.25*(y+4716))+int(30.6001*(m+1))+dy+b-1524.5
    mjd=jd-2400000.5

    return (mjd)

######################################################################
def mjd_cal(mjd):
    """convert MJD to calendar date (yr,mn,dy)
    """
    
    JD=mjd+2400000.5

    JD+=.5
    Z=int(JD)
    F=JD-Z
    if (Z<2299161):
        A=Z
    else:
        alpha=int((Z-1867216.25)/36524.25)
        A=Z+1+alpha-int(alpha/4)
    B=A+1524
    C=int((B-122.1)/365.25)
    D=int(365.25*C)
    E=int((B-D)/30.6001)
    day=B-D-int(30.6001*E)+F
    if (E<14):
        month=E-1
    else:
        month=E-13
    if (month<=2):
        year=C-4715
    else:
        year=C-4716

    return (year,month,day)


######################################################################
def find_dst_bounds(yr,stdtz,use_dst):
    """
    finds mjd's at which daylight savings time begins
    and ends.  The parameter use_dst allows for a number
    of conventions, namely:
    0 = don't use it at all (standard time all the time)
    1 = use USA convention (1st Sun in April to
    last Sun in Oct after 1986; last Sun in April before
    for 2007 & after, second Sun in March/first Sun in Nov )
    2 = use Spanish convention (for Canary Islands)
    -1 = use Chilean convention (CTIO).
    -2 = Australian convention (for AAT, MWA).
    Negative numbers denote sites in the southern hemisphere,
    where mjdb and mjde are beginning and end of STANDARD time for
    the year.
    It's assumed that the time changes at 2AM local time; so
    when clock is set ahead, time jumps suddenly from 2 to 3,
    and when time is set back, the hour from 1 to 2 AM local
    time is repeated.  This could be changed in code if need be."""
    

    if (use_dst==1 or use_dst==0):
        # USA
        # these versions are not current as of 2007
        if (yr >= 2007):
            logging.warning("Warning: DST calculation may be incorrect as of 2007...\n")
        if (yr<2007):
            mo=4
            if (yr>=1986):
                d=1
            else:
                d=30
        else:
            mo=3
            d=6
        h=2
        mn=0
        s=0
        #Find first Sunday in April for 1986 through 2006
        if (yr>=1986 & yr<2007):
            while (day_of_week(cal_mjd(yr,mo,d)) != 6):                
                d+=1
        elif (yr>=2007):
            # find second Sunday in March
            while (day_of_week(cal_mjd(yr,mo,d)) != 6):                
                d+=1
        else:
            # last Sunday in April for pre-1986
            while (day_of_week(cal_mjd(yr,mo,d)) != 6):
                d-=1
        mjdb=cal_mjd(yr,mo,d)+stdtz/24.0

        if (yr < 2007):
            # Find last Sunday in October        
            mo=10
            d=31
            while (day_of_week(cal_mjd(yr,mo,d)) != 6):
                d-=1
        else:
            # first sunday in November
            mo=11
            d=1
            while (day_of_week(cal_mjd(yr,mo,d)) != 6):
                d+=1
            
        mjde=cal_mjd(yr,mo,d)+(stdtz-1)/24.0

    elif (use_dst==2):
        # Spanish, for Canaries
        mo=3
        d=31
        h=2
        mn=0
        s=0
        while (day_of_week(cal_mjd(yr,mo,d)) != 6):
            d-=1
        mjdb=cal_mjd(yr,mo,d)+stdtz/24.0

        # Find last Sunday in October
        mo=9
        d=30
        while (day_of_week(cal_mjd(yr,mo,d)) != 6):
            d-=1
        mjde=cal_mjd(yr,mo,d)+(stdtz-1)/24.0
    elif (use_dst==-1):
        # Chilean
        # off daylight 2nd Sun in March, onto daylight 2nd Sun in October
        mo=3
        d=8
        h=2
        mn=0
        s=0
        while (day_of_week(cal_mjd(yr,mo,d)) != 6):
            d+=1
        mjdb=cal_mjd(yr,mo,d)+(stdtz-1)/24.0

        # mjdb last Sunday in October
        mo=10
        d=8
        while (day_of_week(cal_mjd(yr,mo,d)) != 6):
            d+=1
        mjde=cal_mjd(yr,mo,d)+(stdtz-0)/24.0
    elif (use_dst==-2):
        # Australian
        # off daylight 1st Sun in March, onto daylight last Sun in October
        mo=3
        d=1
        h=2
        while (day_of_week(cal_mjd(yr,mo,d)) != 6):
            d+=1
        mjdb=cal_mjd(yr,mo,d)+(stdtz-1)/24.0
        mo=10
        d=31
        while (day_of_week(cal_mjd(yr,mo,d)) != 6):
            d-=1
        mjde=cal_mjd(yr,mo,d)+(stdtz-1)/24.0      
 
    else:
        logging.warning("Unknown DST code: %d" % (use_dst))
        mjdb=0
        mjde=0

    return (mjdb,mjde)

######################################################################
def zonetime(use_dst,stdtz,mjd,mjdb,mjde):
    """Returns zone time offset when standard time zone is stdz,
           when daylight time begins (for the year) on jdb, and ends
           (for the year) on jde.  This is parochial to the northern
           hemisphere.  */
        /* Extension -- specifying a negative value of use_dst reverses
           the logic for the Southern hemisphere; then DST is assumed for
           the Southern hemisphere summer (which is the end and beginning
           of the year.) */
           """
    if (use_dst==0):
        return stdtz
    elif (mjd>mjdb and mjd<mjde and use_dst>0):
        return stdtz-1
    elif (mjd<mjdb or mjd>mjde and use_dst<0):
        return stdtz-1
    else:
        return stdtz


######################################################################
def day_of_week(mjd):
    """ returns day of week for mjd
    0=Mon
    6=Sun
    """

    jd=mjd+2400000.5

    jd+=0.5
    i=int(jd)
    x=i/7.0+0.01
    d=7*(x-int(x))
    return int(d)


######################################################################
# UTILITY FUNCTIONS
######################################################################

######################################################################
def adj_time(x):
    """ adjusts a time (decimal hours) to be between -12 and 12,
    generally used for hour angles.

    from skycalcv5"""
    if (math.fabs(x) < 100000.):        
        while(x > 12.):
            x = x - 24
        while(x < -12.):
            x = x + 24.
    else:
        printerr("Out of bounds in adj_time!\n")

    return(x)

######################################################################
def frac(x):
    """ return fractional part"""
    return (x-int(x))


######################################################################
def circulo(x):
    """ assuming x is an angle in degrees, returns
    modulo 360 degrees."""

    n=int(x/360)
    return (x-360*n)

######################################################################
def putrange(x,r=24):
    """ puts a value in the range [0,r)
    """

    if (not isinstance(x,numpy.ndarray)):
        while (x<0):
            x+=r
        while (x>=r):
            x-=r
        return x
    else:
        # numpy version
        while (numpy.any(x<0)):
            x[x<0]+=r
        while (numpy.any(x>=r)):
            x[x>=r]-=r
        return x
    
######################################################################
def interp1(X,Y,x):
    """1-D 2-point interpolation (linear)
    solves for y(x) given Y(X)
    """

    m=(Y[1]-Y[0])/(X[1]-X[0])
    y=m*(x-X[1])+Y[1]
    return y

######################################################################
def dec2sex(x):
    """ convert decimal to sexadecimal
    note that this fails for -1<x<0: d will be 0 when it should be -0
    """
    
    sign=1
    if (x<0):
        sign=-1
    x=math.fabs(x)

    d=int(x)
    m=int(60*(x-d))
    s=60*(60*(x-d)-m)
    if (sign == -1):
        d*=-1

    return (d,m,s)

######################################################################
def sex2dec(d,m,s):
    """ convert sexadecimal d,m,s to decimal
    d,m,s can be integer/float or string
    will only handle negative 0 correctly if it's a string
    """
    
    sign=1
    if (isinstance(d,int)):
        if (d<0):
            sign=-1
            d=math.fabs(d)
    elif isinstance(d,str):
        if (d.find('-') >= 0):
            sign=-1
        d=math.fabs(int(d))
    x=d+int(m)/60.0+float(s)/3600.0
    x=x*sign

    return x

######################################################################
def dec2sexstring(x, includesign=0,digits=2,roundseconds=0):    
    """
    dec2sexstring(x, includesign=0,digits=2,roundseconds=0)
    convert a decimal to a sexadecimal string
    if includesign=1, then always use a sign
    can specify number of digits on seconds (if digits>=0) or minutes (if < 0)
    """

    (d,m,s)=dec2sex(float(x))

    if (not roundseconds):
        sint=int(s)
        if (digits>0):
            sfrac=(10**digits)*(s-sint)
            ss2='%02' + 'd' + '.%0' + ('%d' % digits) + 'd'
            ss=ss2 % (sint,sfrac)
        elif (digits == 0):
            ss='%02d' % sint
        else:
            mfrac=10**(math.fabs(digits))*(s/60.0)
            ss2='%02' + 'd' + '.%0' + ('%d' % math.fabs(digits)) + 'd'
            ss=ss2 % (m,mfrac)
    else:
        sint=int(s)
        if (digits == 0):
            ss='%02d' % (round(s))
        elif (digits > 0):
            ss2='%02.' + ('%d' % digits) + 'f'            
            ss=ss2 % s
            if (s < 10):
                ss='0' + ss
        else:
            ss2='%02.' + ('%d' % math.fabs(digits)) + 'f'            
            ss=ss2 % (m+s/60.0)
            if (m < 10):
                ss='0' + ss
            
    
    if (not includesign):
        if (digits>=0):
            sout="%02d:%02d:%s" % (d,m,ss)
        else:
            sout="%02d:%s" % (d,ss)
        if (float(x)<0 and not sout.startswith("-")):
            sout='-' + sout
    else:
        sign='+'
        if (float(x)<0):
            sign='-'
        if (digits>=0):
            sout="%s%02d:%02d:%s" % (sign,math.fabs(d),m,ss)
        else:
            sout="%s%02d:%s" % (sign,math.fabs(d),ss)
        
    return sout

######################################################################
def sexstring2dec(sin):
    """ convert a sexadecimal string to a float
    string can be separated by colons or by hms, dms
    """

    d=0
    m=0
    s=0.0
    if (sin.find(':')>=0):
        # colon-separated values
        if (sin.count(':')==2):
            [d,m,s]=sin.split(':')
        elif (sin.count(':')==1):
            [d,m]=sin.split(':')
            s=0
    elif (sin.find('h')>=0):
        # hms separated
        j1=sin.find('h')
        j2=sin.find('m')
        j3=sin.find('s')
        if (j1>=0):
            d=sin[:j1]
            if (j2>j1):
                m=sin[j1+1:j2]
                if (j3>j2):
                    s=sin[j2+1:j3]
                elif (len(sin)>j2):
                    s=sin[j2+1:]
    elif (sin.find('d')>=0):
        # dms separated
        j1=sin.find('d')
        j2=sin.find('m')
        j3=sin.find('s')
        if (j1>=0):
            d=sin[:j1]
            if (j2>j1):
                m=sin[j1+1:j2]
                if (j3>j2):
                    s=sin[j2+1:j3]
                elif (len(sin)>j2):
                    s=sin[j2+1:]
  
    return sex2dec((d),(m),(s))

######################################################################
def checksex(x):
    """ check and see if the argument is a sexadecimal string
    or a float

    return the float version
    """
    
    y=0
    if (x != None):
        try:
            if ((x).count(':')>=1):
                y=sexstring2dec(x)
        except (TypeError,AttributeError):
            y=float(x)
        except:
            # print what the error was
            print "Unexpected error:", sys.exc_info()[0]
            y=0
    return y

######################################################################
def precomment(s):
    """ insert a comment (#) before every line of text
    """
    p=re.compile(r'^(\D)')
    p2=re.compile(r'\n(\D)')
    s2=p.sub(r'# \1',s)
    s3=p2.sub(r'\n# \1',s2)
    
    return s3

######################################################################
def printerr(s):
    """ writes s to stderr
    """

    logging.warning(s)

######################################################################
def adtolb(RA,Dec):
    """
    [l,b]=adtolb2(RA,Dec)
    all in radians, (RA,Dec) are J2000
    this uses a direct tform from Allen's Astrophysical Quantities
    """

    a=RA
    d=Dec
    a0=282.86*numpy.pi/180;
    l0=(32.93)*numpy.pi/180;
    d0=(62.87)*numpy.pi/180;
    
    sinb=numpy.sin(d)*numpy.cos(d0)-numpy.cos(d)*numpy.sin(a-a0)*numpy.sin(d0);
    b=numpy.arcsin(sinb);
    cosb=numpy.cos(b);
    
    cosdl=numpy.cos(d)*numpy.cos(a-a0)/cosb;
    sindl=(numpy.sin(d0)*numpy.sin(d)+numpy.cos(d0)*numpy.cos(d)*numpy.sin(a-a0))/cosb;
    
    dl=numpy.arctan2(sindl,cosdl);
    l=dl+l0;  

    try:
        if (numpy.any(l>math.pi)):
            l[l>math.pi]-=2*math.pi
    except TypeError:
        if (l>math.pi):
            l-=2*math.pi
    return [l,b]

######################################################################
def lbtoad(l,b):
    """
    [a,d]=adtolb2(l,b)
    all in radians, (a,d) are J2000
    this may occasionally barf on the quadrants, since I only have the sin(RA) term
    taken from Allen's  
    """
    a0=282.86*math.pi/180
    l0=(32.93)*math.pi/180
    d0=(62.87)*math.pi/180

    if (isinstance(l,numpy.ndarray)):
        sind=numpy.cos(b)*numpy.sin(l-l0)*numpy.sin(d0)+numpy.sin(b)*numpy.cos(d0)
        d=numpy.arcsin(sind)
        cosd=numpy.cos(d)
        
        sinda=(numpy.cos(b)*numpy.sin(l-l0)*numpy.cos((d0))-numpy.sin(b)*numpy.sin((d0)))/cosd
        da=numpy.arcsin(sinda)
        a=da+a0
        
        a[numpy.where(cosd==0)]=0
        
        return [a,d]
    else:
        
        sind=math.cos(b)*math.sin(l-l0)*math.sin(d0)+math.sin(b)*math.cos(d0)
        d=math.asin(sind)
        cosd=math.cos(d)
        
        if (cosd == 0):
            a=0
        else:
            sinda=(math.cos(b)*math.sin(l-l0)*math.cos((d0))-math.sin(b)*math.sin((d0)))/cosd
            da=math.asin(sinda)
            a=da+a0
        return [a,d]
        
######################################################################
def galeq(l,b):
    """
    [RA,Dec]=galeq(l,b)
    Transformation from IAU 1958 galactic coordinates to
    J2000.0 equatorial coordinates (double precision)
    
    Given:
    DL,DB       dp       galactic longitude and latitude L2,B2
    
    Returned:
    DR,DD       dp       J2000.0 RA,Dec
    
    (all arguments are radians)
    
    Called:
    sla_DCS2C, sla_DIMXV, sla_DCC2S, sla_DRANRM, sla_DRANGE
    
    Note:
    The equatorial coordinates are J2000.0.  Use the routine
    sla_GE50 if conversion to B1950.0 'FK4' coordinates is
    required.
    
    Reference:
    Blaauw et al, Mon.Not.R.Astron.Soc.,121,123 (1960)
    
    P.T.Wallace   Starlink   21 September 1998
    
    Copyright (C) 1998 Rutherford Appleton Laboratory
    """


    """
    L2,B2 system of galactic coordinates
    
    P = 192.25       RA of galactic north pole (mean B1950.0)
    Q =  62.6        inclination of galactic to mean B1950.0 equator
    R =  33          longitude of ascending node
    
    P,Q,R are degrees
    
    Equatorial to galactic rotation matrix (J2000.0), obtained by
    applying the standard FK4 to FK5 transformation, for zero proper
    motion in FK5, to the columns of the B1950 equatorial to
    galactic rotation matrix:
    """

    if (isinstance(l,numpy.ndarray) and len(l)>1):
        R=numpy.zeros(l.shape)
        D=numpy.zeros(b.shape)
        for i in xrange(len(l)):
            [R[i],D[i]]=galeq(l[i],b[i])
        return [R,D]
    else:
        Rmat=numpy.array([[-0.054875539726,-0.873437108010,-0.483834985808],
                          [+0.494109453312,-0.444829589425,+0.746982251810],
                          [-0.867666135858,-0.198076386122,+0.455983795705]])
        # sperical to cartesian
        V1=dcs2c(l,b)
        
        # galactic to equatorial
        V2=dimxv(numpy.transpose(Rmat),V1)
        
        # cartesian to spherical
        [R,D]=dcc2s(V2)
        
        # put in range
        R=putrange(R,math.pi*2)
        
        return [R,D]

######################################################################
def dcs2c(A, B):
    """    
    *  Spherical coordinates to direction cosines (double precision)
    *
    *  Given:
    *     A,B       d      spherical coordinates in radians
    *                         (RA,Dec), (long,lat) etc.
    *
    *  Returned:
    *     V         d(3)   x,y,z unit vector
    *
    *  The spherical coordinates are longitude (+ve anticlockwise looking
    *  from the +ve latitude pole) and latitude.  The Cartesian coordinates
    *  are right handed, with the x axis at zero longitude and latitude, and
    *  the z axis at the +ve latitude pole.
    *
    *  Last revision:   26 December 2004
    *
    *  Copyright P.T.Wallace.  All rights reserved.
    """

    if (isinstance(A,numpy.ndarray)):
        V=numpy.zeros((3,len(A)))
        COSB = numpy.cos(B)
        
        V[0,:] = numpy.cos(A)*COSB
        V[1,:] = numpy.sin(A)*COSB
        V[2,:] = numpy.sin(B)
        
        return V
    else:
        V=numpy.zeros((3,1))
        COSB = math.cos(B)
        
        V[0,:] = math.cos(A)*COSB
        V[1,:] = math.sin(A)*COSB
        V[2,:] = math.sin(B)
        return V
######################################################################
def dimxv(M, Va):
    """
    [Vb]=dimxv(M, Va)
    *  Performs the 3-D backward unitary transformation:
    *
    *     vector VB = (inverse of matrix M) * vector VA
    *
    *  (double precision)
    *
    *  (n.b.  the matrix must be unitary, as this routine assumes that
    *   the inverse and transpose are identical)
    *
    *  Given:
    *     DM       dp(3,3)    matrix
    *     VA       dp(3)      vector
    *
    *  Returned:
    *     VB       dp(3)      result vector
    *
    *  P.T.Wallace   Starlink   March 1986
    *
    *  Copyright (C) 1995 Rutherford Appleton Laboratory
    """

    Vb=numpy.array(numpy.mat(M)*numpy.mat(Va))
    return Vb

######################################################################    
def dcc2s(V):
    """
    *  Cartesian to spherical coordinates (double precision)
    *
    *  Given:
    *     V     d(3)   x,y,z vector
    *
    *  Returned:
    *     A,B   d      spherical coordinates in radians
    *
    *  The spherical coordinates are longitude (+ve anticlockwise looking
    *  from the +ve latitude pole) and latitude.  The Cartesian coordinates
    *  are right handed, with the x axis at zero longitude and latitude, and
    *  the z axis at the +ve latitude pole.
    *
    *  If V is null, zero A and B are returned.  At either pole, zero A is
    *  returned.
    *
    *  Last revision:   22 July 2004
    *
    *  Copyright P.T.Wallace.  All rights reserved.
    """

    if (len(V.shape)==1 or V.shape[1]==1):
        x=V[0]
        y=V[1]
        z=V[2]
        R=math.sqrt(x*x+y*y)
        if (R == 0):
            A=0
        else:
            A=math.atan2(y,x)
        if (z == 0):
            B=0
        else:
            B=math.atan2(z,R)
        return [A,B]
    

######################################################################
def calcGPSseconds_noleap(MJD,UT):
    """
    calculate the GPSseconds corresponding to the date MJD (days) and time UT (hours)
    ignores leap seconds
    """
    return round(((MJD+UT/24.0)-GPSseconds_MJDzero)*86400)

######################################################################
def calcUTGPSseconds_noleap(GPSseconds):
    """
    calculate the MJD (days) and UT (hours) corresponding to the time in GPSseconds
    ignores leap seconds
    """

    MJD=int((GPSseconds)/86400.0)+GPSseconds_MJDzero
    UT=(((GPSseconds/86400.0)-int((GPSseconds)/86400.0))*24)
    return [MJD,UT]

######################################################################
def calcUTGPSseconds(GPSseconds):
    """
    calculate the MJD (days) and UT (hours) corresponding to the time in GPSseconds
    includes leap seconds from EHM
    """

    i0=3

    try:
        offset_seconds=int((numpy.array(Offset_seconds)[(GPSseconds>numpy.array(GPSseconds_Start))*(GPSseconds<=numpy.array(GPSseconds_End))])[0])
    except IndexError:
        logging.warning("Leap second table not valid for GPSseconds=%d.  Returning value without leap seconds." % GPSseconds)
        return calcUTGPSseconds_noleap(GPSseconds)
    offset_seconds-=Offset_seconds[i0]

    y=GPSseconds+offset_seconds-GPSseconds_Start[i0]-1
    x=y/86400.0
    MJD=math.floor(x)+MJD_Start[i0]
    UT=((y-86400*math.floor(x)))/3600.0
    return [MJD,UT]

######################################################################
def calcGPSseconds(MJD, UT=0):
    """
    calculate the GPSseconds corresponding to the date MJD (days) and time UT (hours)
    based on leap seconds provided by EHM
    """

    try:
        offset_seconds=int((numpy.array(Offset_seconds)[(MJD>numpy.array(MJD_Start))*(MJD<=numpy.array(MJD_End))])[0])
    except IndexError:
        logging.warning("Leap second table not valid for MJD=%d.  Returning value without leap seconds." % MJD)
        return calcGPSseconds_noleap(MJD,UT)
    return (MJD-40587)*86400+UT*3600-offset_seconds
######################################################################
def GPSseconds_now():
    """
    calculate the GPSseconds corresponding to the current time
    """

    x=time.gmtime()
    MJD=cal_mjd(x[0],x[1],x[2])
    UT=x[3]+x[4]/60.0+x[5]/3600.0
    return calcGPSseconds(MJD,UT)

######################################################################
def GPSseconds_now_f():
    """
    CW: calculates the current GPSseconds including fractional seconds
    """

    x=datetime.datetime.utcnow()
    MJD=cal_mjd(x.year,x.month,x.day)
    UT=x.hour+x.minute/60.0+(x.second+x.microsecond/1000000.0)/3600.0
    return calcGPSseconds(MJD,UT)


######################################################################
def GPSseconds_next(GPSseconds=None, buffer=1):
    """
    gpsseconds=GPSseconds_next(GPSseconds=None, buffer=1)
    return the next 8-s boundary in GPSseconds
    if argument is None, will use GPSseconds_now(), otherwise will calculate the next time based on the argument
    if buffer > 0, then the time returned will be >= buffer seconds from argument
    """
    
    if (GPSseconds):
        x=GPSseconds
    else:
        x=GPSseconds_now()
    if (buffer):
        x+=buffer
    return (int(x+9)&int("fffffff8",16))

######################################################################
def rdtoxy(fitshd, RA, Dec):
    """
    [x,y]=rdtoxy(fitshd,ra,dec)
    convert (ra,dec) (degrees) to (x,y) (pixels)
    using the FITS header in fitshd
    """

    try:
        CD1_1=fitshd['CD1_1']
        CD2_2=fitshd['CD2_2']
        try:
            CD2_1=fitshd['CD2_1']
            CD1_2=fitshd['CD1_2']
        except:
            CD2_1=0
            CD1_2=0

    except:
        CD1_1=fitshd['CDELT1']
        CD2_2=fitshd['CDELT2']
        CD1_2=0
        CD2_1=0

    det=(CD1_1*CD2_2-CD1_2*CD2_1)

    CDINV1_1=CD2_2/det
    CDINV1_2=-CD1_2/det
    CDINV2_1=-CD2_1/det
    CDINV2_2=CD1_1/det

    ra0=fitshd['CRVAL1'] * math.pi/180
    dec0=fitshd['CRVAL2']*math.pi/180

    ra=RA*math.pi/180
    dec=Dec*math.pi/180
    if (isinstance(ra,numpy.ndarray)):        
        bottom=numpy.sin(dec)*numpy.sin(dec0)+numpy.cos(dec)*numpy.cos(dec0)*numpy.cos(ra-ra0)
        
        xi=numpy.cos(dec)*numpy.sin(ra-ra0)/bottom
        eta=(numpy.sin(dec)*numpy.cos(dec0)-numpy.cos(dec)*numpy.sin(dec0)*numpy.cos(ra-ra0))/bottom
    else:
        bottom=math.sin(dec)*math.sin(dec0)+math.cos(dec)*math.cos(dec0)*math.cos(ra-ra0)
        
        xi=math.cos(dec)*math.sin(ra-ra0)/bottom
        eta=(math.sin(dec)*math.cos(dec0)-math.cos(dec)*math.sin(dec0)*math.cos(ra-ra0))/bottom
        

    xi*=180/math.pi
    eta*=180/math.pi

    x=CDINV1_1*xi+CDINV1_2*eta+fitshd['CRPIX1']
    y=CDINV2_1*xi+CDINV2_2*eta+fitshd['CRPIX2']

    return (x,y)

######################################################################
# OBSERVATORY DEFINITIONS
######################################################################

######################################################################
def print_obs(itoprint=-1):
    """ print all of the observatories
    """
    if (itoprint >= 0):
        print Obs[itoprint]
    else:
        for i in range(0,len(Obs)):
            print "%s\n" % Obs[i]

# entries have: Code, Name, long. (deg), lat. (deg), elev. (m), TZ (hr), DST, TZ code
Obs=[]
Obs.append(Observatory('LCO','Las Campanas','-70:42:00','-29:00:30',2282,4,-1,"C"))
Obs.append(Observatory('KPNO','Kitt Peak',-7.44111*15,31.9533,700,7,0,"M"))
Obs.append(Observatory('LS','ESO La Silla',-4.7153*15,-29.257,2347,4,-1,"C"))
Obs.append(Observatory('CP','ESO Cerro Paranal',-4.69356*15,-24.625,2635,4,-1,"C"))
Obs.append(Observatory('MP','Mount Palomar',-7.79089*15,33.35667,1706,8,1,"P"))
Obs.append(Observatory('CTIO','Cerro Tololo',-4.721*15,-30.165,2215,4,-1,"C"))
Obs.append(Observatory('MK','Mauna Kea',-10.36478*15,19.8267,4215,10,0,"H"))
Obs.append(Observatory('MH','Mount Hopkins (MMT)',-7.39233*15,31.6883,2608,7,0,'M'))
Obs.append(Observatory('LO','Lick',-8.10911*15,37.3433,1290,8,1,'P'))
#Obs.append(Observatory('LP','La Palma',-1.192*15,28.75833,0,2,'G'))
Obs.append(Observatory('MWA','Murchison Widefield Array (32T)','116:40:14.93','-26:42:11.95',377.8,-8,-2,"W"))
obscode={}
for i in range(len(Obs)):
    obscode[Obs[i].code]=i


######################################################################
class SiderealTime(datetime.time):
    """
    a subclass of time to do LSTs
    the only difference is that float(SiderealTime) will return the LST in degrees
    otherwise stored as hours, minutes, seconds, microseconds
    """

    ##############################
    def __float__(self):
        return 15*(self.hour+self.minute/60.0+self.second/3600.0+
                   self.microsecond/3600.0/1000000.0)
    ##############################
    def __setattr__(self,name,value):
        if name in ['hour','minute','second','microsecond'] and value is not None:
            if name == 'hour':
                self=self.replace(hour=value)
            elif name == 'minute':
                self=self.replace(minute=value)
            elif name == 'second':
                self=self.replace(second=value)
            elif name == 'microsecond':
                self=self.replace(microsecond=value)
        

######################################################################
class MWATime():
    """
    internally stored as a datetime.datetime object

    can print or set via MJD, gpstime, datetimestring
    will also print LST
    
    longitude, latitude, elevation are class attributes

    """
    # in degrees
    longitude=sexstring2dec('116:40:14.93')
    latitude=sexstring2dec('-26:42:11.95')
    # in m
    elevation=377.8
    datetimemodule=datetime

    ##############################
    def __init__(self,datetime=None,gpstime=None,
                 **kwargs):
        
        self.datetime=datetime
        if gpstime is not None:
            self.datetime=gps_datetime(gpstime)
        if len(kwargs)>0:
            self.datetime=self.__class__.datetimemodule.datetime(**kwargs)
        self.observer=ephem.Observer()
        self.observer.pressure=0
        self.observer.long=self.__class__.longitude/DEG_IN_RADIAN
        self.observer.lat=self.__class__.latitude/DEG_IN_RADIAN
        self.observer.elevation=self.__class__.elevation
        self.observer.epoch=ephem.J2000


    ##############################
    @classmethod
    def now(cls):
        """
        Returns the current time as an MWATime object
        """
        return cls(cls.datetimemodule.datetime.utcnow())

    ##############################
    def __setattr__(self,name,value):

        if name in ['datetime','observer']:
            if name is 'datetime' and isinstance(value,datetime.datetime) and value.tzinfo is None:
                value=value.replace(tzinfo=pytz.utc)
            self.__dict__[name]=value
        else:
            if name == 'gpstime' and value is not None:
                self.datetime=gps_datetime(value)
            elif name == 'MJD' and value is not None:
                ut=24*(value-int(value))
                self.datetime=mjd_datetime(int(value),ut)
            elif name == 'datetimestring' and value is not None:
                self.datetime=datetime.datetime(int(value[:4]),
                                                int(value[4:6]),
                                                int(value[6:8]),
                                                int(value[8:10]),
                                                int(value[10:12]),
                                                int(value[12:14]),0,pytz.utc)
                if len(value)>14 and '.' in value:
                    self.datetime.replace(microsecond=int(1e6*float(value[14:])))
            elif name in ['year','month','day','hour','minute','second','microsecond'] and value is not None:
                if name == 'year':
                    self.datetime=self.datetime.replace(year=value)
                elif name == 'month':
                    self.datetime=self.datetime.replace(month=value)
                elif name == 'day':
                    self.datetime=self.datetime.replace(day=value)
                elif name == 'hour':
                    self.datetime=self.datetime.replace(hour=value)
                elif name == 'minute':
                    self.datetime=self.datetime.replace(minute=value)
                elif name == 'second':
                    self.datetime=self.datetime.replace(second=value)
                elif name == 'microsecond':
                    self.datetime=self.datetime.replace(microsecond=value)
                    
                    
    ##############################
    def __getattr__(self,name):
        #if name in ['gpstime','MJD','datetimestring','LST']:
        #    if name == 'gpstime' and self.datetime is not None:
        #        return datetime_gps(self.datetime)
        #    if name == 'MJD' and self.datetime is not None:
        #        mjd,ut=datetime_mjd(self.datetime)
        #        return mjd + ut/24.0
        #    if name == 'UT' and self.datetime is not None:
        #        mjd,ut=datetime_mjd(self.datetime)
        #        return ut
        #    if name == 'datetimestring' and self.datetime is not None:
        #        return self.datetime.strftime('%Y%m%d%H%M%S')
        #    if name == 'LST' and self.datetime is not None:
        #        self.observer.date=self.strftime('%Y/%m/%d %H:%M:%S')
        #        h,m,s=dec2sex(self.observer.sidereal_time()*HRS_IN_RADIAN)
        #        us=int(1e6*(s-int(s)))
        #        return SiderealTime(hour=int(h),minute=int(m),
        #                            second=int(s),microsecond=us)
        #    return None
        if not self.__dict__.has_key(name):            
            return self.datetime.__getattribute__(name)
        else:
            return self.__dict__[name]

    ##############################
    def _get_gpstime(self):
        if self.datetime is not None:
            return datetime_gps(self.datetime)
        else:
            return None
    gpstime=property(_get_gpstime, doc='GPS seconds')
    ##############################
    def _get_MJD(self):
        if self.datetime is not None:
            mjd,ut=datetime_mjd(self.datetime)
            return mjd + ut/24.0
        else:
            return None
    MJD=property(_get_MJD, doc='GPS seconds')

    ##############################
    def _get_epoch(self):
        if self.datetime is not None:
            startofyear=datetime.datetime(year=self.year,month=1,
                                          day=1,hour=0,minute=0,second=0,tzinfo=pytz.utc)
            endofyear=datetime.datetime(year=self.year+1,month=1,
                                        day=1,hour=0,minute=0,second=0,tzinfo=pytz.utc)
            yearduration=(endofyear-startofyear)
            yearduration_seconds=(yearduration.seconds+yearduration.days*86400)
            fractionofyear=(self.datetime-startofyear)
            fractionofyear_seconds=(fractionofyear.seconds+fractionofyear.days*86400)
            return self.year+fractionofyear_seconds*1.0/yearduration_seconds
        else:
            return None
    epoch=property(_get_epoch, doc='Epoch (fractional year)')


    ##############################
    def _get_UT(self):
        if self.datetime is not None:
            return datetime_mjd(self.datetime)[1]
        else:
            return None
    UT=property(_get_UT, doc='UT')
    ##############################
    def _get_LST(self):
        if self.datetime is not None:
            self.observer.date=self.strftime('%Y/%m/%d %H:%M:%S')
            h,m,s=dec2sex(self.observer.sidereal_time()*HRS_IN_RADIAN)
            us=int(1e6*(s-int(s)))
            return SiderealTime(hour=int(h),minute=int(m),
                                        second=int(s),microsecond=us)
        else:
            return None
    LST=property(_get_LST, doc='Local Sidereal Time')

    ##############################
    def __add__(self, other):
        if isinstance(other,self.__class__.datetimemodule.timedelta):
            return self.__class__(self.datetime.__add__(other))
        return self + self.__class__.datetimemodule.timedelta(seconds=other)
    ##############################
    def __sub__(self, other):
        if isinstance(other,self.__class__.datetimemodule.timedelta):
            return self.__class__(self.datetime.__sub__(other))
        return self - self.__class__.datetimemodule.timedelta(seconds=other)

################################################################################
def HA(LST,RA,Dec,epoch=2000.0):
    """
    HA(LST,RA,Dec,epoch=2000.0):
    
    returns the hour angle in degrees
    LST should be apparent sidereal time in degrees
    RA,Dec should be RA,Dec in degrees (J2000 assumed)
    if epoch is != 2000, will precess RA,Dec as appropriate
    """
    if epoch != 2000.0:
        RAnow,Decnow=precess(RA,Dec,2000,epoch)
    else:
        RAnow,Decnow=RA,Dec
    return putrange(LST-RAnow,360)

################################################################################
def premat(equinox1, equinox2, fk4=False):
   """
    NAME:
          PREMAT
    PURPOSE:
          Return the precession matrix needed to go from EQUINOX1 to EQUINOX2.
    EXPLANTION:
          This matrix is used by the procedures PRECESS and BARYVEL to precess
          astronomical coordinates
   
    CALLING SEQUENCE:
          matrix = PREMAT( equinox1, equinox2, [ /FK4 ] )
   
    INPUTS:
          EQUINOX1 - Original equinox of coordinates, numeric scalar.
          EQUINOX2 - Equinox of precessed coordinates.
   
    OUTPUT:
         matrix - double precision 3 x 3 precession matrix, used to precess
                  equatorial rectangular coordinates
   
    OPTIONAL INPUT KEYWORDS:
          /FK4   - If this keyword is set, the FK4 (B1950.0) system precession
                  angles are used to compute the precession matrix.   The
                  default is to use FK5 (J2000.0) precession angles
   
    EXAMPLES:
          Return the precession matrix from 1950.0 to 1975.0 in the FK4 system
   
          IDL> matrix = PREMAT( 1950.0, 1975.0, /FK4)
   
    PROCEDURE:
          FK4 constants from Computational Spherical Astronomy by Taff (1983),
          p. 24. (FK4). FK5 constants from Astronomical Almanac Explanatory
          Supplement 1992, page 104 Table 3.211.1.
   
    REVISION HISTORY
          Written, Wayne Landsman, HSTX Corporation, June 1994
          Converted to IDL V5.0   W. Landsman   September 1997
   """

   deg_to_rad = numpy.pi / 180.0e0
   sec_to_rad = deg_to_rad / 3600.e0
   
   t = 0.001e0 * (equinox2 - equinox1)
   
   if not fk4:   
      st = 0.001e0 * (equinox1 - 2000.e0)
      #  Compute 3 rotation angles
      a = sec_to_rad * t * (23062.181e0 + st * (139.656e0 + 0.0139e0 * st) + t * (30.188e0 - 0.344e0 * st + 17.998e0 * t))
      
      b = sec_to_rad * t * t * (79.280e0 + 0.410e0 * st + 0.205e0 * t) + a
      
      c = sec_to_rad * t * (20043.109e0 - st * (85.33e0 + 0.217e0 * st) + t * (-42.665e0 - 0.217e0 * st - 41.833e0 * t))
      
   else:   
      
      st = 0.001e0 * (equinox1 - 1900.e0)
      #  Compute 3 rotation angles
      
      a = sec_to_rad * t * (23042.53e0 + st * (139.75e0 + 0.06e0 * st) + t * (30.23e0 - 0.27e0 * st + 18.0e0 * t))
      
      b = sec_to_rad * t * t * (79.27e0 + 0.66e0 * st + 0.32e0 * t) + a
      
      c = sec_to_rad * t * (20046.85e0 - st * (85.33e0 + 0.37e0 * st) + t * (-42.67e0 - 0.37e0 * st - 41.8e0 * t))
      
   
   sina = numpy.sin(a)
   sinb = numpy.sin(b)
   sinc = numpy.sin(c)
   cosa = numpy.cos(a)
   cosb = numpy.cos(b)
   cosc = numpy.cos(c)
   
   r = numpy.zeros((3, 3))
   r[0,:] = numpy.array([cosa * cosb * cosc - sina * sinb, sina * cosb + cosa * sinb * cosc, cosa * sinc])
   r[1,:] = numpy.array([-cosa * sinb - sina * cosb * cosc, cosa * cosb - sina * sinb * cosc, -sina * sinc])
   r[2,:] = numpy.array([-cosb * sinc, -sinb * sinc, cosc])
   
   return r


################################################################################
def precess(ra0, dec0, equinox1, equinox2, doprint=False, fk4=False, radian=False):
   """
    NAME:
         PRECESS
    PURPOSE:
         Precess coordinates from EQUINOX1 to EQUINOX2.
    EXPLANATION:
         For interactive display, one can use the procedure ASTRO which calls
         PRECESS or use the /PRINT keyword.   The default (RA,DEC) system is
         FK5 based on epoch J2000.0 but FK4 based on B1950.0 is available via
         the /FK4 keyword.
   
         Use BPRECESS and JPRECESS to convert between FK4 and FK5 systems
    CALLING SEQUENCE:
         PRECESS, ra, dec, [ equinox1, equinox2, /PRINT, /FK4, /RADIAN ]
   
    INPUT - OUTPUT:
         RA - Input right ascension (scalar or vector) in DEGREES, unless the
                 /RADIAN keyword is set
         DEC - Input declination in DEGREES (scalar or vector), unless the
                 /RADIAN keyword is set
   
         The input RA and DEC are modified by PRECESS to give the
         values after precession.
   
    OPTIONAL INPUTS:
         EQUINOX1 - Original equinox of coordinates, numeric scalar.  If
                  omitted, then PRECESS will query for EQUINOX1 and EQUINOX2.
         EQUINOX2 - Equinox of precessed coordinates.
   
    OPTIONAL INPUT KEYWORDS:
         /PRINT - If this keyword is set and non-zero, then the precessed
                  coordinates are displayed at the terminal.    Cannot be used
                  with the /RADIAN keyword
         /FK4   - If this keyword is set and non-zero, the FK4 (B1950.0) system
                  will be used otherwise FK5 (J2000.0) will be used instead.
         /RADIAN - If this keyword is set and non-zero, then the input and
                  output RA and DEC vectors are in radians rather than degrees
   
    RESTRICTIONS:
          Accuracy of precession decreases for declination values near 90
          degrees.  PRECESS should not be used more than 2.5 centuries from
          2000 on the FK5 system (1950.0 on the FK4 system).
   

    PROCEDURE:
          Algorithm from Computational Spherical Astronomy by Taff (1983),
          p. 24. (FK4). FK5 constants from Astronomical Almanac Explanatory
          Supplement 1992, page 104 Table 3.211.1.
   
    PROCEDURE CALLED:
          Function PREMAT - computes precession matrix
   
    REVISION HISTORY
          Written, Wayne Landsman, STI Corporation  August 1986
          Correct negative output RA values   February 1989
          Added /PRINT keyword      W. Landsman   November, 1991
          Provided FK5 (J2000.0)  I. Freedman   January 1994
          Precession Matrix computation now in PREMAT   W. Landsman June 1994
          Added /RADIAN keyword                         W. Landsman June 1997
          Converted to IDL V5.0   W. Landsman   September 1997
          Correct negative output RA values when /RADIAN used    March 1999
          Work for arrays, not just vectors  W. Landsman    September 2003
          Convert to Python                     Sergey Koposov  July 2010
   """
   scal = True
   if isinstance(ra0, numpy.ndarray):
      ra = ra0.copy()  
      dec = dec0.copy()
      scal = False
   else:
      ra=numpy.array([ra0])
      dec=numpy.array([dec0])
   npts = ra.size 
   origshape=ra.shape
   if len(ra.shape)>1:
       # it is nd
       ra=ra.flatten()
       dec=dec.flatten()
   
   if not radian:   
      ra_rad = numpy.deg2rad(ra)     #Convert to double precision if not already
      dec_rad = numpy.deg2rad(dec)
   else:   
      ra_rad = ra
      dec_rad = dec
   
   a = numpy.cos(dec_rad)
   
   x = numpy.zeros((npts, 3))
   x[:,0] = a * numpy.cos(ra_rad)
   x[:,1] = a * numpy.sin(ra_rad)
   x[:,2] = numpy.sin(dec_rad)
   
   # Use PREMAT function to get precession matrix from Equinox1 to Equinox2
   
   r = premat(equinox1, equinox2, fk4=fk4)
   
   x2 = numpy.transpose(numpy.dot(numpy.transpose(r), numpy.transpose(x)))      #rotate to get output direction cosines
   
   ra_rad = numpy.zeros(npts) + numpy.arctan2(x2[:,1], x2[:,0])
   dec_rad = numpy.zeros(npts) + numpy.arcsin(x2[:,2])
   
   if not radian:   
      ra = numpy.rad2deg(ra_rad)
      ra = ra + (ra < 0.) * 360.e0            #RA between 0 and 360 degrees
      dec = numpy.rad2deg(dec_rad)
   else:   
      ra = ra_rad
      dec = dec_rad
      ra = ra + (ra < 0.) * 2.0e0 * numpy.pi
   
   if scal:
      ra, dec = ra[0], dec[0]
   return ra.reshape(origshape), dec.reshape(origshape)
