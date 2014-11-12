# metafits format version number
_VERSION=2.0

import logging,datetime,math
import numpy,ephem
try:
    import astropy.io.fits as pyfits
except ImportError:
    import pyfits

import json,urllib,urllib2

USEWEB = True   # If true, use the web services to get metadata, otherwise call functions in obssched.tilestatus

if not USEWEB:
    import mwaconfig
    from obssched import tilestatus

from mwapy import ephem_utils
import mwapy

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

try:
    from astropy.time import Time
    from astropy.coordinates.angles import Angle
    from astropy import units as u
    _useastropy=True
except ImportError:
    _useastropy=False

# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('metadata')
logger.setLevel(logging.WARNING)


# 128 antennas * 2 polns
_NINP_128T=256
# 16 inputs (16 antennas * 2 polns) go into each Rx
_INPUTSPERRX=16
# default digital gain
_DEFAULT_GAIN=64
# total number of coarse channels
_NUM_COARSE_CHANNELS=256

# if a dipole is bad, its delay is set to this
_BAD_DIPOLE_DELAY=32


_BASEURL='http://mro.mwa128t.org'


######################################################################
def fetch_metadata(service='obs', gpstime=None, filename=None, URL=_BASEURL):
    """Given a service (eg 'obs' or 'con') and either a gpstime in
    seconds or a data file name for that observation, return 
    the metadata as a Python dictionary.
    """
    if USEWEB:
        if gpstime is not None:
            data = urllib.urlencode({'obs_id':gpstime})
            if gpstime > ephem_utils.GPSseconds_now():
                logger.warning('Time requested (%d) is in the future; results may not be reliable' % (gpstime))
        elif filename is not None:
            data = urllib.urlencode({'filename':filename})
        else:
            logger.error("Must pass either filename or obs_id")
            return
        if service.strip().lower() in ['obs','con']:
            service = service.strip().lower()
        else:
            logger.error("Invalid service name: %s" % service)
            return
        url=URL + '/metadata/' + service + '?' + data
        try:
            logger.debug('Retrieving %s...' % url)
            result = json.load(urllib2.urlopen(url))
        except urllib2.HTTPError as error:
            logger.error("HTTP error from server: code=%d, response:\n %s" % (error.code, error.read()))
            logger.error('Unable to retrieve %s' % (url))
            return
        except urllib2.URLError as error:
            logger.error("URL or network error: %s" % error.reason)
            logger.error('Unable to retrieve %s' % (url))
            return
        except:
            logger.error('Unable to retrieve %s' % (url))
            return

        return result
    else:
        if service == 'obs':
            resdict = tilestatus.getObservationInfo(obsid=gpstime, filename=filename)
        elif service == 'con':
            db = tilestatus.getdb()
            if filename and (not gpstime):
                gpstime = tilestatus.getobsid(filename, db=db)
            tiles = tilestatus.getTiles(reftime=gpstime, db=db)
            resdict = dict([(tileid,dict(value)) for (tileid,value) in tiles.items()])
        else:
            return None
        return json.loads(json.dumps(resdict))



######################################################################
def fetch_observations(URL=_BASEURL, **kwargs):
    service='find'
    constraints={}
    if kwargs is not None:
        for key, value in kwargs.iteritems():
            if value is not None:
                constraints[key]=value
    if len(constraints.keys())>0:
        data = urllib.urlencode(constraints)
    else:
        return []
    url=URL + '/metadata/' + service + '?' + data
    try:
        logger.debug('Retrieving %s...' % url)
        result = json.load(urllib2.urlopen(url))
    except urllib2.HTTPError as error:
        logger.error("HTTP error from server: code=%d, response:\n %s" % (error.code, error.read()))
        logger.error('Unable to retrieve %s' % (url))
        return
    except urllib2.URLError as error:
        logger.error("URL or network error: %s" % error.reason)
        logger.error('Unable to retrieve %s' % (url))
        return
    except:
        logger.error('Unable to retrieve %s' % (url))
        return []
    return result


######################################################################
def fetch_obsinfo(gpstime, URL=_BASEURL):
    """
    Return the MWA observation data associated with a given gpstime
    """

    return fetch_metadata(service='obs',
                          gpstime=gpstime,
                          URL=URL)
    
######################################################################
def fetch_tileinfo(gpstime, URL=_BASEURL):
    """
    Return the MWA tile connection data associated with a given gpstime
    """
    tileinfo=fetch_metadata(service='con',
                            gpstime=gpstime,
                            URL=URL)

    # make sure keys are integers
    newtileinfo={}
    for t in tileinfo.keys():
        newtileinfo[int(t)]=tileinfo[t]
    return newtileinfo


