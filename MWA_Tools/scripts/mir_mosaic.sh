#!/bin/bash

# Expecting a series of fits images of any stokes parameters, with file names like:
# obsnum_stokes.fits
# preferably where stokes = x, y, or i. (Not tested thoroughly to be robust to e.g. XX, YY)
# Creates a big mosaic based on the projection you specify below:

#          projection   RA(deg)_0  pixel_x0  pixel_size(deg) size_x(pixels)
#                      Dec(deg)_0  pixel_y0  pixel_size(deg) size_y(pixels)
#                       axes=x,y    tolerance=intolerant ?:) you have to set it.

regrid_commands="project=ZEA desc=45,4001,-1.6667E-02,8000,-47.5,2401,-1.6667E-02,4800 axes=1,2 tol=0"

# Some other examples:
# Cylindrical projection doesn't have pixels of equal area
#	regrid in=$root.im out=$root.regrid.im project=CYP desc=45,4001,-1.6667E-02,8000,-47.5,2401,-1.6667E-02,4800 axes=1,2 tol=0
# Healpix requires a template image?
#	regrid in=$root.im out=$root.regrid.im tin=512.im axes=1,2 tol=0 project=HPX
# A small patch around Vela
#	regrid in=$root.im out=$root.regrid.im project=AIT desc=128.5,513,-1.6667E-02,1024,-45.5,513,-1.6667E-02,1024 axes=1,2 tol=0

# see 'man regrid' for details on how to change these options

i=0
for file in 10*.fits
do
# Apply fixhdr if it hasn't been done already
	if ! grep -q PV2_1 $file
	then
		fixhdr -R -v -T -o new.fits $file
		mv new.fits $file
	fi
# Generate a primary beam (if there isn't one already in the directory)
	root=`echo $file | sed "s/.fits//"`
	obsnum=`echo $root | awk 'BEGIN {FS="_"} {print $1}'`
	stokes=`echo $root | awk 'BEGIN {FS="_"} {print $2}'`
	delays=`get_observation_info.py -g $obsnum | grep "delays" | awk '{print $3}'`
	if [[ ! -e ${obsnum}_x_beam.im ]]
	then
		if [[ ! -e ${obsnum}_x_beam.fits ]]
		then
			make_beam.py -f $file -d $delays
			mv ${root}_beamXX.fits ${obsnum}_x_beam.fits
			mv ${root}_beamYY.fits ${obsnum}_y_beam.fits
		fi
		fits op=xyin in=${obsnum}_x_beam.fits out=${obsnum}_x_beam.im
		fits op=xyin in=${obsnum}_y_beam.fits out=${obsnum}_y_beam.im
		if [[ "$stokes"=="i" ]] || [[ "$stokes"=="I" ]] ||  [[ "$stokes"=="ii" ]] ||  [[ "$stokes"=="II" ]]
		then
# Fake a Stokes I beam
			maths exp="(<${obsnum}_x_beam.im>+<${obsnum}_y_beam.im>)/2" out=${obsnum}_${stokes}_beam.im
			fits op=xyout in=${obsnum}_${stokes}_beam.im out=${obsnum}_${stokes}_beam.fits
		fi
	fi
	beam=${obsnum}_${stokes}_beam
			
	fits op=xyin in=$file out=$root.im
	regrid in=$root.im out=$root.regrid.im $regrid_commands
	regrid in=$beam.im out=$beam.regrid.im $regrid_commands
	maths exp="<$root.regrid.im>*<$beam.regrid.im>" out=${root}_mult.regrid.im options=unmask
	maths exp="<$beam.regrid.im>*<$beam.regrid.im>" out=${root}_beamsq.regrid.im options=unmask

# There's a limit to the number of files miriad can handle in a single expression,
# so it's necessary to sequentially build up the mosaic from individual files
	if [[ $i -gt 0 ]]
# i.e. it's not the first file
	then
		maths exp="<$savedfirst>+<${root}_mult.regrid.im>" out=mosaic$i.im options=unmask
		maths exp="<$savedbeam>+<${beam}.regrid.im>" out=beam_mosaic$i.im options=unmask
		maths exp="<$savedbeamsq>+<${root}_beamsq.regrid.im>" out=beamsq_mosaic$i.im options=unmask
# Each mosaic is huge so it's a good idea to clean up files you're not using
		rm -rf $savedfirst $savedbeam $savedbeamsq
# Can also delete the regridded files - they're just as big
		rm -rf ${root}_mult.regrid.im ${beam}.regrid.im ${root}_beamsq.regrid.im
		savedfirst="mosaic$i.im"
		savedbeam="beam_mosaic$i.im"
		savedbeamsq="beamsq_mosaic$i.im"
	else
# it's the very first file: nothing to add or multiply, just save the variables
		savedfirst=${root}_mult.regrid.im
		savedbeam=${beam}.regrid.im
		savedbeamsq=${root}_beamsq.regrid.im
	fi
	((i+=1))
done

# Make the final maps
((i-=1))

maths exp="<mosaic$i.im>/<beam_mosaic$i.im>" out=weighted_mosaic.im options=unmask
maths exp="<mosaic$i.im>/<beamsq_mosaic$i.im>" out=pb-corrected_mosaic.im options=unmask
fits op=xyout in=weighted_mosaic.im out=weighted_mosaic.fits
fits op=xyout in=pb-corrected_mosaic.im out=pb-corrected_mosaic.fits

exit 0
