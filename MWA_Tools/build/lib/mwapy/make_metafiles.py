"""
gpstime=1028714112

T=make_metafiles.instrument_configuration(gpstime=gpstime, db=db)
T.make_instr_config()
print T
print T.antenna_locations()

h=make_metafiles.Corr2UVFITSHeader(gpstime, coarse_channels=12, db=db)
h.make_header()
print h


"""

# metafits format version number
_VERSION=1.0

import sys,os,logging,shutil,datetime,re,subprocess,math,tempfile,string,glob,copy
import numpy,ephem,pyfits
import itertools
from optparse import OptionParser,OptionGroup
from mwapy import ephem_utils, dbobj
from mwapy import get_observation_info, splat_average
import psycopg2
import mwapy

# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('make_metafiles')
logger.setLevel(logging.INFO)

try:
    from mwapy.obssched.base import schedule
except:
    logger.error("Unable to open connection to database")
    sys.exit(1)

# open up database connection
try:
    db = schedule.getdb()
except:
    logger.error("Unable to open connection to database")
    sys.exit(1)

# GPStime corresponding to the start of 128T
# 2013-03-03
_START_128T=1046304456
# 32 antennas * 2 polns
_NINP_32T=64
_NINP_128T=256
# 16 inputs (16 antennas * 2 polns) go into each Rx
_INPUTSPERRX=16
# default digital gain
_DEFAULT_GAIN=64
# total number of coarse channels
_NUM_COARSE_CHANNELS=256

# configuration for different correlator options
# set the starttime (gpstime), integration time, and fine channel width for each setup
# 0, 2012-09-01, 2013-04-01
# add dates for mode experimentation, 2013-08-01 or so, DDT time
_START=[0,1030492816,1048809616, 1059241152, 1059304872, 1059319096+8]
# integration time in s
_DT=[1,1,0.5,1,2,0.5]
# fine channel width in kHz
_DF=[40,10,40,10,10,40]
######################################################################
class tile_config():
    """
    class tile_config()
    holds configuration information for a single tile/polarization:

    tilename
    recevier number
    slot number
    input number
    polarization
    length (electrical + physical)
    flag status
    per-channel gains

    this can be used to generate an instr_config file
    """
    
    ##################################################    
    def __init__(self, tile=None, tilename=None,
                 receiver=None, slot=None, inputnumber=None, pol=None, length=None, flag=False, electrical=True, gains=[]):
        self.tile=tile
        self.tilename=tilename
        self.receiver=receiver
        self.slot=slot
        self.inputnumber=inputnumber
        self.pol=pol
        self.length=length
        self.flag=flag
        self.electrical=electrical
        self.gains=gains