######################################################################
class MWA_Observation_Summary():
    """
    Holds a quick bit of data for each observation
    This is returned in a search query
    """
    def __init__(self, data):
        self.obsid=data[0]
        self.projectid=data[3]
        self.creator=data[2]
        self.obsname=data[1]
        try:
            self.ra=data[4]
            self.dec=data[5]
        except:
            self.ra=None
            self.dec=None
        if _useastropy:
            self.time=Time(self.obsid,format='gps',scale='utc')
        else:
            self.time = None

    def __str__(self):
        if self.dec>=0:
            decsign='+'
        else:
            decsign='-'
        decstring=decsign + '%.1f' % numpy.abs(self.dec)
        while len(decstring)<5:
            decstring=' ' + decstring

        if self.time is not None:
            return '%d\t%s\t%s\t%-15s\t%5.1f\t%s\t%s' % (self.obsid,
                                                         self.time.datetime.strftime('%Y-%m-%dT%H:%M:%S'),
                                                         self.projectid,
                                                         self.creator,
                                                         self.ra,
                                                         decstring,
                                                         self.obsname)
        else:
            return '%d\t%s\t%s\t%-15s\t%5.1f\t%s\t%s' % (self.obsid,
                                                         '--',
                                                         self.projectid,
                                                         self.creator,
                                                         self.ra,
                                                         decstring,
                                                         self.obsname)

    @classmethod
    def string_header(self):
        return '# starttime\t\t\t\tproject\tcreator\t\tRA(d)\tDec(d)\tobsname'


