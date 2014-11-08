
import logging, sys, os, glob, subprocess, string, re, urllib, math, time,shutil
from optparse import OptionParser
import numpy, ephem, pyfits

import ephem
from mwapy import ephem_utils, get_observation_info, make_metafiles, plot_lfile, splat_average, find_external
from mwapy.obssched.base import schedule
try:
    import pylab
    _useplotting=True
except ImportError:
    _useplotting=False    


# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('convert_ngas')
logger.setLevel(logging.WARNING)

# open up database connection
try:
    db = schedule.getdb()
except:
    logger.error("Unable to open connection to database")
    sys.exit(1)



######################################################################
# external routines
# the value after is 1 (if critical) or 0 (if optional)
external_paths=find_external.find_external({'build_lfiles': 1, 'corr2uvfits': 1})


######################################################################
class NGAS_Correlator():
    """
    C=NGAS_Correlator(gpstime=gpstime, channels=channels, filename=filename, db=db)
    print C
    C.plot_autos('test')

    """

    ##############################
    def __init__(self, gpstime=None, db=None, fine_channel=10, inputs=64, channelsperfile=1536,
                 filenames=None, center_channel=None, flag=True, flagfile=None, lock=False,
                 adjust_gains=True,
                 headername='header.txt', instrname='instr_config.txt', antennaname='antenna_locations.txt',
                 timeoffset=0, maxtimediff=10, command=None):
    

        self.dict={}
        
        self.fine_channel=fine_channel
        self.inputs=inputs
        self.integrationtime=1
        self.nav_time=1
        self.nav_freq=1
        self.duration=None

        self.channelsperfile=channelsperfile
        self.coarse_channels=None
        # this is the number of DASs or GPU boxes or whatever
        self.ndas=None
        self.ntimefiles=None

        self.filenames=filenames
        self.observation_number=None
        self.center_channel=center_channel
        self.observation=None
        self.instrument_configuration=None
        self.Corr2UVFITSHeader=None
        self.flag=flag
        self.flagfile=flagfile
        self.lock=lock
        self.adjust_gains=adjust_gains

        self.writeheader=True
        self.headername=headername
        self.writeinstr=True
        self.instrname=instrname
        self.writeantenna=True
        self.antennaname=antennaname
        self.timeoffset=timeoffset
        self.quack=0
        
        self.maxtimediff=maxtimediff

        self.build_lfiles=external_paths['build_lfiles']
        self.corr2uvfits=external_paths['corr2uvfits']

        self.acname=None
        self.ccname=None
        
        self.tempacname=None
        self.tempccname=None

        self.command=command

        self.db=db
        self.gpstime=gpstime


    ##############################
    def __del__(self):
        if self.tempacname is not None:
            try:
                os.remove(self.tempacname)
            except:
                logger.warning('Unable to remove temporary AC file %s' % self.tempacname)
        if self.tempccname is not None:
            try:
                os.remove(self.tempccname)
            except:
                logger.warning('Unable to remove temporary AC file %s' % self.tempccname)

    ##############################
    def find_closest_observation(self):
        """
        find_closest_observation(self)
        """
        if self.gpstime is None:
            logger.error('Must supply gpstime to search')
            return None
        if self.db is None:
            logger.error('Cannot retrieve flagging information without database connection')
            return None
        observation_number=get_observation_info.find_closest_observation((self.gpstime),maxdiff=self.maxtimediff,
                                                                         db=self.db)
        if observation_number is None:
            logger.error('Did not identify observation for gpstime %d after searching %d s' % (self.gpstime, self.maxtimediff))
            return None
        else:
            logger.info('Found it at %d' % observation_number)
        self.observation_number=observation_number

    ##################################################
    def __str__(self):
        return str(self.observation)
            
    ##################################################
    def __setattr__(self, name, value):
        self.__dict__[name]=value

        if (name == 'filenames' and value is not None and len(value) > 0):
            self.ntimefiles=len(value)
            self.ndas=len(value[0])
            for filenames in value:
                for filename in filenames:
                    if not os.path.exists(filename):
                        logger.error('File %s does not exist' % filename)
                        self.filenames=None
                        return None
            self.coarse_channels=12*self.ndas
            logger.info('Have %d x %d input files' % (self.ndas,
                                                      self.ntimefiles))


        elif (name == 'gpstime' and value is not None and value > 0):
            # if the gpstime is set, compute everything else
            self.observation=get_observation_info.MWA_Observation(observation_number=self.gpstime, db=self.db)
            if (self.observation.duration <= 0):
                logger.warning('Did not identify observation for gpstime %d' % self.gpstime)
                self.find_closest_observation()
                if (self.observation_number is None):
                    self.observation=None
                    return None
                self.observation=get_observation_info.MWA_Observation(observation_number=self.observation_number, db=self.db)
            else:
                self.observation_number=self.observation.observation_number
            self.center_channel=self.observation.center_channel
            self.duration=self.observation.duration

        elif (name == 'observation_number' and value is not None and value > 0):
            self.get_metadata()

    ##############################
    def get_metadata(self):
        if self.db is None:
            logger.error('Cannot retrieve flagging information without database connection')
            return None
        
        if self.observation_number is None:
            logger.error('Must supply observation_number')
            return None
        
        self.instrument_configuration=make_metafiles.instrument_configuration(gpstime=self.observation_number,
                                                                              db=self.db)
        self.instrument_configuration.make_instr_config()
        self.Corr2UVFITSHeader=make_metafiles.Corr2UVFITSHeader(self.observation_number,
                                                                coarse_channels=self.coarse_channels,
                                                                timeoffset=0,
                                                                inttime=1,
                                                                fine_channel=self.fine_channel,
                                                                lock=self.lock,
                                                                db=self.db)
        self.Corr2UVFITSHeader.make_header()
        
        self.dict={'gpstime': self.gpstime,
                   'obsnum': self.observation_number,
                   'obsservation_number': self.observation_number,
                   'target': self.observation.filename,
                   'channel': self.center_channel}

    ##############################
    def make_lfile(self, root, nav_time=1, nav_freq=1, subbands=1, quack=0, timetoskip=0, maxtime=None):
        """
        outname_ac,outname_cc=make_lfile(self, root, nav_time=1, nav_freq=1, subbands=1, quack=0, timetoskip=0, maxtime=None)
        """
        temproot='_test'

        if self.filenames is None or len(self.filenames)==0:
            logger.error('Cannot create lfiles without an input file')
            return None
        if self.center_channel is not None:
            correct_chan=splat_average.channel_order(self.center_channel)
        else:
            logger.error('Cannot create lfiles without knowing the center channel')
            return None
        if self.adjust_gains:
            gains=splat_average.get_gains(self.center_channel)
            logger.info('Adjusting coarse PFB gains by a factor of 1.0/%s' % (gains))
        else:
            gains=None
        if isinstance(self.filenames,str):
            # just a single file, defined by a string
            
            # convert to a temporary L file set
            command=self.build_lfiles + ' -m 1 -v %s -f %d -o %s -i %d -s %d' % (self.filenames,
                                                                                 self.channelsperfile,
                                                                                 temproot,
                                                                                 self.inputs,
                                                                                 timetoskip)
            if maxtime is not None and maxtime>0:
                command+=' -n %d' % maxtime
            result=runit(command,
                         verbose=logger.getEffectiveLevel()<logging.WARNING)
            if (hasstring(result[1],'ERROR')):
                logger.error('Error running build_lfiles:\n\t%s',
                             ''.join(result[1]))
                return None
            if not os.path.exists(temproot + '.LACSPC'):
                logger.error('Expected output file %s does not exist' % (
                    temproot + '.LACSPC'))
                return None
        else:
            for j in xrange(len(self.filenames)):
                # convert to a temporary L file set
                command=self.build_lfiles + ' -m 1 -v %s -f %d -o %s -i %d -s %d' % (' -v '.join(self.filenames[j]),
                                                                                     self.channelsperfile*self.ndas,
                                                                                     temproot,
                                                                                     self.inputs,
                                                                                     timetoskip)
                if maxtime is not None and maxtime>0:
                    command+=' -n %d' % maxtime
                if j > 0:
                    command+=' -a'
                result=runit(command,
                             verbose=logger.getEffectiveLevel()<logging.WARNING)
                if (hasstring(result[1],'ERROR')):
                    logger.error('Error running build_lfiles:\n\t%s',
                                 ''.join(result[1]))
                    return None
                if not os.path.exists(temproot + '.LACSPC'):
                    logger.error('Expected output file %s does not exist' % (
                        temproot + '.LACSPC'))
                    logger.error(result[0])
                    logger.error(result[1])
                    return None

            # after this there is only a single file
            self.channelsperfile=self.channelsperfile*self.ndas
            self.ndas=1
        fnames_ac,fnames_cc,n_times=splat_average.get_filenames_integrations(temproot,
                                                                             self.ndas,
                                                                             self.channelsperfile,
                                                                             self.inputs)
        self.duration=n_times
        if n_times <=0:
            logger.error('Determined integration time of 0 for %s' % (fnames_ac[0]))
            return None
        logger.info('Processing %d integrations' % (n_times))
        if '%' in root:
            root=update_filename(root,self.dict)
        if subbands==1:
            outname_ac=root + '.lacspc'
            outname_cc=root + '.lccspc'

            if nav_time>1:
                logger.info('Averaging output by factor of %d in time' % nav_time)
            if nav_freq>1:
                logger.info('Averaging output by factor of %d in frequency' % nav_freq)
        else:
            logger.info('Will write %d separate sub-bands' % subbands)
            outname_ac=[]
            outname_cc=[]
            for i in xrange(subbands):
                outname_ac.append(root + '_band%02d.lacspc' % (i+1))
                outname_cc.append(root + '_band%02d.lccspc' % (i+1))
                if nav_time>1:
                    logger.info('Averaging output by factor of %d in time' % nav_time)
                if nav_freq>1:
                    logger.info('Averaging output by factor of %d in frequency' % nav_freq)

        if quack > 0:
            if int(quack) % int(nav_time) > 0:
                # not an integer multiple
                logger.warning('Requested quacking time of %d is not a multiple of requested time averaging %d; increasing quacking to %d...' % (
                    quack,nav_time,((int(quack)/int(nav_time))+1)*int(nav_time)))
                quack=((int(quack)/int(nav_time))+1)*int(nav_time)

            logger.info('Will quack first %d time samples' % quack)
        self.quack=quack
        
        logger.info('SPLAT and averaging AC...')
        retval=splat_average.splat_average_ac(fnames_ac, outname_ac, n_times, 
                                              self.channelsperfile*self.ndas, self.inputs, 
                                              nav_time, nav_freq, correct_chan, quack=quack, gains=gains)
        if isinstance(outname_ac,str):
            if retval is None or not os.path.exists(outname_ac):
                logger.error('Error writing splatted AC file')
                return None
        else:
            for ac in outname_ac:
                if retval is None or not os.path.exists(ac):
                    logger.error('Error writing splatted AC file')
                    return None

        logger.info('SPLAT and averaging CC...')
        retval=splat_average.splat_average_cc(fnames_cc, outname_cc, n_times, 
                                              self.channelsperfile*self.ndas, self.inputs, 
                                              nav_time, nav_freq, correct_chan, quack=quack, gains=gains)
        if isinstance(outname_cc,str):
            if retval is None or not os.path.exists(outname_cc):
                logger.error('Error writing splatted CC file')
                return None
        else:
            for cc in outname_cc:
                if retval is None or not os.path.exists(cc):
                    logger.error('Error writing splatted CC file')
                    return None


        for ac,cc in zip(fnames_ac,fnames_cc):
            os.remove(ac)
            os.remove(cc)

        self.acname,self.ccname=outname_ac,outname_cc
        self.nav_time=nav_time
        self.nav_freq=nav_freq
        return outname_ac,outname_cc

    ##############################
    def make_uvfits(self,output='',update=True):
        """
        uvfitsname=makee_uvfits(self,output='',update=True)
        """

        if self.Corr2UVFITSHeader is None:
            self.writeheader=False
        if str(self)=='None':
            self.writeinstr,self.writeantenna=None,None

        if (not self.writeheader and not os.path.exists(self.headername)):
            logger.error('Existing header file %s does not exist' % self.headername)
            return        

        if (self.writeinstr and str(self)=='None'):
            logger.error('No instr_config file available')
            return
        if (not self.writeinstr and not os.path.exists(self.instrname)):
            logger.error('Existing instr_config file %s does not exist' % self.instrname)
            return

        if (self.writeantenna and str(self)=='None'):
            logger.error('No antenna_locations file available')
            return
        if (not self.writeantenna and not os.path.exists(self.antennaname)):
            logger.error('Existing antenna_locations file %s does not exist' % self.antennaname)
            return

        if not self.writeheader:
            # it is a pre-existing file
            logger.info('Using existing header file %s' % self.headername)
        else:
            
            self.Corr2UVFITSHeader=make_metafiles.Corr2UVFITSHeader(self.observation_number,
                                                                    coarse_channels=self.coarse_channels,
                                                                    timeoffset=self.timeoffset,
                                                                    inttime=1*self.nav_time,
                                                                    fine_channel=self.fine_channel*self.nav_freq,
                                                                    lock=self.lock,
                                                                    db=self.db)
            self.Corr2UVFITSHeader.obs.duration=self.duration
            self.Corr2UVFITSHeader.make_header()


            # need to write it out
            if '%' in self.headername:
                self.headername=update_filename(self.headername,self.dict)
            f=open(self.headername,'w')
            f.write(self.Corr2UVFITSHeader.header)
            f.close()
            logger.info('Wrote header to %s' % self.headername)

        if not self.writeinstr:
            # it is a pre-existing file
            logger.info('Using existing instr_config file %s' % self.instrname)
        else:
            # need to write it out
            if '%' in self.instrname:
                self.instrname=update_filename(self.instrname,self.dict)
            f=open(self.instrname,'w')
            f.write(self.instrument_configuration.instr_config())
            f.close()
            logger.info('Wrote instr_config to %s' % self.instrname)

        if not self.writeantenna:
            # it is a pre-existing file
            logger.info('Using existing antenna_locations file %s' % self.antennaname)
        else:
            # need to write it out
            if '%' in self.antennaname:
                self.antennaname=update_filename(self.antennaname,self.dict)
            f=open(self.antennaname,'w')
            f.write(self.instrument_configuration.antenna_locations())
            f.close()
            logger.info('Wrote antenna_locations to %s' % self.antennaname)

        if output is None or len(output)==0:
            logger.error('Must specify output file name')
            return

        if '%' in output:
            output=update_filename(output,self.dict)
        uvfitsname,ext=os.path.splitext(output)
        if not ext.upper() in ['FITS','UVFITS']:
            uvfitsname+='.uvfits'

        command=self.corr2uvfits + ' -c %s -a %s' % (self.ccname,self.acname)
            
        if (not os.path.exists(self.ccname)):
            logger.error('Cross correlation file %s does not exist',self.ccname)
            return None
        if (not os.path.exists(self.acname)):
            logger.error('Auto correlation file %s does not exist',self.acname)
            return None
        command+=' -o %s' % (uvfitsname)
        if (self.flag):
            command+=' -f'
            if (self.nav_freq == 1):
                # 10 kHz channels
                command+=' 3'
            elif (self.nav_freq == 4):
                # 40 kHz channels
                command+=' 2'
            else:
                command+=' 1'
        if (self.flagfile is not None and len(self.flagfile)>0):
            if not os.path.exists(self.flagfile):
                logger.error('corr2uvfits global flag file %s does not exist',self.flagfile)
                return None
            else:
                command+=' -F %s' % self.flagfile
        command+=' -S %s' % self.antennaname
        command+=' -I %s' % self.instrname
        command+=' -H %s' % self.headername
        if self.lock:
            command+=' -l'
        if (os.path.exists(uvfitsname)):
            os.remove(uvfitsname)
        result=runit(command)
        if (hasstring(result[1],'ERROR')):
            logger.error('Error running corr2uvfits:\n\t%s',''.join(result[1]))
            return None

        try:
            f=pyfits.open(uvfitsname,'update')
        except IOError,err:
            logger.error('Cannot open UVFits file %s\n%s', uvfitsname,err)
            return None
        f.verify('fix')

        # this is the order of the keywords to update
        keywords=['N_INPUTS','NAV_TIME','NAV_FREQ','QUACK','TIMEOFF','OBSNUM','CALIBRTR','RECEIVRS',
                  'DELAYS','SUNALT','ALTITUDE','AZIMUTH','N_CHANS','BANDWDTH','INV_FREQ','CONJGATE',
                  'INTTIME','EXPTIME','HA_HRS','LST_HRS','OBSNDATE','INSTCONF','ANTENNAS','FREQCENT']
        for i in xrange(len(self.filenames)):
            for j in xrange(self.ndas):
                keywords.append('NGAS%02d%02d' % (j+1,i))
        keywords+=['CCNAME','ACNAME','CORRTYPE','FLAGCORR','FLAGFILE']
        
        itemstoupdate={'N_INPUTS': [self.inputs,'Number of inputs'],
                       'NAV_TIME': [self.nav_time,'Time averaging factor'],
                       'NAV_FREQ': [self.nav_freq,'Frequency averaging factor'],
                       'QUACK': [self.quack,'Number of initial time samples quacked (flagged)'],
                       'TIMEOFF': [self.timeoffset,'[s] Assumed time offset between OBSNUM and start of data']
                       }
        
        if self.observation_number is not None:
            itemstoupdate['OBSNUM']=[self.observation_number,'Observation number']
        if self.observation is not None:
            itemstoupdate['CALIBRTR']=[ternary(self.observation.calibration,pyfits.TRUE,pyfits.FALSE),
                                       'Is the observation of a calibrator target?']
            itemstoupdate['RECEIVRS']=[str(self.observation.receivers),'Active receivers']
            itemstoupdate['DELAYS']=[str(self.observation.delays),'Beamformer delays']
            itemstoupdate['SUNALT']=[self.observation.sun_elevation,'[deg] Sun altitude']
            itemstoupdate['ALTITUDE']=[self.observation.elevation,'[deg] Pointing altitude']
            itemstoupdate['AZIMUTH']=[self.observation.azimuth,'[deg] Pointing azimuth']
        if self.Corr2UVFITSHeader is not None:
            itemstoupdate['N_CHANS']=[self.Corr2UVFITSHeader.n_chans,'Number of fine channels']
            itemstoupdate['BANDWDTH']=[self.Corr2UVFITSHeader.bandwidth,'[MHz] Total bandwidth']
            itemstoupdate['INV_FREQ']=[ternary(self.Corr2UVFITSHeader.invert_freq,pyfits.TRUE,pyfits.FALSE),
                                       'Invert frequencies?']
            itemstoupdate['CONJGATE']=[ternary(self.Corr2UVFITSHeader.conjugate,pyfits.TRUE,pyfits.FALSE),
                                       'Conjugate inputs?']
            itemstoupdate['INTTIME']=[self.Corr2UVFITSHeader.inttime,'[s] Time of each integrations']
            itemstoupdate['EXPTIME']=[self.Corr2UVFITSHeader.inttime*self.Corr2UVFITSHeader.n_scans,
                                      '[s] Total time of observation']
            itemstoupdate['HA_HRS']=[self.Corr2UVFITSHeader.HA,'[hrs] Hour Angle']
            itemstoupdate['LST_HRS']=[float(self.Corr2UVFITSHeader.mwatime.LST)/15.0,'[hrs] Local sidereal time']
            itemstoupdate['OBSNDATE']=[self.Corr2UVFITSHeader.mwatime.strftime('%Y-%m-%dT%H:%M:%S'),'Date of observation']
            
            itemstoupdate['INSTCONF']=[self.instrname,'Instrument configuration file']
            itemstoupdate['ANTENNAS']=[self.antennaname,'Antenna locations file']
            itemstoupdate['FREQCENT']=[make_metafiles.channel2frequency(int(self.center_channel)),
                                       '[MHz] Center frequency for full band']
            for i in xrange(len(self.filenames)):
                for j in xrange(self.ndas):
                    itemstoupdate['NGAS%02d%02d' % (j+1,i)]=[self.filenames[i][j], 'Name of NGAS file for DAS %d and time %d' % (j+1,i)]
            if (self.ccname):
                itemstoupdate['CCNAME']=[self.ccname,'Name of CC file']
            if (self.acname):
                itemstoupdate['ACNAME']=[self.acname,'Name of AC file']
            itemstoupdate['CORRTYPE']=['B','Correlation type. C(ross), B(oth), or A(uto)']
            itemstoupdate['FLAGCORR']=[ternary(self.flag,pyfits.TRUE,pyfits.FALSE),
                                       'Flagging done during conversion to UVFITS?']
            if (self.flagfile is not None):
                itemstoupdate['FLAGFILE']=[self.flagfile,
                                           'Global flagging file']
            else:
                itemstoupdate['FLAGFILE']=['NONE',
                                           'Global flagging file']

        if update:
            try:
                h=f[0].header
            except:
                logger.error('Error reading FITS header for %s' % uvfitsname)
                return None

            areerrors=False
            try:
                if (self.command is not None):
                    h.add_history('Command was:')
                    h.add_history(self.command)
            except:
                logger.error('Error updating FITS history for %s:\n%s',
                             uvfitsname,sys.exc_info()[1])
                areerrors=True

            for k in keywords:
                if itemstoupdate.has_key(k):
                    try:
                        h.update(k,itemstoupdate[k][0],itemstoupdate[k][1])
                    except:
                        logger.error('Error updating FITS header for %s[%s]:\n%s',
                                     uvfitsname,k,sys.exc_info()[1])
                        areerrors=True

            try:
                f.flush(output_verify='fix')
                if areerrors:
                    logger.warning('Error(s) during updating FITS header but updated file anyway')
            except:
                logger.error('Error updating FITS file %s:\n%s',
                             uvfitsname,sys.exc_info()[1])
                return None

            # need this for some reason to update the header cards
            # they were made lowercase, which miriad cannot read
            # I tried to fix this purely in pyfits
            # but that screwed up the ordering
            try:
                f3=open(uvfitsname,'r+')
                n=0
                while n < 36*4:
                    s=f3.read(80)
                    n+=1
                    if s.startswith('END'):
                        break
                    if ('PTYPE' in s):
                        s=s.upper()
                        f3.seek(-80,os.SEEK_CUR)
                        f3.write(s)
                f3.flush()
            except:
                pass        

        return uvfitsname


    ##############################
    def plot_autos(self, root, timetoskip=4, timetoaverage=8, format='png'):
        """
        outputfiles=plot_autos(self, root, timetoskip=4, timetoaverage=8, format='png')
        """

        if self.tempacname is None or self.tempccname is None:
            try:
                outname_ac,outname_cc=self.make_lfile('_test2', timetoskip=timetoskip, maxtime=timetoaverage)
            except:
                logger.error('Error converting to L files')
                return None
            if outname_ac is None or outname_cc is None:
                logger.error('Error converting to L files')
                return None
            self.tempacname,self.tempccname=outname_ac,outname_cc
        else:
            outname_ac,outname_cc=self.tempacname,self.tempccname

        if '%' in root:
            root=update_filename(root,self.dict)


        acdata=plot_lfile.load_acdata(outname_ac, ninputs=self.inputs, nchannels=self.channelsperfile*self.ndas)
        xxdata=acdata[:,::2,:]
        yydata=acdata[:,1::2,:]
        # mask out values that are 0, but are not masked otherwise
        ntimes=xxdata.shape[0]
        nchan=xxdata.shape[2]
        nants=xxdata.shape[1]
        logger.info('Read AC data with ntimes=%d, nchan=%d, nants=%d' % (ntimes,nchan,nants))

        # turn off tex for the text
        pylab.rc('text',usetex=False)        
        fig=pylab.figure()
        chans=(make_metafiles.channel2frequency(self.center_channel)-12.5*1.28)+10e-3*numpy.arange(nchan) 

        coarsechans=self.center_channel+numpy.arange(-12.0,12.0,1.0/128)

        if isinstance(self.filenames,str):
            titleroot=self.filenames
        else:
            titleroot=self.filenames[0][0]
        if (self.observation_number is not None):
            titleroot+='(%d)' % self.observation_number

        if self.instrument_configuration is not None:
            y=sorted(self.instrument_configuration.tiles, key=lambda t: t.tile_id)
            y_id=numpy.array([t.tile_id for t in y])

        outputfiles=[]
        #for antenna in xrange(nants):
        for antenna in xrange(nants):
            title='%s\nInput=%d,%d' % (titleroot,2*antenna,2*antenna+1)
            if self.instrument_configuration is not None:
                title+='\n'
                ix=numpy.where(y_id==self.instrument_configuration.inputs[2*antenna].tile)[0][0]
                iy=numpy.where(y_id==self.instrument_configuration.inputs[2*antenna+1].tile)[0][0]
                title+= '(Ant %d Rx %d Slot %d Tile %d%s,Ant %d Rx %d Slot %d Tile %d%s)' % (
                    ix,self.instrument_configuration.inputs[2*antenna].receiver,
                    self.instrument_configuration.inputs[2*antenna].slot,
                    self.instrument_configuration.inputs[2*antenna].tile,
                    self.instrument_configuration.inputs[2*antenna].pol.upper(),
                    iy,self.instrument_configuration.inputs[2*antenna+1].receiver,
                    self.instrument_configuration.inputs[2*antenna].slot,
                    self.instrument_configuration.inputs[2*antenna+1].tile,
                    self.instrument_configuration.inputs[2*antenna+1].pol.upper())
                
            fig.clf()
            ax1=fig.add_subplot(1,1,1)
            zx=xxdata[:,antenna,:].mean(axis=0)
            zy=yydata[:,antenna,:].mean(axis=0)
            ax1.plot(chans,zx,'b',chans,zy,'r')
            ax1.legend(['XX','YY'])

            ax2=ax1.twiny()
            ax2.plot(coarsechans,zx,'b',coarsechans,zy,'r')
            
            xlim=numpy.array(ax1.get_xlim())
            ylim=numpy.array(ax1.get_ylim())

            ax2.set_xlim((xlim-chans[0])/1.28+self.center_channel-12)
            for c in self.center_channel+numpy.arange(-12,13):
                ax2.plot([c,c],ylim,'k:')

            ax1.set_xlabel('Fine Channel Frequency (MHz)')      
            ax2.set_xlabel('Coarse Channel Number')
            ax2.set_xticks(self.center_channel+numpy.arange(-12,13,2))

            #ax1.xaxis.set_ticklabels('')            
            ax1.text(xlim[0]+0.025*(xlim[1]-xlim[0]),ylim[1]-0.10*(ylim[1]-ylim[0]),title, size='small')
            fname='%s_%03d.%s' % (root,antenna,format)
            logger.info('# Saving auto to %s' % (fname))
            try:
                pylab.savefig(fname)
                outputfiles.append(fname)
            except RuntimeError,err:
                logger.error('Error saving figure: %s',err)                
            
        return outputfiles

    ##############################
    def plot_crosses(self, root, timetoskip=4, timetoaverage=8, format='png'):
        """
        outputfiles=plot_crosses(self, root, timetoskip=4, timetoaverage=8, format='png')
        """
        if self.tempacname is None or self.tempccname is None:
            try:
                outname_ac,outname_cc=self.make_lfile('_test2', timetoskip=timetoskip, maxtime=timetoaverage)
            except:
                logger.error('Error converting to L files')
                return None
            if outname_ac is None or outname_cc is None:
                logger.error('Error converting to L files')
                return None
            self.tempacname,self.tempccname=outname_ac,outname_cc
        else:
            outname_ac,outname_cc=self.tempacname,self.tempccname

        if '%' in root:
            root=update_filename(root,self.dict)


        ccdata=plot_lfile.load_ccdata(outname_cc, ninputs=self.inputs, nchannels=self.channelsperfile*self.ndas)
        real_data=ccdata[:,:,::2]
        imag_data=ccdata[:,:,1::2]
        
        ampl=numpy.sqrt(real_data.mean(axis=0)**2+imag_data.mean(axis=0)**2)
        phase=numpy.arctan2(imag_data.mean(axis=0),real_data.mean(axis=0))*180/math.pi
        ntimes=real_data.shape[0]
        nchan=real_data.shape[2]
        nants=(math.sqrt(1+8*ccdata.shape[1])/2+0.5)/2
        logger.info('Read CC data with ntimes=%d, nchan=%d, nants=%d' % (ntimes,nchan,nants))
    
    
        # turn off tex for the text
        pylab.rc('text',usetex=False)        
        fig=pylab.figure()
        chans=(make_metafiles.channel2frequency(self.center_channel)-12.5*1.28)+10e-3*numpy.arange(nchan) 

        coarsechans=self.center_channel+numpy.arange(-12.0,12.0,1.0/128)

        if isinstance(self.filenames,str):
            titleroot=self.filenames
        else:
            titleroot=self.filenames[0][0]
        if (self.observation_number is not None):
            titleroot+='(%d)' % self.observation_number

        if self.instrument_configuration is not None:
            y=sorted(self.instrument_configuration.tiles, key=lambda t: t.tile_id)
            y_id=numpy.array([t.tile_id for t in y])

        outputfiles=[]
        for input1 in xrange(0,int(2*nants),2):
            for input2 in xrange(input1+2,int(2*nants),2):
                index_xx=-0.5*(input1)**2 + (2*nants-1.5)*input1-1+input2
                index_xy=-0.5*(input1)**2 + (2*nants-1.5)*input1-1+input2+1
                index_yx=-0.5*(input1+1)**2 + (2*nants-1.5)*(input1+1)-1+input2
                index_yy=-0.5*(input1+1)**2 + (2*nants-1.5)*(input1+1)-1+input2+1
                title='%s\nInput=%dx%d, %dx%d, %dx%d, %dx%d' % (titleroot,input1,input2,input1,input2+1,
                                                                input1+1,input2,input1+1,input2+1)

                if self.instrument_configuration is not None:
                    title+='\n'
                    i1=numpy.where(y_id==self.instrument_configuration.inputs[input1].tile)[0][0]
                    i2=numpy.where(y_id==self.instrument_configuration.inputs[input2].tile)[0][0]
                    title+= '(Ant %d Rx %d Slot %d Tile %d,Ant %d Rx %d Slot %d Tile %d)' % (
                    i1,self.instrument_configuration.inputs[input1].receiver,
                    self.instrument_configuration.inputs[input1].slot,
                    self.instrument_configuration.inputs[input1].tile,
                    i2,self.instrument_configuration.inputs[input2].receiver,
                    self.instrument_configuration.inputs[input2].slot,
                    self.instrument_configuration.inputs[input2].tile)
                
                fig.clf()
                fig.subplots_adjust(hspace=-0.0)
                ax_phase=fig.add_subplot(2,1,1)
                ax_phase.xaxis.set_label_position('top')
                ax_phase.xaxis.set_ticks_position('top')
                ax_ampl=fig.add_subplot(2,1,2)
                zampl_xx=ampl[index_xx,:]
                zphase_xx=phase[index_xx,:]
                zampl_xy=ampl[index_xy,:]
                zphase_xy=phase[index_xy,:]
                zampl_yx=ampl[index_yx,:]
                zphase_yx=phase[index_yx,:]
                zampl_yy=ampl[index_yy,:]
                zphase_yy=phase[index_yy,:]

                ax_ampl.plot(chans,zampl_xx,'b',chans,zampl_xy,'r',chans,zampl_yx,'g',chans,zampl_yy,'k')
                
                ax_phase.plot(coarsechans,zphase_xx,'b',coarsechans,zphase_xy,'r',coarsechans,zphase_yx,'g',coarsechans,zphase_yy,'k')
                ax_phase.set_ylim((-180,180))
                ax_phase.legend(['XX','XY','YX','YY'])
                
                xlim_ampl=numpy.array(ax_ampl.get_xlim())
                ylim_phase=numpy.array(ax_phase.get_ylim())
                ylim_ampl=numpy.array(ax_ampl.get_ylim())

                ax_phase.set_xlim((xlim_ampl-chans[0])/1.28+self.center_channel-12)
                xlim_phase=numpy.array(ax_phase.get_xlim())

                for c in self.center_channel+numpy.arange(-12,13):
                    ax_phase.plot([c,c],ylim_phase,'k:')
                    ax_ampl.plot([c*1.28,c*1.28],ylim_ampl,'k:')
                ax_ampl.set_xlim(xlim_ampl)
                ax_phase.set_xlim(xlim_phase)
                                    
                ax_ampl.set_xlabel('Fine Channel Frequency (MHz)')      
                
                ax_phase.set_xlabel('Coarse Channel Number')
                ax_phase.set_xticks(self.center_channel+numpy.arange(-12,13,2))
                ax_phase.set_ylabel('Phase (deg)')
                ax_ampl.set_ylabel('Amplitude')

                ax_ampl.text(xlim_ampl[0]+0.025*(xlim_ampl[1]-xlim_ampl[0]),
                              ylim_ampl[1]-0.20*(ylim_ampl[1]-ylim_ampl[0]),title, size='small')
                fname='%s_%03d_%03d.%s' % (root,input1/2,input2/2,format)
                logger.info('# Saving cross to %s' % (fname))
                try:
                    pylab.savefig(fname)
                    outputfiles.append(fname)
                except RuntimeError,err:
                    logger.error('Error saving figure: %s',err)                

        return outputfiles



    
