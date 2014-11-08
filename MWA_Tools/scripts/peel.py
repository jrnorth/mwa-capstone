# auto-rotate visibilities, subtract the Crab, rotate back
# Natasha Hurley-Walker
# May 2013

# Note that to use chgcentre outside of casa, you need to install casacore and point toward the geodetics directories:

# Add to your /home/user/.casarc and uncomment:
#measures.DE200.directory: /scratch/astronomy556/code/casacore-data/ephemerides
#measures.DE405.directory: /scratch/astronomy556/code/casacore-data/ephemerides
#measures.line.directory: /scratch/astronomy556/code/casacore-data/ephemerides
#measures.sources.directory: /scratch/astronomy556/code/casacore-data/ephemerides
#measures.comet.directory: /scratch/astronomy556/code/casacore-data/ephemerides
#measures.ierseop97.directory: /scratch/astronomy556/code/casacore-data/geodetic
#measures.ierspredict.directory: /scratch/astronomy556/code/casacore-data/geodetic
#measures.tai_utc.directory: /scratch/astronomy556/code/casacore-data/geodetic
#measures.igrf.directory: /scratch/astronomy556/code/casacore-data/geodetic
#measures.observatory.directory: /scratch/astronomy556/code/casacore-data/geodetic


import subprocess
import re

# get current RA and dec

ms.open(vis)
rec=ms.summary()
ms.close()

# CASA 3.4
try: 
   ra_rad=rec['header']['field_0']['direction']['m0']
# CASA 4.++
except:
   ra_rad=rec['field_0']['direction']['m0']
ra=qa.formxxx(ra_rad,format='hms')
ra=re.sub('\:','h',ra,1)
ra=re.sub('\:','m',ra,1)
ra=ra+'s'

# CASA 3.4
try: 
   dec_rad=rec['header']['field_0']['direction']['m1']
# CASA 4.++
except:
   dec_rad=rec['field_0']['direction']['m1']
dec=qa.formxxx(dec_rad,format='dms')
dec=re.sub('\.','d',dec,1)
dec=re.sub('\.','m',dec,1)
dec=dec+'s'

sources=[['Crab','05h34m31.94s','+22d00m52.2s'],['HydA','09h18m05.651s','-12d05m43.99s'],['PicA','05h19m49.735s','-45d46m43.70s'],['PKS2356-61','23h59m04.365s','-60d54m59.41s'],['PKS2153-69','21h57m05.98061s','-69d41m23.6855s'],['CygnusA','19h59m28.35663s','+40d44m02.0970s']]

for source in sources:
	print source

	ra_distance_h=qa.abs(qa.sub(ra,source[1]))
#	ra_distance_d=qa.abs(qa.sub(ra,source[1])*qa.cos(dec))
	dec_distance=qa.abs(qa.sub(dec,source[2]))
	# Three general positions for a source to fall in, due to the nature of the square grating lobes
	# A better way of doing this would be to check if the estimated flux of the source (flux * pb response) exceeds some value
	# Within an hour of RA (15 degrees) - ignoring the cos term for now
	# Within 10 degrees of Dec, and 30 degrees of RA
	# Within 20 degrees of Dec, and 22.5 degrees of RA
	if ((ra_distance_h['value']<15) or ((ra_distance_h['value']<30) and (dec_distance['value']<10)) or ((ra_distance_h['value']<25) and (dec_distance['value']<20))):
		subprocess.call(["chgcentre",vis,source[1],source[2]])
	# make a 5deg x 5deg image with 1' resolution - should be suitable for all arrays

#for stokes in 'xx','yy':
# Don't know how to make a model that contains XX and YY separately so treat as the same for now
		stokes='I'
		clean(vis=vis, imagename=vis+'_'+source[0]+'_'+stokes, gridmode='widefield', psfmode='hogbom', imagermode='csclean', wprojplanes=1, facets=1, niter=5000, imsize=[80,80], cell=['1arcmin', '1arcmin'], threshold='1Jy', stokes=stokes, mode='mfs', selectdata=True, uvrange='0.01~3klambda', weighting='uniform',nterms=2,cyclefactor=100,usescratch=True)

# FT into the visibilities
# Shouldn't need to do this if usescratch=True
#	ft(vis=vis,model=[vis+'_'+source[0]+'_'+stokes+'.model.tt0',vis+'_'+source[0]+'_'+stokes+'.model.tt1'],nterms=2,usescratch=True,incremental=False)

# subtract
		uvsub(vis=vis,reverse=False)
# remove images
		rmtables(vis+'_'+source[0]+'*')


# rotate back
subprocess.call(["chgcentre",vis,ra,dec])
