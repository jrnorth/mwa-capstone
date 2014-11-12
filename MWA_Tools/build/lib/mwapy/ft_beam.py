#from mwapy import ft_beam

# Generate automatic calibration model and form a bandpass solution
# Requires pywcs-1.9-4.4.4 and numpy-1.7.0 or numpy-1.6.2 installed into casapy
# You can do this by installing PAPERcasa, and using 'casapython' to install the modules


# Natasha Hurley-Walker 10/07/2013
# Updated 08/08/2013 to scale the YY and XX beams separately
# Updated 01/10/2013 Use the field name as the calibrator name if the calibrator wasn't filled in properly during scheduling
# Updated 21/11/2013 Added sub-calibrators to complex fields (but didn't find much improvement)
# Updated 02/12/2013 Added a spectral beam option; turned subcalibrators off by default

import mwapy, subprocess, re
import mwapy.get_observation_info
from mwapy.obssched.base import schedule
import numpy as n,os,sys,shutil
try:
	import pyfits
except:
	import astropy.io.fits as pyfits
from mwapy.pb import make_beam
import mwapy
from taskinit import *
import tasks




# Attempte to autoset directories
# Model location:
if not os.environ.has_key('MWA_CODE_BASE'):
	print '$MWA_CODE_BASE not set: do not know where models are'
	raise KeyboardInterrupt
	
modeldir=os.environ['MWA_CODE_BASE']+'/MWA_Tools/Models/'
if not os.path.exists(modeldir):
	print 'Model directory %s does not exist' % modeldir
	raise KeyboardInterrupt	

try:
	db=schedule.getdb()
except:
	print 'Unable to open connection to database'
	raise KeyboardInterrupt	