######################################################################
def runit(command,stdin=None,fake=0,verbose=1, **kwargs):
    """
    stdout,stderr=runit(command,stdin=None,fake=0,verbose=1)
    wraps os.system() to log results (using logger())
    or will just print statements (if fake==1)
    if (not verbose), will not print
    returns results of stdout and stderr
    """

    try:
        logger.debug(command)
    except NameError:
        pass
    if (verbose):
        print command
    if (not fake):
        try:
            if (stdin is None):
                p=subprocess.Popen(command,shell=True,stderr=subprocess.PIPE,
                                   stdout=subprocess.PIPE, close_fds=True, **kwargs)
                (result,result_error)=p.communicate()
            else:                
                p=subprocess.Popen(command,shell=True,stdin=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   stdout=subprocess.PIPE, close_fds=True, **kwargs)
                (result,result_error)=p.communicate(stdin)
        except:            
            logger.error('Error running command:\n\t%s\n%s', command,sys.exc_info()[1])
            return None
        # go from a single string to a list of strings (one per line)
        if (result is not None):
            result=result.split('\n')
        if (result_error is not None):
            result_error=result_error.split('\n')
        return result,result_error
    return None

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
######################################################################
def hasstring(S,s):
    """
    result=hasstring(S,s)
    returns True if string s is in any element of list S
    """
    try:
        return any([s in S[i] for i in xrange(len(S))])
    except NameError:
        # put this in for python 2.4 which does not have any()
        return sum([s in S[i] for i in xrange(len(S))])>=1

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
def parseNGASfile(filename, separator='_'):
    '''
    Parse out obs id, time, host and part from an MWA correlator file
    Fileid format:
    <id>_<time>_<host>_<partnumber>.<ext>
    Note:
    <time> is %Y%m%d%H%M%S
    if <partnumber> is missing, will return 0 as int
    (otherwise will return string)
    '''
    path,filename=os.path.split(filename)
    name,ext=os.path.splitext(filename)
    if name.count(separator)==3:
        obsid,datetimestring,host,partnumber=name.split(separator)
    elif name.count(separator)==2:
        obsid,datetimestring,host=name.split(separator)
        partnumber=0
    else:
        logger.error('Do not know how to parse NGAS file %s' % filename)
        return None
    
    return obsid, datetimestring, host, partnumber