######################################################################
class instrument_configuration():
    """
    generates an instrument configuration
    maps input number into antenna/polarization
    also includes electrical length and whether or not to flag the input

    and also determines antenna_locations.txt file contents

    Usage:

    gpstime=1001175315
    T=instrument_configuration(gpstime=gpstime, db=db)
    T.make_instr_config()
    print T
    print T.antenna_locations()
    """


    ##################################################    
    def __init__(self, gpstime=None, duration=None, db=None, debug=False):
        self.inputs={}
        self.db=db        
        self.tiles_to_flag=set([])
        self.tiles=[]
        self.gpstime=gpstime
        self.mwatime=ephem_utils.MWATime(gpstime=self.gpstime)
        self.duration=0
        self.ninputs=_NINP_128T
        self.ninputsperrx=_INPUTSPERRX
        self.obs=None
	self.RA=None
	self.HA=None
	self.Dec=None
        self.corr2uvfitsheader=None
        self.debug=debug
        if duration is not None:
            self.duration=duration
        

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
        s+='# Written by %s\n' % (__file__.split('/')[-1])        
        s+='# for observation at %d\n' % (self.gpstime)
        now=datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        s+='# %s\n' % now
        s+="""##################################################
# INPUT   ANTENNA   POL     DELTA   FLAG 
"""

        y=sorted(self.tiles, key=lambda t: t.tile_id)
        y_id=numpy.array([t.tile_id for t in y])
        for inputnumber in sorted(self.inputs.keys()):
            if (self.inputs[inputnumber].flag):
                f=1
            else:
                f=0
            i=numpy.where(y_id==self.inputs[inputnumber].tile)[0][0]
            length='%.2f' % self.inputs[inputnumber].length
            if self.inputs[inputnumber].electrical:
                length='EL_' + length
            s+="%d\t%d\t%s\t%s\t%d" % (inputnumber, i,
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
        s+='# Written by %s\n' % (__file__.split('/')[-1])        
        s+='# for observation at %d\n' % (self.gpstime)
        now=datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        s+='# %s\n' % now
        for t in sorted(self.tiles, key=lambda t: t.tile_id):
            if not 'tilename' in t.__dict__.keys():
                t.tilename='Tile%d' % t.tile_id
            s+='%s %09.3f %09.3f %08.3f\n' % (t.tilename,t.tile_pos_east,
                                              t.tile_pos_north,t.tile_altitude)
        return s

    ##################################################   
    def get_tiles_to_flag(self):
        """
        determines the tiles to flag based on the observation time
        """
        if (self.db is None):
            logger.error('Cannot retrieve flagging information without database connection')
            return
        
        try:
            flagged_tiles=list(itertools.chain(*dbobj.execute('select tile_id from tile_flags where starttime<%d and stoptime>%d' % (
                self.gpstime+self.duration,self.gpstime),db=self.db)))
        except (psycopg2.InternalError, psycopg2.ProgrammingError) , e:
            logger.warning('Database error=%s' % (e.pgerror))
            db.rollback()

        for x in flagged_tiles:
            self.tiles_to_flag.add(x)
        logger.info('Will flag tiles %s' % list(self.tiles_to_flag))


    ##################################################    
    def make_instr_config(self):
        """
        based on a recipe from Bryna Hazelton
        2012-05

        works for 128T commissioning data 
        """
        if (self.gpstime is None):
            logger.error('Must supply gpstime for determining instr_config')
            return None

        if (self.db is None):
            logger.error('Cannot retrieve configuration information without database connection')
            return None
        
        try:
            self.get_tiles_to_flag()
        except:
            logger.warning('Cannot retrieve flagging information for gpstime=%d' % (self.gpstime))
        
        # figure out which receivers are present
        try:
            receivers_fibers = dbobj.execute('select receiver_id,fibre_length from receiver_info where begintime < %d and endtime > %d' % (self.gpstime,self.gpstime), db=self.db)
        except (psycopg2.InternalError, psycopg2.ProgrammingError) , e:
            logger.warning('Database error=%s' % (e.pgerror))
            db.rollback()
        
        self.receivers,self.fiber_lengths=[],[]
        for x in receivers_fibers:
            self.receivers.append(x[0])
            self.fiber_lengths.append(x[1])
        logger.info('Found receivers %s' % self.receivers)
        if len(self.receivers)<1:
            logger.error('No receivers found for gpstime=%d' % self.gpstime)
            return None

        # figure out which receivers are present but not active
        try:
            inactive_receivers = dbobj.execute('select receiver_id from receiver_info where active = false and begintime < %d and endtime > %d' % (self.gpstime,self.gpstime), db=self.db)
        except (psycopg2.InternalError, psycopg2.ProgrammingError) , e:
            logger.warning('Database error=%s' % (e.pgerror))
            db.rollback()
        self.inactive_receivers=[]
        for x in inactive_receivers:
            self.inactive_receivers.append(x[0])
        if len(self.inactive_receivers)>0:
            logger.info('Found inactive receivers %s' % self.inactive_receivers)

        self.fiber_velocity_factor=None
        try:
            self.fiber_velocity_factor=dbobj.execute('select velocity_factor from cable_velocity_factor where type = \'fiber\'',db=self.db)[0][0]
        except(psycopg2.InternalError, psycopg2.ProgrammingError) , e:
            logger.warning('Database error=%s' % (e.pgerror))
            db.rollback()
        if self.fiber_velocity_factor is None:
            self.fiber_velocity_factor=1
            logger.warning('No fiber_velocity_factor found; using default fiber_velocity_factor=%.2f' % self.fiber_velocity_factor)
        else:
            logger.info('Found fiber_velocity_factor=%.2f' % self.fiber_velocity_factor)
            

            
        for receiver,fiber_length in zip(self.receivers,self.fiber_lengths):
            found_slot_power=False
            try:
                slot_power=dbobj.execute('select slot_power from obsc_recv_cmds where rx_id=%d and starttime=%d' % (
                        ((receiver)),self.gpstime), db=self.db)[0][0]
                logger.info('Found slot power information for starttime=%d, Rx=%d: %s' % (self.gpstime,receiver,slot_power))
                found_slot_power=True
            except (psycopg2.InternalError, psycopg2.ProgrammingError) , e:
                logger.warning('Database error=%s' % (e.pgerror))
                db.rollback()
            except:
                logger.warning('Unable to retrieve slot power information for gpstime=%d, Rx=%d' % (self.gpstime,receiver))

            if not found_slot_power:
                try:
                    slot_power=dbobj.execute('select slot_power from obsc_recv_cmds where rx_id=%d and observation_number=%d' % (
                        ((receiver)),self.gpstime), db=self.db)[0][0]
                    logger.info('Found slot power information for observation_number=%d, Rx=%d: %s' % (self.gpstime,receiver,slot_power))
                    found_slot_power=True
                except (psycopg2.InternalError, psycopg2.ProgrammingError) , e:
                    logger.warning('Database error=%s' % (e.pgerror))
                    db.rollback()
                    
                except:
                    logger.warning('Unable to retrieve slot power information for observation_number=%d, Rx=%d' % (self.gpstime,receiver))

            if not found_slot_power or slot_power is None:
                slot_power=[False]*(self.ninputsperrx/2)                

                
            try:
                command='select correlator_index from pfb_correlator_mapping pc inner join pfb_receiver_connection pr on (pc.pfb_id=pr.pfb_id and pc.pfb_slot=pr.pfb_slot) where pr.rx_id=%d and pr.begintime<%d and pr.endtime>%d and pc.begintime<%d and pc.endtime>%d' % (
                    receiver, self.gpstime, self.gpstime, self.gpstime, self.gpstime)
                correlator_index=dbobj.execute('select correlator_index from pfb_correlator_mapping pc inner join pfb_receiver_connection pr on (pc.pfb_id=pr.pfb_id and pc.pfb_slot=pr.pfb_slot) where pr.rx_id=%d and pr.begintime<%d and pr.endtime>%d and pc.begintime<%d and pc.endtime>%d' % (
                    receiver, self.gpstime, self.gpstime, self.gpstime, self.gpstime), db=self.db)
                if len(correlator_index)==0:
                    logger.error('Could not find correlator_index for Rx=%d and starttime=%d; skipping Rx %d...' % (receiver,self.gpstime,receiver))
                    continue
                logger.info('Rx=%d and starttime=%d maps to correlator_index %s' % (receiver,self.gpstime,correlator_index))
                if (len(correlator_index)>1):
                    logger.warning('Rx=%d and starttime=%d maps to > 1 correlator_index (%s); results may not be valid...' % (
                        receiver,self.gpstime,
                        ','.join([str(y[0]) for y in correlator_index])))                                            
                correlator_index=correlator_index[0][0]
            except (psycopg2.InternalError, psycopg2.ProgrammingError) , e:
                logger.warning('Database error=%s' % (e.pgerror))
                db.rollback()
            
            for rx_slot in xrange(1,self.ninputsperrx/2+1):
                try:
                    tile_num=dbobj.execute('select tile from tile_connection where receiver_id = %d and receiver_slot = %d and begintime<%d and endtime>%d' % (
                        receiver, rx_slot, self.gpstime, self.gpstime), db=self.db)[0][0]
                    corr_product_index=dbobj.execute('select corr_product_index from siteconfig_tilecorrproductmapping where rx_slot=%d' % (rx_slot), db=self.db)[0][0]
                except (psycopg2.InternalError, psycopg2.ProgrammingError) , e:
                    logger.warning('Database error=%s' % (e.pgerror))
                    db.rollback()

                try:
                    cable_electrical_length=dbobj.execute('select eleclength from cable_info ci inner join tile_connection tc on ci.name=tc.cable_name where tc.tile=%d and ci.begintime<%d and ci.endtime>%d and tc.begintime<%d and tc.endtime>%d' % (
                        tile_num, self.gpstime, self.gpstime, self.gpstime, self.gpstime),
                                                          db=self.db)[0][0]
                except (psycopg2.InternalError, psycopg2.ProgrammingError) , e:
                    logger.warning('Database error=%s' % (e.pgerror))
                    db.rollback()

#   Randall Aug 2013: don't need the coax cable velocity factor here any more since we're using
# the coax electrical lengths directly, but the coax velocity factor is tested to be not 1.0 below to
# write the special "EL_" prefix in the instr config files to signify electrical length not physical
# so set it to -1.0
                cable_velocity_factor=-1.0

                y_input_number=(correlator_index-1)*16 + corr_product_index*2
                x_input_number=(correlator_index-1)*16 + corr_product_index*2 + 1

                # total electrical delay
                if cable_electrical_length is None:
                    logger.error('Found no cable length for tile %s' % tile_num)
                    return None
                if fiber_length is None:
                    logger.warning('Found no fiber length for Rx %s; assuming length=0...' % receiver)
                    fiber_length=0
                    
                tile_electrical_delay=(cable_electrical_length - fiber_length / self.fiber_velocity_factor)
                try:
                    tilename=dbobj.execute('select tilename from siteconfig_tile where tilenumber=%d' % (
                        tile_num),
                                           db=self.db)[0][0]
                except (psycopg2.InternalError, psycopg2.ProgrammingError) , e:
                    logger.warning('Database error=%s' % (e.pgerror))
                    db.rollback()

                # per tile per channel digital gains
                tile_gains=[_DEFAULT_GAIN] * _NUM_COARSE_CHANNELS
                try:
                    tile_gains=dbobj.execute('select digital_gain_multipliers from cable_flavor cf inner join cable_info ci on cf.flavor=ci.flavor inner join tile_connection tc on tc.cable_name=ci.name where tc.receiver_id=%d and tc.receiver_slot=%d and tc.endtime > %d and ci.endtime > %d and cf.begintime<%d and cf.endtime>%d' % (
                        receiver, rx_slot, self.gpstime, self.gpstime, self.gpstime, self.gpstime),
                                             db=self.db)[0][0]
                    
                except (psycopg2.InternalError, psycopg2.ProgrammingError) , e:
                    logger.warning('Database error=%s' % (e.pgerror))
                    db.rollback()
                    

                if self.inputs.has_key(x_input_number):
                    logger.warning('Trying to write entry for Tile %dX (Rx %d, Slot %d) on input %d, but an entry already exists on that input (%s%s, Rx %d, Slot %d)' % (
                        tile_num,receiver,rx_slot,x_input_number,
                        self.inputs[x_input_number].tilename,
                        self.inputs[x_input_number].pol.upper(),
                        self.inputs[x_input_number].receiver,
                        self.inputs[x_input_number].slot))
                self.inputs[x_input_number]=tile_config(tile=tile_num, tilename=tilename, receiver=receiver,
                                                        inputnumber=x_input_number,
                                                        length=tile_electrical_delay,
                                                        pol='X', slot=rx_slot, flag=False,
                                                        electrical=cable_velocity_factor != 1,
                                                        gains=tile_gains)
                if self.inputs.has_key(y_input_number):
                    logger.warning('Trying to write entry for Tile %dY (Rx %d, Slot %d) on input %d, but an entry already exists on that input (%s%s, Rx %d, Slot %d)' % (
                        tile_num,receiver,rx_slot,y_input_number,
                        self.inputs[y_input_number].tilename,
                        self.inputs[y_input_number].pol.upper(),
                        self.inputs[y_input_number].receiver,
                        self.inputs[y_input_number].slot))

                self.inputs[y_input_number]=tile_config(tile=tile_num, tilename=tilename, receiver=receiver,
                                                        inputnumber=y_input_number,
                                                        length=tile_electrical_delay,
                                                        pol='Y', slot=rx_slot, flag=False,
                                                        electrical=cable_velocity_factor != 1,
                                                        gains=tile_gains)
                # flagging
                if not slot_power[rx_slot-1]:
                    self.inputs[x_input_number].flag=True
                    self.inputs[y_input_number].flag=True
                if receiver in self.inactive_receivers:
                    logger.info('Flagging tile %d because it belongs to inactive Rx %s' % (tile_num,receiver))
                    self.inputs[x_input_number].flag=True
                    self.inputs[y_input_number].flag=True
                    

                if tile_num in self.tiles_to_flag or str(tile_num) in self.tiles_to_flag:
                    self.inputs[x_input_number].flag=True
                    self.inputs[y_input_number].flag=True                    
                                
                try:
                    id=dbobj.execute('select id from tile_info where tile_id = %s and begintime < %d and endtime > %d'
                                     % (self.inputs[x_input_number].tile,self.gpstime,self.gpstime),
                                     db=self.db)[0][0]
                    tt=schedule.MWA_Tile(id, db=self.db)
                    tt.tilename=self.inputs[x_input_number].tilename
                    if not tt.id in [t.id for t in self.tiles]:
                        self.tiles.append(tt)
                except (psycopg2.InternalError, psycopg2.ProgrammingError) , e:
                    logger.warning('Database error=%s' % (e.pgerror))
                    db.rollback()

                except:
                    logger.error('Unable to get tile_info for tile=%s and gpstime=%d' % (
                        self.inputs[x_input_number].tile,self.gpstime))

        # fill in the remaining slots with fake tiles if necessary
        if self.gpstime < _START_128T:
            # still 32T
            logger.info('Still 32T: using %d inputs' % (_NINP_32T))
            self.ninputs=_NINP_32T
        if (len(self.inputs)<self.ninputs):
            for inputnumber in xrange(0,self.ninputs,2):
                if not self.inputs.has_key(inputnumber):
                    logger.info('Creating fake tile %d' % (501+inputnumber/2))
                    self.inputs[inputnumber]=tile_config(tile=501+inputnumber/2,
                                                         tilename='Tile%d' % (501+inputnumber/2),
                                                         receiver=32,
                                                         inputnumber=inputnumber,
                                                         length=0,
                                                         pol='X',
                                                         slot=1,flag=True,
                                                         gains=[_DEFAULT_GAIN] * _NUM_COARSE_CHANNELS)
                    self.inputs[inputnumber+1]=tile_config(tile=501+inputnumber/2,
                                                           tilename='Tile%d' % (501+inputnumber/2),
                                                           receiver=32,
                                                           inputnumber=inputnumber+1,
                                                           length=0,
                                                           pol='Y',
                                                           slot=1,flag=True,
                                                           gains=[_DEFAULT_GAIN] * _NUM_COARSE_CHANNELS)                        
                    self.tiles.append(copy.deepcopy(self.tiles[-1]))
                    self.tiles[-1].tile_id=501+inputnumber/2
                    self.tiles[-1].tilename='Tile%d' % self.tiles[-1].tile_id
        return True
 
    ##################################################  
    def rts_in(self, rtstime = None):
        
        if self.obs is None:
            self.obs=get_observation_info.MWA_Observation(observation_number=self.gpstime, db=db)

	if rtstime is not None:
            self.mwatime=ephem_utils.MWATime(datetime=rtstime)

        db_mwatime = ephem_utils.MWATime(gpstime=self.gpstime)

        s='// RTS configuration file\n'
	s+='// Written by %s\n' % (__file__.split('/')[-1])        
        s+='// for  database at ObsID: %d UT: %s \n' % (self.gpstime,db_mwatime)
        s+='// but positions evaluated at: %s \n' % (self.mwatime)
	s+='useStoredCalibrationFiles=0\n' 
	s+='ArrayNumberOfStations= %d\n' % (self.ninputs/2)
	s+='ArrayFile=array_file.txt\n'
	s+='applyDIcalibration=1\n'
	s+='doRawDataCorrections=1\n'
	s+='doMWArxCorrections=1\n'
	s+='doRFIflagging=0\n'
	s+='useFastPrimaryBeamModels=1\n'
	s+='UseCorrelatorInput=1\n'
	s+='UsePacketInput=0\n'
	s+='UseThreadedVI=0\n'
	s+='CorrelatorPort=65535\n'
	s+='CorrDumpTime=1\n'
	s+='CorrDumpsPerCadence=8\n'
	s+='NumberOfIntegrationBins=3\n'
	s+='SkipPrimaryHeader=1\n'
	s+='//Assumes 296 second observations\n'
	s+='NumberOfIterations=37\n'
	s+='NumberOfChannels=32\n'
	s+='ChannelBandwidth=0.04\n'
	s+='ReadAllFromSingleFile=1\n'
	s+='ObservationFrequencyBase=156.8\n'
	s+='// The following RA/Dec is in Epoch of Date - NOT FK5/J2000\n'
	s+='ObservationPhaseCentreRA=%f\n' % ((float(self.mwatime.LST)/360.0) * 24.0)
	s+='ObservationPhaseCentreDec=-26.703319\n'
	      
        if self.RA is None:
            if (self.obs._MWA_Setting.ra_phase_center is not None):
                logger.info('Setting RA,Dec from phase center')
                self.RA=self.obs._MWA_Setting.ra_phase_center
                self.Dec=self.obs._MWA_Setting.dec_phase_center
            else:
                self.RA=self.obs.RA
                self.Dec=self.obs.Dec

	s+='//J2000 RA,DEC of pointing %f,%f\n' % (self.RA, self.Dec)
	s+='//The following HA/Dec are also in Epoch of Date\n'
	
        mwa=ephem_utils.Observatory('MWA','Murchison Widefield Array (32T)','116:40:14.93','-26:42:11.95',377.8,-8,-2,"W")
        observer=ephem.Observer()
	observer.pressure=0
	observer.long=(mwa.long/180.0)*math.pi
	observer.lat=(mwa.lat/180.0)*math.pi
	observer.elevation=mwa.elev
	observer.date=rtstime
	observer.epoch=ephem.J2000

        body=ephem.FixedBody()
        body._ra=(self.RA/180.0)*math.pi
        body._dec=(self.Dec/180.0)*math.pi
        body._epoch=ephem.J2000
        body.compute(observer)

        self.HA=ephem_utils.putrange((float(self.mwatime.LST)/15.0)-((body.ra/(2*math.pi))*24),24)
        
	s+='ObservationPointCentreHA=%s\n' % (self.HA)
	s+='ObservationPointCentreDec=%f\n' % ((body.dec/math.pi)*180.0)

	s+='ObservationLSTBase=%f\n' % ((float(self.mwatime.LST)/360.0) * 24.0)
	s+='ObservationTimeBase=%f\n' % (self.mwatime.MJD+2400000.5)
	s+='//Calibration and Imaging Options\n'
	s+='DoCalibration=1\n'
	s+='SourceCatalogueFile=\n'
	s+='NumberOfCalibrators=\n'
	s+='NumberOfSourcesToPeel=\n'

	return s


    ##################################################    
    def array_file(self):
        if self.obs is None:
            self.obs=get_observation_info.MWA_Observation(observation_number=self.gpstime, db=db)
        preamble="""##################################################
# this file is the instrument config file for the RTS and combines the information provided
# by the instr_config.txt and the antenna_locations.txt files. 
# It contains the antennas in order plus the position (ENH) followed by cable lengths 
# (corrected for electrical length)
# a flag and the gains for all 16 antenna associated with that tile i
# - as of 2012/11 these are all set to 1.0.
# 
"""
        s=preamble
        s+='# Written by %s\n' % (__file__.split('/')[-1])        
        s+='# for observation at %d\n' % (self.gpstime)
        now=datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        s+='# UTC (FILE CREATION) %s\n' % now
	s+='# LST (OBSERVATION (deg)) = %s\n' % (self.obs.LST)
	s+='# UTC (OBSERVATION) = %s\n' % (self.obs.UT)
	s+='# JD (OBSERVATION) = %f\n' % (self.mwatime.MJD+2400000.5)
        s+="""##################################################
# ID\tNAME\tE\tN\tH\tLENGTH\tFLAG\tDIPOLE\tGAINS[32]
"""

        for inputnumber in sorted(self.inputs.keys()):
            
            if (self.inputs[inputnumber].flag):
                f=1
            else:
                f=0
            length='%.2f' % self.inputs[inputnumber].length

            if self.inputs[inputnumber].electrical:
                length='EL_' + length

            t = [t for t in self.tiles if t.tile_id == self.inputs[inputnumber].tile].pop()

            north = t.tile_pos_north
            east = t.tile_pos_east
            height = t.tile_altitude

#	    east = dbobj.execute('select tile_pos_east from tile_info where tile_id = %s and begintime < %d and endtime > %d'
#                                     % (self.inputs[inputnumber].tile,self.gpstime,self.gpstime),db=self.db,debug=self.debug)[0][0]

#            east = [t.tile_pos_east for t in self.tiles if t.tile_id == self.inputs[inputnumber].tile].pop()

#	    north = dbobj.execute('select tile_pos_north from tile_info where tile_id = %s  and begintime < %d and endtime > %d'
#                                     % (self.inputs[inputnumber].tile,self.gpstime,self.gpstime),db=self.db,debug=self.debug)[0][0]

#            north = [t.tile_pos_north for t in self.tiles if t.tile_id == self.inputs[inputnumber].tile].pop()

#	    height = dbobj.execute('select tile_altitude from tile_info where tile_id = %s  and begintime < %d and endtime > %d'
#                                     % (self.inputs[inputnumber].tile, self.gpstime, self.gpstime),db=self.db,debug=self.debug)[0][0]

#            height = [t.tile_altitude for t in self.tiles if t.tile_id == self.inputs[inputnumber].tile].pop()

            s+="%d\tTile%03d %09.3f %09.3f %08.3f\t%s\t%d\n" % (inputnumber, self.inputs[inputnumber].tile,
                                         east, north, height, length, f)


        return s

    ##################################################
    def make_metafits(self):
        h=pyfits.PrimaryHDU()
        head=h.header
        head.update('GPSTIME',self.gpstime,'[s] GPS time of observation start')
        
        if self.duration>0:
            head.update('EXPOSURE',self.duration,'[s] duration of observation')

        if self.obs is None:
            self.obs=get_observation_info.MWA_Observation(observation_number=self.gpstime, db=db)
        head.update('FILENAME',self.obs.filename,'Name of observation')
        head.update('MJD',self.obs.MJD,'[days] MJD of observation')
        head.update('DATE-OBS','%04d-%02d-%02dT%02d:%02d:%02d' % (
            self.obs.year,
            self.obs.month,self.obs.day,
            self.obs.hour,self.obs.minute,self.obs.second),'[UT] Date and time of observation')
            

        if self.obs.LST is not None:
            head.update('LST',self.obs.LST,'[deg] LST')
        if self.obs.HA is not None:
            head.update('HA',ephem_utils.dec2sexstring(self.obs.HA,digits=0,roundseconds=1),
                        '[hours] hour angle')
        if (self.obs.azimuth is not None):
            head.update('AZIMUTH',self.obs.azimuth,'[deg] Azimuth of pointing center')
            head.update('ALTITUDE',self.obs.elevation,'[deg] Altitude of pointing center')
        if (self.obs.RA is not None):
            head.update('RA',self.obs.RA,'[deg] RA of pointing center')
            head.update('DEC',self.obs.Dec,'[deg] Dec of pointing center')
        if (self.obs._MWA_Setting.ra_phase_center is not None):
            head.update('RAPHASE',self.obs._MWA_Setting.ra_phase_center,
                        '[deg] RA of desired phase center')
            head.update('DECPHASE',self.obs._MWA_Setting.dec_phase_center,
                        '[deg] DEC of desired phase center')
        if self.obs._Schedule_Metadata is not None:
            head.update('SUN-DIST',self.obs._Schedule_Metadata.sun_pointing_distance,
                        '[deg] Distance from pointing center to Sun')
            head.update('MOONDIST',self.obs._Schedule_Metadata.moon_pointing_distance,
                        '[deg] Distance from pointing center to Moon')
            head.update('JUP-DIST',self.obs._Schedule_Metadata.jupiter_pointing_distance,
                        '[deg] Distance from pointing center to Jupiter')
            if len(self.obs._Schedule_Metadata.gridpoint_name)>0:
                head.update('GRIDNAME',self.obs._Schedule_Metadata.gridpoint_name,
                            'Pointing grid name')
                head.update('GRIDNUM',self.obs._Schedule_Metadata.gridpoint_number,
                            'Pointing grid number')
        if self.obs._MWA_Setting is not None:
            head.update('CREATOR',self.obs._MWA_Setting.creator,'Observation creator')
            head.update('PROJECT',self.obs._MWA_Setting.projectid,'Project ID')
            head.update('MODE',self.obs._MWA_Setting.mode,'Observation mode')
        if (len(self.obs.receivers)>0):
            head.update('RECVRS',','.join([str(x) for x in self.obs.receivers]),'Active receivers')
        if (len(self.obs.delays)>0):
            head.update('DELAYS',','.join([str(x) for x in self.obs.delays]),'Beamformer delays')
        if (self.obs.calibration is not None):
            if (self.obs.calibration):
                head.update('CALIBRAT',pyfits.TRUE,'Intended for calibration')
            else:
                head.update('CALIBRAT',pyfits.FALSE,'Intended for calibration')
        gains=None
        if self.obs.center_channel is not None:
            head.update('CENTCHAN',self.obs.center_channel,'Center coarse channel')

            # no longer get gains from this source
            # instead use tile-dependent values 
            #try:
            #    gains=splat_average.get_gains(self.obs.center_channel)
            #except:
            #    logger.warning('Unable to get coarse channel gains')


        head.update('CHANNELS',','.join([str(x) for x in self.obs.channels]),'Coarse channels')
        #if gains is not None:
        #    head.update('CHANGAIN',','.join([str(x) for x in gains]),'Coarse channel gains')

        head.update('SUN-ALT',self.obs.sun_elevation,'[deg] Altitude of Sun')
        
        head.update('FIBRFACT',self.fiber_velocity_factor,'Fiber velocity factor')
        head.update('TILEFLAG',','.join([str(x) for x in self.tiles_to_flag]),'Tiles flagged')
        nav_freq=int(self.corr2uvfitsheader.fine_channel/10)
        head.update('NAV_FREQ',nav_freq,'Assumed frequency averaging')
        head.update('FINECHAN',self.corr2uvfitsheader.fine_channel,'[kHz] Fine channel width')
        head.update('INTTIME',self.corr2uvfitsheader.inttime,'[s] Individual integration time')

        head.update('NSCANS',self.corr2uvfitsheader.n_scans,'Number of scans (time instants) in correlation products')
        head.update('NINPUTS',self.corr2uvfitsheader.n_inputs,'Number of inputs into the correlation products')
        head.update('NCHANS',self.corr2uvfitsheader.n_chans,'Number of fine channels in spectrum')
        head.update('BANDWDTH',self.corr2uvfitsheader.bandwidth,'[MHz] Total bandwidth')
        head.update("FREQCENT",channel2frequency(self.corr2uvfitsheader.channel)+(nav_freq-1)*0.005,
                    '[MHz] Center frequency of observation')
        head.update('TIMEOFF',self.corr2uvfitsheader.timeoffset,
                    '[s] Offset between observation starttime and start of correlations')
        head.update('DATESTRT',self.corr2uvfitsheader.mwatime.strftime('%Y-%m-%d')+'T'+
                    self.corr2uvfitsheader.mwatime.strftime('%H:%M:%S'),
                    '[UT] Date and time of correlations start')
        head.update('VERSION',_VERSION,'METAFITS version number')
        head.update('MWAVER',mwapy.__version__,'MWAPY version number')
        head.update('MWADATE',mwapy.__date__,'MWAPY version date')
        head.update('TELESCOP','MWA128T')

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

        y=sorted(self.tiles, key=lambda t: t.tile_id)
        y_id=numpy.array([t.tile_id for t in y])
        z_id=numpy.array([t.tile_id for t in self.tiles])
        for inputnumber in sorted(self.inputs.keys()):
            if (self.inputs[inputnumber].flag):
                f=1
            else:
                f=0
            i=numpy.where(y_id==self.inputs[inputnumber].tile)[0][0]
            j=numpy.where(z_id==self.inputs[inputnumber].tile)[0][0]
            length='%.2f' % self.inputs[inputnumber].length
            if self.inputs[inputnumber].electrical:
                length='EL_' + length
            Input.append(inputnumber)
            Antenna.append(i)
            Pol.append(self.inputs[inputnumber].pol.upper())
            Length.append(length)
            Flag.append(f)
            Rx.append(self.inputs[inputnumber].receiver)
            Slot.append(self.inputs[inputnumber].slot)
            Tile.append(self.inputs[inputnumber].tile)
            North.append(self.tiles[j].tile_pos_north)
            East.append(self.tiles[j].tile_pos_east)
            Height.append(self.tiles[j].tile_altitude)
            # select only the appropriate values for the channels used
            Gains.append(numpy.array(self.inputs[inputnumber].gains)[numpy.array(self.obs.channels)])

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
        tbhdu=pyfits.new_table([col1,col2,col3,col4,col5,col6,col7,col8,col9,col10,col11,col12])
        tbhdu.update_ext_name('TILEDATA',comment='Data about the tile/slot/Rx mapping')


        now=datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        head.update('DATE',now,'UT Date of file creation')
        #head.add_comment('Written by %s\n' % (__file__.split('/')[-1]))
        
        hdulist=pyfits.HDUList([h,tbhdu])
        


        return hdulist
                   
##################################################
class Corr2UVFITSHeader:
##################################################
    """ A class to write the header files for corr2uvfits

    Usage:
    
    gpstime=1001175315
    h=Corr2UVFITSHeader(gpstime, db=db)
    h.make_header()
    print h

    """

    ##################################################
    def __init__(self,gpstime=None,coarse_channels=24,
                 n_inputs=_NINP_128T,fine_channel=0,inttime=0,
                 timeoffset=0, lock=False, coarse_channel=None, db=None):
        """
        __init__(self,gpstime=None,coarse_channels=24,
                 n_inputs=_NINP_128T,fine_channel=10,inttime=1,
                 timeoffset=0, lock=False, coarse_channel=None, db=None):
        """

        self.db=db

        self.inttime=inttime
        self.coarse_channels=coarse_channels
        self.coarse_channel=coarse_channel
        # in kHz
        self.fine_channel=fine_channel
        self.n_inputs=n_inputs
        self.timeoffset=timeoffset

        self.corrtype='B'
        self.invert_freq=0
        self.conjugate=1

        # In degrees
        self.RA=None
        self.Dec=None
        self.header=None
        self.objectname=None
        self.obs=None
        self.n_scans=None
        self.bandwidth=None
        self.n_chans=None
        self.channel=None
        #self.year=None
        #self.month=None
        #self.day=None
        #self.hour=None
        #self.minute=None
        #self.second=None
        #self.MJD=None
        #self.UT=None
        self.lock=lock

        self.gpstime=gpstime


    ##################################################
    def __str__(self):
        return self.header

    ##################################################
    def __setattr__(self, name, value):
        self.__dict__[name]=value

        if (name == 'gpstime' and value is not None and value > 0):
            # if the gpstime is set, compute everything else
            self.obs=get_observation_info.MWA_Observation(observation_number=self.gpstime, db=db)
            if (self.obs.duration <= 0):
                logger.error('Did not identify observation for gpstime %d' % self.gpstime)
                return

            
    ##################################################
    def make_header(self):
        """
        make_header(self)
        """

        if (self.objectname is None):
            self.objectname=self.obs.filename

        if self.inttime==0:
            try:
                self.inttime=self.obs._MWA_Setting.int_time
            except:
                # determine integration time by date            
                self.inttime=_DT[max(numpy.where(self.gpstime>=numpy.array(_START))[0])]
                logger.info('Set integration time to %.1fs based on gpstime %d' % (
                    self.inttime,self.gpstime))
        if self.fine_channel==0:
            try:
                self.fine_channel=self.obs._MWA_Setting.freq_res
            except:
                # determine fine channel by date
                self.fine_channel=_DF[max(numpy.where(self.gpstime>=numpy.array(_START))[0])]
                logger.info('Set fine channel to %d kHz based on gpstime %d' % (
                    self.fine_channel,self.gpstime))
            
        # DLK
        # do not subtract self.timeoffset here since the number of recorded integrations
        # is independent of that
        # only adjust the starttime
        if self.n_scans is None:
            self.n_scans=int((self.obs.duration)/self.inttime)
        # in MHz
        self.bandwidth=self.coarse_channels * 1.28
        # fine channel is in kHz
        self.n_chans=int(self.bandwidth*1e3/(self.fine_channel))

        if (self.coarse_channels==24):
            self.channel=self.obs.center_channel
        else:
            if self.coarse_channels > 1:
                try:
                    self.channel=self.obs.channels[self.coarse_channels/2]
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
            if (self.obs._MWA_Setting.ra_phase_center is not None):
                logger.info('Setting RA,Dec from phase center')
                self.RA=self.obs._MWA_Setting.ra_phase_center
                self.Dec=self.obs._MWA_Setting.dec_phase_center
            else:
                self.RA=self.obs.RA
                self.Dec=self.obs.Dec

        self.mwatime=ephem_utils.MWATime(gpstime=self.gpstime+self.timeoffset)
        #[self.MJD,self.UT]=ephem_utils.calcUTGPSseconds(self.gpstime+self.timeoffset)
        #[self.year,self.month,self.day]=ephem_utils.mjd_cal(self.MJD)
        #self.hour,self.minute,self.second=ephem_utils.dec2sex(self.UT)
        #self.second=round(self.second)
        #self.time=self.mwatime.strftime('%H:%M:%S')
        #'%02d:%02d:%02d' % (self.hour,self.minute,self.second)
        #self.lst=ct2lst_mwa((self.year),(self.month),(self.day),self.time)
        self.HA=ephem_utils.putrange(float(self.mwatime.LST)/15.0-self.RA/15.0,24)

        if self.gpstime < _START_128T:
            # still 32T
            logger.info('Still 32T: using %d inputs' % (_NINP_32T))
            self.n_inputs=_NINP_32T
                
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

        header+="FIELDNAME %s\n" % self.objectname
        header+="N_SCANS   %-3d   # number of scans (time instants) in correlation products\n" % (self.n_scans)
        header+="N_INPUTS  %-3d   # number of inputs into the correlation products\n" % (self.n_inputs)
        header+="N_CHANS   %-3d   # number of channels in spectrum\n" % (self.n_chans)
        header+="CORRTYPE  %s     # correlation type to use. \'C\'(cross), \'B\'(both), or \'A\'(auto)\n" % (self.corrtype)
        header+="INT_TIME  %.1f   # integration time of scan in seconds\n" % (self.inttime)
        if self.channel is not None:
            nav_freq=int(self.fine_channel/10)
            # correct for averaging            
            header+="FREQCENT  %.3f # observing center freq in MHz\n" % (
                channel2frequency(self.channel)+(nav_freq-1)*0.005)
        else:
            logger.warning('No center channel specified; corr2uvfits will not be happy')
            
        header+="BANDWIDTH %.3f  # total bandwidth in MHz\n" % (self.bandwidth)
        header+="RA_HRS    %.6f   # the RA of the desired phase centre (hours)\n" % (self.RA/15.0)
        if self.lock:
           header+="HA_HRS    %.6f   # the HA at the *start* of the scan. (hours)\n" % (self.HA)

        header+="DEC_DEGS  %.4f   # the DEC of the desired phase centre (degs)\n" % (self.Dec)
        header+="DATE      %s  # YYYYMMDD\n" % (self.mwatime.strftime('%Y%m%d'))
        header+="TIME      %s      # HHMMSS\n" % (self.mwatime.strftime('%H%M%S'))
        header+="INVERT_FREQ %d # 1 if the freq decreases with channel number\n" % (self.invert_freq)
        # no longer necessary
        if self.mwatime.year<2012:
            header+="CONJUGATE %d # conjugate the raw data to fix sign convention problem if necessary\n" % (self.conjugate)
        
        self.header=header


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
######################################################################
def update_filename(filename, d):
    """
    filename=update_filename(filename, d)
    searches through filename for instances of %variable%
    replaces them by value where:
    d={'variable':value,
    'variable2':value2}

    """

    for k,v in d.items():
        filename=re.sub(r'%' + k + '%', str(v), filename)

    if re.search('%(\w+)%',filename) is not None:
        # still has some unresolved variables
        logger.warning('String \'%s\' has some unresolved variables after substitution' % filename)
        logger.warning('Available variables are: %s' % d)

    return filename
