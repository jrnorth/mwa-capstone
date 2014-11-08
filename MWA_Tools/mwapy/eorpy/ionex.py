"""
    module to download IONEX data
    ionospheric TEC based on:
    http://igscb.jpl.nasa.gov/components/prods.html
    

    class ionexmaps=
    set of IONEX maps
    it parses the data from a file (downloading if necessary)
    can return TEC, geomagnetic B, and Rotation Measure

    examples (zenith):
    t=Time('2012-09-20T00:00:00',scale='utc')
    i=ionex.ionexmaps(int(t.gps))
    TEC=i(int(t.gps))
    Bx,By,Bz=i.getB(int(t.gps))
    RM=i.RM(int(t.gps))

    off-zenith:
    TEC=i(newtime, ra=110, dec=-26)
    RM=i.RM(newtime, ra=110, dec=-26)


written by David Kaplan

Origin:
program to automatically form file name of needed ionex file(s), download
them, and uncompress them, saving much typing.

Walter Brisken    Jun 15, 2002

Modified by Abraham Neben (2014)


"""

from os import system
import sys
import urllib2
import sys,os,logging,shutil,datetime,re,subprocess,math,tempfile,string,glob,copy
import numpy
import astropy.time,astropy.coordinates.angles as angles
import astropy.units as u, astropy.constants as c
import scipy.interpolate
from mwapy import ephem_utils
import igrf11_python

# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('ionex')
logger.setLevel(logging.WARNING)    
    

_proto = 'ftp'
_site = 'cddis.gsfc.nasa.gov'
_basedir = '/gps/products/ionex/'
_MWA=ephem_utils.Obs[ephem_utils.obscode['MWA']]

TECU=1e16/u.m**2
# http://en.wikipedia.org/wiki/Faraday_effect
RMconstant=((c.e.esu**3/(2*numpy.pi*c.m_e**2*c.c**4))).cgs.value

##################################################
def download_ionex(date, force=False):
    """
    filename=download_ionex(date, force=False)
    download and uncompress IONEX data for a given date
    date can be:
    (year, dayofyear) tuple
    or astropy.time.Time
    or datetime.datetime
    or integer (assumed gpstime)
    """

    if isinstance(date,tuple) or isinstance(date,list) or isinstance(date,numpy.ndarray):
        # assume year, doy
        year=date[0]
        doy=date[1]
    elif isinstance(date, astropy.time.Time):
        t=date.datetime.timetuple()
        year,doy=t.tm_year, t.tm_yday
    elif isinstance(date, int):
        t=astropy.time.Time(date, format='gps', scale='utc').datetime.timetuple()
        year,doy=t.tm_year, t.tm_yday
    elif isinstance(date, datetime.datetime):
        t=date.timetuple()
        year,doy=t.tm_year, t.tm_yday
        

    filename='jplg%03d0.%02di' % (doy,
                                 numpy.mod(year,100))

    if os.path.exists(filename + '.npz') and not force:
        logger.info('Zipped IONEX file found for %04d/%03d; not downloading' % (year, doy))
        return filename+'.npz'

    if os.path.exists(filename) and not force:
        logger.info('IONEX file found for %04d/%03d; not downloading' % (year, doy))
        return filename
    url = '%s://%s%s%04d/%03d/%s.Z' % (_proto,
                                       _site,
                                       _basedir,
                                       year,
                                       doy,
                                       filename)
                                                    
    
    logger.info('Fetching %s ...' % url)
    req=urllib2.Request(url)
    
    try:
        response=urllib2.urlopen(req)
    except urllib2.URLError as e:
        logger.error('Unable to fetch %s' % url)
        logger.error(e.reason)
        return None
    the_page=response.read()
    try:
        f=open(filename + '.Z','wb')
    except:
        logger.error('Unable to open file %s.Z for writing' % filename)
        return None
    f.write(the_page)
    f.close()
    try:
        subprocess.call(['uncompress',filename+'.Z'])
    except:
        subprocess.call(['gunzip',filename+'.Z'])        
    if not os.path.exists(filename):
        logger.error('Unable to find uncompressed file %s' % filename)
        return None
    return filename