def ft_beam(vis=None,refant='Tile012',clobber=True,
	    spectral_beam=False,
	    subcalibrator=False,uvrange='>0.03klambda'):
	"""
	def ft_beam(vis=None,refant='Tile012',clobber=True,
	spectral_beam=False,
	subcalibrator=False,uvrange='>0.03klambda'):

	# Reference antenna
	refant='Tile012'
	# Overwrite files
	clobber=True
	# Option to include the spectral index of the primary beam
	spectral_beam=False
	# Option to add more sources to the field
	"""
	# output calibration solution
	caltable=re.sub('ms','cal',vis)
	if vis is None or len(vis)==0 or not os.path.exists(vis):
		print 'Input visibility must be defined'
		return None
	
	# Get the frequency information of the measurement set
	ms.open(vis)
	rec = ms.getdata(['axis_info'])
	df,f0 = (rec['axis_info']['freq_axis']['resolution'][len(rec['axis_info']['freq_axis']['resolution'])/2],rec['axis_info']['freq_axis']['chan_freq'][len(rec['axis_info']['freq_axis']['resolution'])/2])
	F =rec['axis_info']['freq_axis']['chan_freq'].squeeze()/1e6
	df=df[0]*len(rec['axis_info']['freq_axis']['resolution'])
	f0=f0[0]
	rec_time=ms.getdata(['time'])
	sectime=qa.quantity(rec_time['time'][0],unitname='s')
	midfreq=f0
	bandwidth=df
	if isinstance(qa.time(sectime,form='fits'),list):
		dateobs=qa.time(sectime,form='fits')[0]
	else:
		dateobs=qa.time(sectime,form='fits')

	if spectral_beam:
		# Start and end of the channels so we can make the spectral beam image
		startfreq=f0-df/2
		endfreq=f0+df/2
		freq_array=[midfreq,startfreq,endfreq]
	else:
		freq_array=[midfreq]

	# Get observation number directly from the measurement set
	tb.open(vis+'/OBSERVATION')
	obsnum=int(tb.getcol('MWA_GPS_TIME'))
	tb.close

	info=mwapy.get_observation_info.MWA_Observation(obsnum,db=db)
	print 'Retrieved observation info for %d...\n%s\n' % (obsnum,info)

	# Calibrator information
	if info.calibration:
		calibrator=info.calibrators
	else:
		# Observation wasn't scheduled properly so calibrator field is missing: try parsing the fieldname
		# assuming it's something like 3C444_81
		calibrator=info.filename.rsplit('_',1)[0]

	print 'Calibrator is %s...' % calibrator

	# subcalibrators not yet improving the calibration, probably due to poor beam model
	if subcalibrator and calibrator=='PKS0408-65':
		subcalibrator='PKS0410-75'
	elif subcalibrator and calibrator=='HerA':
		subcalibrator='3C353'
	else:
		subcalibrator=False

	# Start models are 150MHz Jy/pixel fits files in a known directory
	model=modeldir+calibrator+'.fits'
	# With a corresponding spectral index map
	spec_index=modeldir+calibrator+'_spec_index.fits'

	if not os.path.exists(model):
		print 'Could not find calibrator model %s' % model
		return None
	
	# Generate the primary beam
	delays=info.delays
	str_delays=','.join(map(str,delays))
	print 'Delays are: %s' % str_delays

	# load in the model FITS file as a template for later
	ftemplate=pyfits.open(model)

	# do this for the start, middle, and end frequencies
	for freq in freq_array:
		freqstring=str(freq/1.0e6) + 'MHz'
		# We'll generate images in the local directory at the right frequency for this ms
		outname=calibrator+'_'+freqstring
		outnt2=calibrator+'_'+freqstring+'_nt2'
		# import model, edit header so make_beam generates the right beam in the right place
		if os.path.exists(outname + '.fits') and clobber:
			os.remove(outname + '.fits')
		shutil.copy(model,outname + '.fits')
		fp=pyfits.open(outname + '.fits','update')
		fp[0].header['CRVAL3']=freq
		fp[0].header['CDELT3']=bandwidth
		fp[0].header['DATE-OBS']=dateobs
		fp.flush()
  
		print 'Creating primary beam models...'
		beamarray=make_beam.make_beam(outname + '.fits',
					      delays=delays)
		# delete the temporary model
		os.remove(outname + '.fits')

		beamimage={}

		for stokes in ['XX','YY']:
			beamimage[stokes]=calibrator + '_' + freqstring + '_beam' + stokes + '.fits'

	# scale by the primary beam
	# Correct way of doing this is to generate separate models for XX and YY
	# Unfortunately, ft doesn't really understand cubes
	# So instead we just use the XX model, and then scale the YY solution later

	freq=midfreq
	freqstring=str(freq/1.0e6)+'MHz'
	outname=calibrator+'_'+freqstring
	outnt2=calibrator+'_'+freqstring+'_nt2'
	# divide to make a ratio beam, so we know how to scale the YY solution later
	fbeamX=pyfits.open(beamimage['XX'])
	fbeamY=pyfits.open(beamimage['YY'])
	ratiovalue=(fbeamX[0].data/fbeamY[0].data).mean()
	print 'Found <XX/YY>=%.2f' % ratiovalue

	# Models are at 150MHz
	# Generate scaled image at correct frequency
	if os.path.exists(outname + '.fits') and clobber:
		os.remove(outname + '.fits')
	# Hardcoded to use the XX beam in the model
	fbeam=fbeamX
	fmodel=pyfits.open(model)
	fspec_index=pyfits.open(spec_index)

	ftemplate[0].data=fbeam[0].data * fmodel[0].data/((150000000/f0)**(fspec_index[0].data))
	ftemplate[0].header['CRVAL3']=freq
	ftemplate[0].header['CDELT3']=bandwidth
	ftemplate[0].header['DATE-OBS']=dateobs
	ftemplate[0].header['CRVAL4']=1
	ftemplate.writeto(outname + '.fits')
	print 'Wrote scaled model to %s' % (outname + '.fits')
	foutname=pyfits.open(outname + '.fits')
	
	# Generate 2nd Taylor term
	if os.path.exists(outnt2 + '.fits') and clobber:
		os.remove(outnt2 + '.fits')

	if spectral_beam:
		# Generate spectral image of the beam
		fcalstart=pyfits.open(calibrator+'_'+str(startfreq/1.0e6)+'MHz_beamXX.fits')
		fcalend=pyfits.open(calibrator+'_'+str(endfreq/1.0e6)+'MHz_beamXX.fits')	
		ftemplate[0].data=(n.log(fcalstart[0].data/fcalend[0].data)/
				   n.log((f0-df/2)/(f0+df/2)))
		beam_spec='%s_%sMHz--%sMHz_beamXX.fits' % (calibrator,
							   str(startfreq/1.0e6),
							   str(endfreq/1.0e6))
		if os.path.exists(beam_spec):
			os.remove(beam_spec)
		ftemplate.writeto(beam_spec)
		fbeam_spec=pyfits.open(beam_spec)
	
		ftemplate[0].data=foutname[0].data * fbeam[0].data * (fspec_index[0].data+fbeam_spec[0].data)
	else:
		ftemplate[0].data=foutname[0].data * fbeam[0].data * fspec_index[0].data
	ftemplate[0].header['DATE-OBS']=dateobs
	ftemplate.writeto(outnt2 + '.fits')
	print 'Wrote scaled Taylor term to %s' % (outnt2 + '.fits')

	# import as CASA images
	if os.path.exists(outname + '.im') and clobber:
		tasks.rmtables(outname + '.im')
	if os.path.exists(outnt2 + '.im') and clobber:
		tasks.rmtables(outnt2 + '.im')
        tasks.importfits(outname + '.fits',outname + '.im')
	tasks.importfits(outnt2 + '.fits',outnt2 + '.im')
	print 'Fourier transforming model...'
	tasks.ft(vis=vis,model=[outname + '.im',outnt2+'.im'],
                 nterms=2,usescratch=True)

	print 'Calibrating...'
	tasks.bandpass(vis=vis,caltable=caltable,refant=refant,uvrange=uvrange)

	print 'Scaling YY solutions by beam ratio...'
	# Scale YY solution by the ratio
	tb.open(caltable)
	G = tb.getcol('CPARAM')
	tb.close()
	
	new_gains = n.empty(shape=G.shape, dtype=n.complex128)
	
	# XX gains stay the same
	new_gains[0,:,:]=G[0,:,:]
	# YY gains are scaled
	new_gains[1,:,:]=ratiovalue*G[1,:,:]

	tb.open(caltable,nomodify=False)
	tb.putcol('CPARAM',new_gains)
	tb.putkeyword('MODEL',model)
	tb.putkeyword('SPECINDX',spec_index)
	tb.putkeyword('BMRATIO',ratiovalue)
	try:
		tb.putkeyword('MWAVER',mwapy.__version__)
	except:
		pass
	tb.close()
	print 'Created %s!' % caltable
	return caltable

#ft_beam.ft_beam(vis=vis)
#caltable=ft_beam(vis=vis)