######################################################################
class MWA_Observation():
    """
    holds the fundamental data for a MWA observation
    the basic information is based on the observation_number,
    which is the starttime in GPS seconds
    once that is set, it computes all the rest of the times.

    o=MWA_Observation(input,rfstream=0, ionex=False)
    input is either gpstime or obsinfo structure
    
    """

    ##################################################
    def __init__(self, input,
                 rfstream=0, ionex=False, url=_BASEURL):        
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
        self.ra_phase_center=None
        self.dec_phase_center=None
        self.filename=''
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
        self.rfstreamnumber=rfstream

        self.ionex=ionex

        obsinfo=None
        self.observation_number=None
        if url is None:
            url=_BASEURL
        
        if isinstance(input, int):
            # it is a gpstime
            gpstime=input
            obsinfo=fetch_obsinfo(gpstime, URL=url)
        elif isinstance(input, dict):
            # assume it is a obsinfo structure
            obsinfo=input
        if obsinfo is not None:
            self.fromobsinfo(obsinfo)

    ##################################################
    def fromobsinfo(self, obsinfo):
        self.observation_number=obsinfo['starttime']
        self.stoptime=obsinfo['stoptime']
        self.duration=self.stoptime-self.observation_number
        self._Schedule_Metadata=obsinfo['metadata']
        self.calibration=self._Schedule_Metadata['calibration']
        self.calibrators=self._Schedule_Metadata['calibrators']
        self.filename=obsinfo['obsname']
        self.inttime=obsinfo['int_time']
        self.fine_channel=obsinfo['freq_res']
        self.creator=obsinfo['creator']
        self.projectid=obsinfo['projectid']
        self.mode=obsinfo['mode']
        self.ra_phase_center=obsinfo['ra_phase_center']
        self.dec_phase_center=obsinfo['dec_phase_center']

        try:
            RFstream=obsinfo['rfstreams'][self.rfstreamnumber]
        except KeyError:
            try:
                RFstream=obsinfo['rfstreams'][str(self.rfstreamnumber)]
            except KeyError:
                logger.error('RFstream %d not present in observation %d' % (self.rfstreamnumber,
                                                                            self.observation_number))
                return None

                         
        try:
            self.channels=RFstream['frequencies']
            self.center_channel=RFstream['frequencies'][len(RFstream['frequencies'])/2]
        except IndexError:
            self.center_channel=None
        mwa=ephem_utils.Obs[ephem_utils.obscode['MWA']]
        if 'ra' in RFstream.keys() and RFstream['ra'] is not None:
            logger.info('Found (RA,Dec) in RFstream (%.5f,%.5f)\n' % (
                RFstream['ra'],RFstream['dec']))
            self.RA=RFstream.ra
            self.Dec=RFstream.dec
            mwatime=ephem_utils.MWATime(gpstime=self.observation_number)
            
            self.azimuth,self.elevation=ephem_utils.radec2azel(self.RA,self.Dec,
                                                         self.observation_number)
            self.HA=ephem_utils.HA(self.LST,self.RA,self.Dec,self.epoch)/15.0
    
        elif (RFstream['azimuth'] is not None):
            logger.info('Found (Az,El) in RFstream (%.5f,%.5f)\n' % (
                RFstream['azimuth'],RFstream['elevation']))
            self.azimuth=RFstream['azimuth']
            self.elevation=RFstream['elevation']            
            self.RA,self.Dec=ephem_utils.azel2radec(self.azimuth,self.elevation,
                                              self.observation_number)
            self.HA=ephem_utils.HA(self.LST,self.RA,self.Dec,self.epoch)/15.0
            
        elif (RFstream['hex'] is not None and len(RFstream['hex'])>0):
            logger.info('Found delays in RFstream (%s)\n' % (
                RFstream['hex']))
            
            self.delays=[int(x) for x in RFstream['hex'].split(',')]
            self.azimuth,za=delays2azza(self.delays)
            self.elevation=90-za
            self.RA,self.Dec=ephem_utils.azel2radec(self.azimuth,self.elevation,
                                              self.observation_number)
            self.HA=ephem_utils.HA(self.LST,self.RA,self.Dec,self.epoch)/15.0
        else:
            logger.warning('No coordinate specified in RFstream:\n %s\n' % RFstream)
        if (len(self.delays)==0):
            # still need to get the delays                
            self.delays=RFstream['delays']
        if self.delays is None or len(self.delays)==0:
            logger.warning('Unable to find a valid delay setting')
            self.delays=[0]*16



    ##################################################
    def __str__(self):
        if (self.observation_number is None):
            return "None"
        s='%s at %d (GPS) [RFstream=%d] [project=%s]\n' % (self.filename,self.observation_number,
                                                           self.rfstreamnumber,
                                                           self.projectid)
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
        #if (len(self.receivers)>0):
        #    s+='receivers = %s\n' % (','.join([str(x) for x in self.receivers]))
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
class MWA_tile_config():
    """
    class MWA_tile_config(ileinfo=None, pol='X')
    holds configuration information for a single tile/polarization:

    tilename
    recevier number
    slot number
    input number
    antenna number
    polarization
    length (electrical + physical)
    flag status
    per-channel gains
    beamformer delays
    cable flavor

    this can be used to generate an instr_config file


    tile is like 11,12
    antenna is like 0, 1 (ordinal numbers)
    
    
    """
    
    ##################################################    
    def __init__(self, tileinfo=None, pol='X'):
                
        self.tile=None
        self.tilename=None
        self.inputnumber=None
        self.antenna=None
        self.receiver=None
        self.slot=None

        self.pol=pol
        self.length=None
        self.flag=False
        self.electrical=None
        self.gains=None
        self.delays=None
        self.flavor=None
        self.tile_pos_east,self.tile_pos_north=0,0
        self.tile_altitude=None
        self.beamformer=None
        self.cable_attenuation=None
        self.beamformer_gain=None
                
        if tileinfo is not None:
            self.fromtileinfo(tileinfo)



    ##################################################    
    def fromtileinfo(self, tileinfo):
        self.receiver=tileinfo['receiver']
        self.slot=tileinfo['slot']
        if tileinfo['flagged'] is not None:
            self.flag=tileinfo['flagged']
        if self.pol=='X':
            self.inputnumber=2*(tileinfo['inputnum']-1)+1
            self.beamformer_gain=tileinfo['bfgainx']
        elif self.pol=='Y':
            self.inputnumber=2*(tileinfo['inputnum']-1)+0            
            self.beamformer_gain=tileinfo['bfgainy']
        self.flavor=tileinfo['flavor']
        self.gains=tileinfo['dgains']
        self.tile_pos_east,self.tile_pos_north=tileinfo['pos']
        self.tile_altitude=tileinfo['altitude']
        # length is total electrical length
        self.length=tileinfo['ted']
        self.electrical=True
        self.beamformer=tileinfo['bf']
        self.cable_attenuation=tileinfo['catten']
        self.tile=tileinfo['id']
        self.tilename='Tile%03d' % self.tile        

    def __str__(self):
        return self.tilename + self.pol