##################################################
class ionexmaps():
    """
    set of IONEX maps
    it parses the data from a file (downloading if necessary)
    can return TEC, geomagnetic B, and Rotation Measure

    examples (zenith):
    t=Time('2012-09-20T00:00:00',scale='utc')
    i=ionex.ionexmaps(int(t.gps))
    TEC=i(int(t.gps))
    Bx,By,Bz=i.getB(int(t.gps))
    RM=i.RM(int(t.gps))

    off-zenith:
    TEC=i(newtime, ra=110, dec=-26)
    RM=i.RM(newtime, ra=110, dec=-26)

    
    """

    def __init__(self, value):
        self.filename=None
        if isinstance(value,tuple) or isinstance(value,list) or isinstance(value,numpy.ndarray):
            # assume year, doy
            filename=download_ionex(value)
            self.parse_raw_ionex(filename)
        elif isinstance(value,str) and os.path.exists(value):
            # assume it's a file            
            self.parse_raw_ionex(value)
        elif isinstance(value,astropy.time.Time):
            filename=download_ionex(value)
            self.parse_raw_ionex(filename)
        elif isinstance(value, int):
            # gpstime
            value=astropy.time.Time(value, format='gps', scale='utc')
            filename=download_ionex(value)
            self.parse_raw_ionex(filename)
        elif isinstance(value, datetime.datetime):
            filename=download_ionex(value)
            self.parse_raw_ionex(filename)

    ##################################################

    def parse_raw_ionex(self, filename):
        """
        parse_raw_ionex(self, filename)
        load in the IONEX data in filename and create a 3D grid:
        (time, latitude, longitude)

        """

        if scipy.__version__ < '0.11.0':
            logger.error('Requires scipy version 0.11.0 or later')
            return None
        
        if filename is None:
            logger.error('No valid file found')
            return None

        if 'npz' in filename:
            logger.info('Loading parsed IONEX data from %s' % (filename))
            d=numpy.load(filename)
            self.data=d['data']
            self.dates=astropy.time.Time(d['dates'],format='gps',scale='utc')
            self.lons=d['lons']
            self.lats=d['lats']
            self.filename=filename
            self.year=d['year']
            self.doy=d['doy']
            self.height=d['height']*u.km
            return

        try:
            f=open(filename)
        except:
            logger.error('Unable to open IONEX file %s' % filename)
            return None
        lines=f.readlines()
        nlat=None
        nlon=None
        maps=[]
        mapdates=[]
        i=0
        while i < len(lines):
            if 'DHGT' in lines[i]:
                self.height=float(lines[i].split()[0])*u.km
            if 'LAT1 / LAT2 / DLAT' in lines[i]:
                lat1,lat2,dlat=map(float,lines[i].split()[:3])
                nlat = int((lat2-lat1)/dlat+1)
                if lat1 < lat2:
                    latvals = numpy.linspace(lat1,lat2,nlat)
                else:
                    latvals = numpy.linspace(lat2,lat1,nlat)
            if 'LON1 / LON2 / DLON' in lines[i]:
                lon1,lon2,dlon=map(float,lines[i].split()[:3])        
                nlon = int((lon2-lon1)/dlon+1)
                lonvals = numpy.linspace(lon1,lon2,nlon)
            if 'START OF TEC MAP' in lines[i]:
                mapdata = numpy.zeros((nlat, nlon))            
                mapnumber=int(lines[i].split()[0])
                i+=1
                t=datetime.datetime(*map(int,
                                         lines[i].split()[:6]))

                i+=1
                while not 'END OF TEC MAP' in lines[i]:
                    if 'LAT/LON1/LON2/DLON/H' in lines[i]:
                        lat=float(lines[i][:8])                    
                        mapdata[latvals==lat]=map(int,
                                                  ' '.join(lines[i+1:i+6]).split())
                        i+=6
                maps.append(mapdata)
                mapdates.append(t)
            i+=1
        self.lats=latvals
        self.lons=lonvals[:-1]
        self.data=numpy.array(maps)[:,:,:-1]
        self.dates=astropy.time.Time(mapdates,scale='utc')
        self.year=self.dates[0].datetime.timetuple().tm_year
        self.doy=self.dates[0].datetime.timetuple().tm_yday
        self.filename=filename
        try:
            numpy.savez(self.filename + '.npz',
                        data=self.data,
                        dates=self.dates.gps,
                        lons=self.lons,
                        lats=self.lats,
                        filename=self.filename,
                        year=self.year,
                        doy=self.doy,
                        height=self.height.to(u.km).value)
        except:
            logger.warning('Error saving numpy zip file %s' % (self.filename + '.npz'))
        
                    
        
    ##################################################
    def __call__(self, newtime, ra=None, dec=None):
        """
        TEC=i(newtime, ra=None, dec=None)
        returns the zenith TEC (if ra is None)
        else the total TEC along the line-of-sight
        in 0.1*TECU
        """
        if ra is None:
            return self.interpolate(newtime)
        else:
            if not isinstance(ra,astropy.units.quantity.Quantity):
                ra=angles.Angle(ra,unit=u.degree)
            if not isinstance(dec,astropy.units.quantity.Quantity):
                dec=angles.Angle(dec,unit=u.degree)
            az,el=ephem_utils.radec2azel(ra.degree,dec.degree,newtime)
            #print '(RA,Dec)=(%.1f,%.1f) deg = (Az,El)=(%.1f,%.1f) deg' % (
            #    ra.degree,dec.degree,az,el)
            az=angles.Angle(az,unit=u.degree)
            el=angles.Angle(el,unit=u.degree)
            za=angles.Angle(90,unit=u.degree)-el
            dLat,dLong,AzPunc,ZenPunc=self.ionosphere_geometry(az,za)
            #print dLat.to(u.degree),dLong.to(u.degree),AzPunc.to(u.degree),ZenPunc.to(u.degree)
            # return the full line of sight TEC, converting from vertical
            return self.interpolate(newtime, dlong=dLong,
                                    dlat=dLat)/numpy.cos(ZenPunc).value
            
    ##################################################
    def getB(self, newtime, dlong=0, dlat=0):
        """
        Bx,By,Bz=i.getB(newtime, dlong=0, dlat=0):                
        return the geomagnetic field in G
        Bx=north component tangent to surface
        By=east component tangent to surface
        Bz=vertical component (-=down, +=up)

        value at MWA site for given time, shifted by dlong or dlat if specified
        quantities are decimal degrees if not explicitly given

        based on the
        International Geomagnetic Reference Field, 11th generation
        http://www.ngdc.noaa.gov/IAGA/vmod/igrf.html
        Geophys. J. Int., Vol 183, Issue 3, pp 1216-1230,
        December 2010. DOI: 10.1111/j.1365-246X.2010.04804.x.
        
        can check with http://www.ngdc.noaa.gov/geomag-web/#igrfwmm
        """
        if not isinstance(dlong,astropy.units.quantity.Quantity):
            dlong=angles.Angle(dlong,unit=u.degree)
        if not isinstance(dlat,astropy.units.quantity.Quantity):
            dlat=angles.Angle(dlat,unit=u.degree)

        if not isinstance(newtime, astropy.time.Time):
            if isinstance(newtime, int):
                # assume gpstime
                newtime=astropy.time.Time(newtime, format='gps',scale='utc')
            if isinstance(newtime, datetime.datetime):
                newtime=astropy.time.Time(newtime, scale='utc')

        # these are in nT
        Bx,By,Bz,Bt=igrf11_python.igrf11syn(0, newtime.jyear, 1,
                                            self.height.to(u.km).value,
                                            90-(_MWA.lat+angles.Angle(dlat).degree),
                                            _MWA.long+angles.Angle(dlong).degree)

        # convert to G
        Bx*=1e4*1e-9
        By*=1e4*1e-9
        Bz*=1e4*1e-9
        return Bx,By,Bz

    ##################################################
    def RM(self, newtime, ra=None, dec=None):
        """
        RM=i.RM(newtime, ra=None, dec=None))
        compute Rotation Measure (rad/m**2)
        along the zenith if ra is None
        else along the specified direction
        """
        TEC=self.__call__(newtime, ra=ra, dec=dec)
        if TEC is None:
            return None
        Bx,By,Bz=self.getB(newtime)
        if ra is None:
            # the important B is the Bz
            ZenPunc=0
            AzPunc=0
        else:
            if not isinstance(ra,astropy.units.quantity.Quantity):
                ra=angles.Angle(ra,unit=u.degree)
            if not isinstance(dec,astropy.units.quantity.Quantity):
                dec=angles.Angle(dec,unit=u.degree)
            az,el=ephem_utils.radec2azel(ra.degree,dec.degree,newtime)
            #logger.info('(RA,Dec)=(%.1f,%.1f) deg = (Az,El)=(%.1f,%.1f) deg' % (
            #    ra.degree,dec.degree,az,el))
            az=angles.Angle(az,unit=u.degree)
            el=angles.Angle(el,unit=u.degree)
            za=angles.Angle(90,unit=u.degree)-el
            dLat,dLong,AzPunc,ZenPunc=self.ionosphere_geometry(az,za)
        # convert the components of B to the B along the LOS
        # taken from ionFR.py
        B=Bz*numpy.cos(ZenPunc) + numpy.sin(ZenPunc)*(By*numpy.sin(AzPunc)+Bx*numpy.cos(AzPunc))
            
        # TEC is in 0.1 TECU
        # B is in G
        RM=RMconstant*B*TEC*1e15
        return RM

    ##################################################
    def ionosphere_geometry(self,az,za):
        """
        dLat,dLong,AzPunc,ZenPunc=ionosphere_geometry(self.az,za)
        return the change in Lat,Long
        and the Az,ZA of the ionosphere puncture
        quantities are decimal degrees if not explicitly given

        based on ionFR/ippcoor.PuncIonOffset

        """
        
        # the zenith angle at the
	# Ionospheric piercing point
        if not isinstance(az,astropy.units.quantity.Quantity):
            az=angles.Angle(az,unit=u.degree)
        if not isinstance(za,astropy.units.quantity.Quantity):
            za=angles.Angle(za,unit=u.degree)
        
	ZenPunc = numpy.arcsin((c.R_earth*numpy.sin(za))/(c.R_earth + self.height))
        theta = za - ZenPunc
        LatPunc=numpy.arcsin(numpy.sin(numpy.radians(_MWA.lat))*numpy.cos(theta) +
                             numpy.cos(numpy.radians(_MWA.lat))*numpy.sin(theta)*numpy.cos(az))
        # latitude difference
        dLat=LatPunc - _MWA.lat*u.degree

        # Longitude difference 
	dLong = numpy.arcsin(numpy.sin(az)*numpy.sin(theta)/numpy.cos(LatPunc))

        # Azimuth at the IPP
        AzPunc=numpy.arcsin(numpy.sin(az)*numpy.cos(numpy.radians(_MWA.lat))/numpy.cos(LatPunc))
        return dLat,dLong,AzPunc,ZenPunc
    ##################################################
    def interpolate(self, newtime, dlong=0, dlat=0):
        """
        return the zenith TEC interpolated at <newtime>
        <newtime> can be:
        astropy.time.Time
        int (assumed GPStime)
        datetime.datetime
        """

        if not isinstance(dlong,astropy.units.quantity.Quantity):
            dlong=angles.Angle(dlong,unit=u.degree)
        if not isinstance(dlat,astropy.units.quantity.Quantity):
            dlat=angles.Angle(dlat,unit=u.degree)


        if self.filename is None:
            logger.error('Valid IONEX data not loaded')
            return None

        if not isinstance(newtime, astropy.time.Time):
            if isinstance(newtime, int):
                # assume gpstime
                newtime=astropy.time.Time(newtime, format='gps',scale='utc')
            if isinstance(newtime, datetime.datetime):
                newtime=astropy.time.Time(newtime, scale='utc')
        #logger.info('Interpolating for %s' % newtime)
        if not newtime >= self.dates[0]:
            logger.error('Requested time is not after the start of this data-set')
            return None
        if not newtime <= self.dates[-1]:
            logger.error('Requested time is not before the end of this data-set')
            return None
        dt=self.dates-newtime
        try:
            ibefore=numpy.where(dt.value<0)[0][-1]
        except IndexError:
            ibefore=0
        try:
            iafter=numpy.where(dt.value>=0)[0][0]
        except IndexError:
            iafter=len(self.data)-1
        if ibefore==0 and iafter==0:
            iafter=1

        latvalue=angles.Angle(_MWA.lat,unit=u.degree)+dlat+angles.Angle(numpy.pi/2,unit=u.radian)
        lonvalue=angles.Angle(_MWA.long,unit=u.degree)+dlong+angles.Angle(numpy.pi,unit=u.radian)
        lonvalue_before=lonvalue+angles.Angle(dt[ibefore].jd*2*numpy.pi,unit=u.radian)
        lonvalue_after=lonvalue-angles.Angle(dt[iafter].jd*2*numpy.pi,unit=u.radian)

        
        interpbefore=scipy.interpolate.RectSphereBivariateSpline(numpy.radians(self.lats)+numpy.pi/2,numpy.radians(self.lons)+numpy.pi, self.data[ibefore])
        interpafter=scipy.interpolate.RectSphereBivariateSpline(numpy.radians(self.lats)+numpy.pi/2,numpy.radians(self.lons)+numpy.pi, self.data[iafter])
        valuebefore=interpbefore(latvalue.radian, lonvalue_before.radian)[0][0]
        valueafter=interpafter(latvalue.radian, lonvalue_after.radian)[0][0]
        return numpy.interp(0, [dt[ibefore].jd, dt[iafter].jd], [valuebefore, valueafter])

    