######################################################################
class instrument_configuration():
    """
    """


    ##################################################    
    def __init__(self, input,
                 rfstream=0, min_bad_dipoles=2, coarse_channels=24,
                 n_inputs=_NINP_128T, timeoffset=0, lock=False, url=_BASEURL):
        self.min_bad_dipoles=min_bad_dipoles
        self.tiles={}
        self.inputs={}
        self.duration=0
        self.ninputs=_NINP_128T
        self.ninputsperrx=_INPUTSPERRX
        self.obs=None
        self.RA=None
        self.HA=None
        self.Dec=None
        self.channel_selection=None
        self.rfstreamnumber=rfstream
        self.receivers=set()
        self.coarse_channels=coarse_channels
        self.coarse_channel=None
        self.n_inputs=n_inputs
        self.timeoffset=timeoffset
        self.n_scans=None

        self.corrtype='B'
        self.invert_freq=0
        self.conjugate=1
        self.lock=lock

        obsinfo=None
        if url is None:
            self.url=_BASEURL
        else:
            self.url=url
            
        if isinstance(input, int):
            # it is a gpstime
            gpstime=input
            obsinfo=fetch_obsinfo(gpstime, URL=self.url)
        elif isinstance(input, dict):
            # assume it is a obsinfo structure
            obsinfo=input
        if obsinfo is not None:
            self.fromobsinfo(obsinfo)

    ##################################################    
    def fromobsinfo(self, obsinfo):
        self.gpstime=obsinfo['starttime']
        self.stoptime=obsinfo['stoptime']
        self.obs=MWA_Observation(obsinfo, rfstream=0, ionex=False)
        self.duration=self.stoptime-self.gpstime
        self.mwatime=ephem_utils.MWATime(gpstime=self.gpstime)
        
        if self.channel_selection is None or len(self.channel_selection)==0:
            self.channel_selection=numpy.arange(len(self.obs.channels))
        if isinstance(self.channel_selection,list):
            self.channel_selection=numpy.array(self.channel_selection)
        if len(self.channel_selection)<self.coarse_channels:
            logger.warning('Will only select %d coarse channels' % len(self.channel_selection))
            self.coarse_channels=len(self.channel_selection)
        if self.n_scans is None:
            self.n_scans=int((self.obs.duration)/self.obs.inttime)
        # in MHz
        self.bandwidth=self.coarse_channels * 1.28
        # fine channel is in kHz
        self.n_chans=int(self.bandwidth*1e3/(self.obs.fine_channel))
        if (self.coarse_channels==24 and len(self.channel_selection)==self.coarse_channels):
            self.channel=self.obs.center_channel
        else:
            if self.coarse_channels > 1:
                try:
                    self.channel=numpy.array(self.obs.channels)[self.channel_selection][self.coarse_channels/2]
                except IndexError:
                    if (isinstance(self.obs.channels,int)):
                        self.channel=numpy.arange(self.obs.channels-12,self.obs.channels+12)[self.coarse_channels/2]
                    elif len(self.obs.channels)==1:
                        self.channel=numpy.arange(self.obs.channels[0]-12,self.obs.channels[0]+12)[self.coarse_channels/2]                    
            else:
                if self.coarse_channel is None:
                    logger.error('Need to specify which coarse channel is being processed')
                    return False
                self.channel=self.obs.channels[self.coarse_channel]
                logger.info('Selecting coarse channel number %d: %d' % (self.coarse_channel,self.channel))

        if self.RA is None:
            try:
                self.RA=self.obs.RA
                self.Dec=self.obs.Dec
            except:
                logger.info('Setting RA,Dec from phase center')
                self.RA=self.obs.ra_phase_center
                self.Dec=self.obs.dec_phase_center

        self.RFstreams=obsinfo['rfstreams']

        # the primary RFstream is just used for pointing info
        try:
            self.RFstream=obsinfo['rfstreams'][self.rfstreamnumber]
        except KeyError:
            try:
                self.RFstream=obsinfo['rfstreams'][str(self.rfstreamnumber)]
            except KeyError:                
                logger.error('RFstream %d not present in observation %d' % (self.rfstreamnumber,
                                                                            self.gpstime))
                return None

        self.gettileinfo()

    ##################################################
    # def __getattr__(self, name):
    #     """
    #     can get attributes from MWA_Observation instance if needed
    #     """
    #     if name in self.__dict__.keys():
    #         return self.__dict__[name]
    #     else:
    #         if name in self.obs.__dict__.keys():
    #             return self.obs.__dict__[name]
    #         # if we get here it's to raise an exception
    #         return self.__dict__[name]
            

    ##################################################
    def gettileinfo(self):

        tileinfo=fetch_tileinfo(self.gpstime, URL=self.url)
        if tileinfo is None:
            return None
        for t in tileinfo.keys():
            for stream in self.RFstreams.keys():
                RFstream=self.RFstreams[stream]
                # figure out which tiles and which polarizations
                # are included in this RFstream
                if t in RFstream['tileset']['xlist'] and t in RFstream['tileset']['ylist']:
                    logger.debug('Tile %d in RFstream %d' % (t,RFstream['number']))
                    self.tiles[t]={'X': MWA_tile_config(tileinfo[t], pol='X'),
                                   'Y': MWA_tile_config(tileinfo[t], pol='Y')}
                    self.inputs[self.tiles[t]['X'].inputnumber]=self.tiles[t]['X']
                    self.inputs[self.tiles[t]['Y'].inputnumber]=self.tiles[t]['Y']
                elif t in RFstream['tileset']['xlist']:
                    self.tiles[t]={'X': MWA_tile_config(tileinfo[t], pol='X')}
                    self.inputs[self.tiles[t]['X'].inputnumber]=self.tiles[t]['X']
                elif t in RFstream['tileset']['ylist']:
                    self.tiles[t]={'Y': MWA_tile_config(tileinfo[t], pol='Y')}
                    self.inputs[self.tiles[t]['Y'].inputnumber]=self.tiles[t]['Y']

        # determine the delays
        for t in sorted(self.tiles.keys()):
            for stream in self.RFstreams.keys():
                RFstream=self.RFstreams[stream]
                # get the delays for the tiles
                if self.tiles[t]['X'].tile in RFstream['tileset']['xlist']:
                    self.tiles[t]['X'].delays=numpy.array(RFstream['delays'])
                    # and flag individual dipole delays if they are listed as bad
                    if t in RFstream['bad_dipoles'].keys() and len(RFstream['bad_dipoles'][t][0])>0:
                        self.tiles[t]['X'].delays[numpy.array(RFstream['bad_dipoles'][t][0])-1]=_BAD_DIPOLE_DELAY
                    if self.tiles[t]['Y'].tile in RFstream['tileset']['ylist']:
                        self.tiles[t]['Y'].delays=numpy.array(RFstream['delays'])
                    # and flag individual dipole delays if they are listed as bad
                    if t in RFstream['bad_dipoles'].keys() and len(RFstream['bad_dipoles'][t][1])>0:
                        self.tiles[t]['Y'].delays[numpy.array(RFstream['bad_dipoles'][t][1])-1]=_BAD_DIPOLE_DELAY
    
        # delays should be filled now
        antenna_number=0
        for t in sorted(self.tiles.keys()):
            for stream in self.RFstreams.keys():
                RFstream=self.RFstreams[stream]
                try:
                    tilex=self.tiles[t]['X']
                    self.receivers.add(tilex.receiver)
                    tilex.antenna=antenna_number
                except:
                    tilex=None
                try:
                    tiley=self.tiles[t]['Y']
                    self.receivers.add(tiley.receiver)
                    tiley.antenna=antenna_number
                except:
                    tiley=None
                # flag tiles if too many of their delays are "bad"
                if tilex is not None and ((tilex.delays==_BAD_DIPOLE_DELAY).sum()>= self.min_bad_dipoles) and not tilex.flag:
                    logger.info('Flagging tile %d because %d X dipole(s) are bad' % (tilex.tile,
                                                                                     (tilex.delays==_BAD_DIPOLE_DELAY).sum()))
                    tilex.flag=True
                    if tiley is not None:
                        tiley.flag=True
                if tiley is not None and ((tiley.delays==_BAD_DIPOLE_DELAY).sum()>= self.min_bad_dipoles) and not tiley.flag:
                    logger.info('Flagging tile %d because %d Y dipole(s) are bad' % (tiley.tile,
                                                                                     (tiley.delays==_BAD_DIPOLE_DELAY).sum()))
                    if tilex is not None:
                        tilex.flag=True
                    tiley.flag=True
                # flag if they are listed in the bad_tiles set
                if t in RFstream['bad_tiles']:
                    logger.info('Flagging tile %d' % t)
                    if tilex is not None:
                        tilex.flag=True
                    if tiley is not None:
                        tiley.flag=True

            antenna_number+=1




    ##################################################    
    def __str__(self):
        preamble="""##################################################
# this file maps inputs into the receiver/correlator to antennas and polarisations.
# in addition, a cable length delta (in meters) can be specified
# the first column is not actually used by the uvfits writer, but is there as
# an aide to human readers. Inputs are ordered from 0 to n_inp-1
# antenna numbering starts at 0 and is an index into the corresponding antenna_locations.txt file
# lines beginning with '\#' and blank lines are ignored. Do not leave spaces in empty lines.
#
# Input flagging: put a 1 in the flag column to flag all data from that input.
#                 0 means no flag.
# Cable lengths: if length is prefixed by EL_ then no velocity correction factor is needed
"""
        s=preamble
        #s+='# Written by %s\n' % (__file__.split('/')[-1])        
        s+='# for observation at %d\n' % (self.gpstime)
        now=datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        s+='# %s\n' % now
        s+="""##################################################
# INPUT   ANTENNA   POL     DELTA   FLAG 
"""

        for inputnumber in sorted(self.inputs.keys()):
            if (self.inputs[inputnumber].flag):
                f=1
            else:
                f=0
            length='%.2f' % self.inputs[inputnumber].length
            if self.inputs[inputnumber].electrical:
                length='EL_' + length
            s+="%d\t%d\t%s\t%s\t%d" % (inputnumber, self.inputs[inputnumber].antenna,
                                       self.inputs[inputnumber].pol.upper(),
                                       length, f)

            s+=' # Rx%03d Slot%02d %s\n' % (self.inputs[inputnumber].receiver,
                                            self.inputs[inputnumber].slot,
                                            self.inputs[inputnumber].tilename)

        return s

    ##################################################    
    def instr_config(self):
        return self.__str__()

    ##################################################
    def antenna_locations(self):
        preamble="""# lines beginning with \'#\' and blank lines are ignored. Do not leave spaces in empty lines.
# locations of antennas relative to the centre of the array in local topocentric
# \"east\", \"north\", \"height\". Units are meters.
# Format: Antenna_name east north height
# antenna names must be 8 chars or less
# fields are separated by white space
"""
        s=preamble
        #s+='# Written by %s\n' % (__file__.split('/')[-1])        
        s+='# for observation at %d\n' % (self.gpstime)
        now=datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        s+='# %s\n' % now
        for t in sorted(self.tiles.keys()):
            tile=None
            if 'X' in self.tiles[t].keys():
                tile=self.tiles[t]['X']
            elif 'Y' in self.tiles[t].keys():
                tile=self.tiles[t]['Y']
            if tile is not None:
                s+='%s %09.3f %09.3f %08.3f\n' % (tile.tilename,tile.tile_pos_east,
                                                  tile.tile_pos_north,tile.tile_altitude)
                
        return s
    ##################################################
    def make_metafits(self, quick=False):

        h=pyfits.PrimaryHDU()
        head=h.header
        head.set('GPSTIME',self.gpstime,'[s] GPS time of observation start')
        
        if self.duration>0:
            head.set('EXPOSURE',self.duration,'[s] duration of observation')

        if self.channel_selection is None or len(self.channel_selection)==0:
                self.channel_selection=numpy.arange(len(self.obs.channels))
        if isinstance(self.channel_selection,list):
                self.channel_selection=numpy.array(self.channel_selection)
        head.set('FILENAME',self.obs.filename,'Name of observation')
        head.set('MJD',self.obs.MJD,'[days] MJD of observation')
        head.set('DATE-OBS','%04d-%02d-%02dT%02d:%02d:%02d' % (
            self.obs.year,
            self.obs.month,self.obs.day,
            self.obs.hour,self.obs.minute,self.obs.second),'[UT] Date and time of observation')
        if self.obs.LST is not None:
            head.set('LST',self.obs.LST,'[deg] LST')
        if self.obs.HA is not None:
            head.set('HA',ephem_utils.dec2sexstring(self.obs.HA,digits=0,roundseconds=1),
                        '[hours] hour angle')
        if (self.obs.azimuth is not None):
            head.set('AZIMUTH',self.obs.azimuth,'[deg] Azimuth of pointing center')
            head.set('ALTITUDE',self.obs.elevation,'[deg] Altitude of pointing center')
        if (self.obs.RA is not None):
            head.set('RA',self.obs.RA,'[deg] RA of pointing center')
            head.set('DEC',self.obs.Dec,'[deg] Dec of pointing center')
        if (self.obs.ra_phase_center is not None):
            head.set('RAPHASE',self.obs.ra_phase_center,
                        '[deg] RA of desired phase center')
            head.set('DECPHASE',self.obs.dec_phase_center,
                        '[deg] DEC of desired phase center')
        if self.obs._Schedule_Metadata is not None:
            head.set('SUN-DIST',self.obs._Schedule_Metadata['sun_pointing_distance'],
                        '[deg] Distance from pointing center to Sun')
            head.set('MOONDIST',self.obs._Schedule_Metadata['moon_pointing_distance'],
                        '[deg] Distance from pointing center to Moon')
            head.set('JUP-DIST',self.obs._Schedule_Metadata['jupiter_pointing_distance'],
                        '[deg] Distance from pointing center to Jupiter')
            if len(self.obs._Schedule_Metadata['gridpoint_name'])>0:
                head.set('GRIDNAME',self.obs._Schedule_Metadata['gridpoint_name'],
                            'Pointing grid name')
                head.set('GRIDNUM',self.obs._Schedule_Metadata['gridpoint_number'],
                            'Pointing grid number')
        head.set('CREATOR',self.obs.creator.strip(),'Observation creator')
        head.set('PROJECT',self.obs.projectid.strip(),'Project ID')
        head.set('MODE',self.obs.mode,'Observation mode')
        if (len(self.receivers)>0):
            head.set('RECVRS',','.join([str(x) for x in self.receivers]),'Active receivers')
        if (len(self.obs.delays)>0):
            head.set('DELAYS',','.join([str(x) for x in self.obs.delays]),'Beamformer delays')
        if (self.obs.calibration is not None):
            if (self.obs.calibration):
                head.set('CALIBRAT',True,'Intended for calibration')
                head.set('CALIBSRC',self.obs.calibrators.strip(),'Calibrator source')
            else:
                head.set('CALIBRAT',False,'Intended for calibration')
        gains=None
        if self.obs.center_channel is not None:
            head.set('CENTCHAN',self.obs.center_channel,'Center coarse channel')

        head.set('CHANNELS',','.join([str(x) for x in numpy.array(self.obs.channels)[self.channel_selection]]),'Coarse channels')
        #if gains is not None:
        #    head.set('CHANGAIN',','.join([str(x) for x in gains]),'Coarse channel gains')
        head.set('CHANSEL',','.join(map(str,self.channel_selection)),'Subset of total channels used')

        head.set('SUN-ALT',self.obs.sun_elevation,'[deg] Altitude of Sun')
        
        try:
                head.set('FIBRFACT',self.fiber_velocity_factor,'Fiber velocity factor')
        except AttributeError:
                pass
        head.set('FINECHAN',self.obs.fine_channel,'[kHz] Fine channel width')
        head.set('INTTIME',self.obs.inttime,'[s] Individual integration time')

        #head.set('TILEFLAG',','.join([str(x) for x in self.tiles_to_flag]),'Tiles flagged')
        nav_freq=int(self.obs.fine_channel/10)
        head.set('NAV_FREQ',nav_freq,'Assumed frequency averaging')

        head.set('NSCANS',self.n_scans,'Number of scans (time instants) in correlation products')
        head.set('NINPUTS',self.n_inputs,'Number of inputs into the correlation products')
        head.set('NCHANS',self.n_chans,'Number of fine channels in spectrum')
        head.set('BANDWDTH',self.bandwidth,'[MHz] Total bandwidth')
        head.set("FREQCENT",channel2frequency(self.channel)+(nav_freq-1)*0.005,
                    '[MHz] Center frequency of observation')
        head.set('TIMEOFF',0,
                    '[s] Offset between observation starttime and start of correlations')
        head.set('DATESTRT',self.mwatime.strftime('%Y-%m-%dT%H:%M:%S'),
                    '[UT] Date and time of correlations start')
        head.set('VERSION',_VERSION,'METAFITS version number')
        head.set('MWAVER',mwapy.__version__,'MWAPY version number')
        head.set('MWADATE',mwapy.__date__,'MWAPY version date')
        head.set('TELESCOP','MWA128T')

        Input=[]
        Antenna=[]
        Pol=[]
        Delta=[]
        Flag=[]
        Length=[]
        Rx=[]
        Slot=[]
        Tile=[]
        North=[]
        East=[]
        Height=[]
        Gains=[]
        Delays=[]

        for inputnumber in sorted(self.inputs.keys()):
            tile=self.inputs[inputnumber]
            if (tile.flag):
                f=1
            else:
                f=0
            length='%.2f' % tile.length
            if tile.electrical:
                length='EL_' + length
            Input.append(inputnumber)
            Antenna.append(tile.antenna)
            Pol.append(tile.pol.upper())
            Length.append(length)
            Flag.append(f)
            Rx.append(tile.receiver)
            Slot.append(tile.slot)
            Tile.append(tile.tile)
            North.append(tile.tile_pos_north)
            East.append(tile.tile_pos_east)
            Height.append(tile.tile_altitude)
            # select only the appropriate values for the channels used
            Gains.append(numpy.array(tile.gains)[numpy.array(self.obs.channels)][self.channel_selection])
            Delays.append(numpy.array(tile.delays))

        if not quick:
            col1=pyfits.Column(name='Input',format='I',array=Input)
            col2=pyfits.Column(name='Antenna',format='I',array=Antenna)
            col3=pyfits.Column(name='Tile',format='I',array=Tile)
            col4=pyfits.Column(name='Pol',format='A',array=Pol)
            col5=pyfits.Column(name='Rx',format='I',array=Rx)
            col6=pyfits.Column(name='Slot',format='I',array=Slot)
            col7=pyfits.Column(name='Flag',format='I',array=Flag)
            col8=pyfits.Column(name='Length',format='A14',array=Length)
            col9=pyfits.Column(name='North',format='E',unit='m',array=North)
            col10=pyfits.Column(name='East',format='E',unit='m',array=East)
            col11=pyfits.Column(name='Height',format='E',unit='m',array=Height)
            col12=pyfits.Column(name='Gains',format='%dI' % len(Gains[0]),array=Gains)
            col13=pyfits.Column(name='Delays',format='%dI' % len(Delays[0]), array=Delays)
            try:
                # this works in the newer pyfits (and astropy?)
                # but not the older versions
                tbhdu=pyfits.BinTableHDU.from_columns([col1,col2,col3,col4,col5,col6,col7,col8,col9,col10,col11,col12,col13])
                tbhdu.name='TILEDATA'
            except:
                # in the newer pyfits/astropy this produces lots of warnings
                tbhdu=pyfits.new_table([col1,col2,col3,col4,col5,col6,col7,col8,col9,col10,col11,col12,col13])
                tbhdu.update_ext_name('TILEDATA',comment='Data about the tile/slot/Rx mapping')
            #tbhdu=pyfits.BinTableHDU(name='TILEDATA')
            #tbhdu.from_columns([col1,col2,col3,col4,col5,col6,col7,col8,col9,col10,col11,col12,col13])
            hdulist=pyfits.HDUList([h,tbhdu])
        else:
            hdulist=pyfits.HDUList([h])
        now=datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        head.set('DATE',now,'UT Date of file creation')
        #head.add_comment('Written by %s\n' % (__file__.split('/')[-1]))
        
        #hdulist=pyfits.HDUList([h,tbhdu])
        


        return hdulist

    ##################################################
    def make_header(self):
        """
        make_header(self)
        """
        if self.RA is None or self.Dec is None:
            logger.error('Cannot construct header.txt without valid RA and Dec')
            return False
        if self.gpstime is None:
            logger.error('Cannot construct header.txt without valid gpstime')
            return False


        # make header.txt
        header="# uvfits header obs id: %d (%s after chopping off first %d sec of data)\n" % (
            self.gpstime,self.mwatime.strftime('%Y/%m/%d %H:%M:%S'),self.timeoffset)
        header+="# blank lines and lines beginning with \'#\' are ignored. Do not leave spaces in empty lines.\n"
        header+="# line format: key value comments\n"

        header+="FIELDNAME %s\n" % self.obs.filename
        header+="N_SCANS   %-3d   # number of scans (time instants) in correlation products\n" % (self.n_scans)
        header+="N_INPUTS  %-3d   # number of inputs into the correlation products\n" % (self.n_inputs)
        header+="N_CHANS   %-3d   # number of channels in spectrum\n" % (self.n_chans)
        header+="CORRTYPE  %s     # correlation type to use. \'C\'(cross), \'B\'(both), or \'A\'(auto)\n" % (self.corrtype)
        header+="INT_TIME  %.1f   # integration time of scan in seconds\n" % (self.obs.inttime)
        if self.channel is not None:
            nav_freq=int(self.obs.fine_channel/10)
            # correct for averaging            
            header+="FREQCENT  %.3f # observing center freq in MHz\n" % (
                channel2frequency(self.channel)+(nav_freq-1)*0.005)
        else:
            logger.warning('No center channel specified; corr2uvfits will not be happy')
            
        header+="BANDWIDTH %.3f  # total bandwidth in MHz\n" % (self.bandwidth)
        header+="RA_HRS    %.6f   # the RA of the desired phase centre (hours)\n" % (self.obs.ra_phase_center/15.0)
        if self.lock:
           header+="HA_HRS    %.6f   # the HA at the *start* of the scan. (hours)\n" % (self.HA)

        header+="DEC_DEGS  %.4f   # the DEC of the desired phase centre (degs)\n" % (self.obs.dec_phase_center)
        header+="DATE      %s  # YYYYMMDD\n" % (self.mwatime.strftime('%Y%m%d'))
        header+="TIME      %s      # HHMMSS\n" % (self.mwatime.strftime('%H%M%S'))
        header+="INVERT_FREQ %d # 1 if the freq decreases with channel number\n" % (self.invert_freq)
        
        self.header=header



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


######################################################################
def channel2frequency(channel):
    """
    returns center frequency (in MHz) given a channel
    assumes 10 kHz fine channels and 1.28 MHz coarse channels
    """
    return 1.28*channel-0.64
######################################################################
def from_iterable(iterable):
    """
    from_iterable(['ABC', 'DEF']) --> A B C D E F
    replaces chain.from_iterable which is not available in python 2.5
    """

    for it in iterable:
        for element in it:
            yield element
######################################################################
def ternary(condition, value1, value2):
    """
    python 2.4 does not have a ternary operator
    so redo it here
    """
    if (condition):
        return value1
    else:
        return value2    



##################################################
def find_observations(GPSstart, GPSstop, limit=1000, url=_BASEURL):
    """
    return gpstimes of all observations between GPSstart and GPSstop
    """
    results=fetch_observations(URL=url,
                               mintime=GPSstart,
                               maxtime=GPSstop,
                               limit=limit)
    if results is None or len(results)==0:
        return []
    else:
        return [x[0] for x in results]
##################################################
def find_closest_observation(GPStime, maxdiff=10, url=_BASEURL):
    """
    return the observation closest to GPStime
    """
    gpstimes=numpy.array(find_observations(GPStime-maxdiff/2, GPStime+maxdiff/2,
                                           url=url))
    if gpstimes is None or len(gpstimes)==0:
        return None    
    tdiff=numpy.abs(gpstimes-GPStime)
    return (gpstimes[tdiff==tdiff.min()])[0]
