#!/bin/bash

# Modified version of RW's miriad commands to apply a CASA calibration and then
# run miriad imaging on a uv-fits file

# $1 is the obsid of the dataset you want to reduce; it is assumed it lives in 
#   $datadir/$obsid/$obsid.uvfits
# $2 is the optional (CASA) calibration solution's full path, e.g.
#   /data/das2/CASA_Cals/$obsid.cal
# If you don't specify this, the script will look for a file like
#   $datadir/$obsid/$obsid_cal.uvfits
# and if it doesn't find this, it will exit.

if [ $# -lt 1 ] ; then
	echo "Usage: $0 src [cal]"
	echo "e.g. mir_sip.sh 1012345678 /data/CASA_Cals/1012357888.cal"
	exit 0
fi

# Assumes standard ngas layout of files obsid/obsid.uvfits
datadir=/data/das4/Alpha_uvfits/C112/

# For the auto-flagger (hopefully this will become obsolete soon)
toolsdir=/data/das4/packages/MWA_Tools/

src=$1
cal=$2

stoke="xx yy i"

# Wherever you are, we make a scratch directory and a results directory:

if [[ ! -d ./scratch ]]
then
	mkdir scratch
fi

if [[ ! -d ./results ]]
then
	mkdir results
fi

cd scratch/

if [[ -e ${datadir}/${src}/${src}.uvfits || -d ${datadir}/${src}/${src}.ms ]]
then

# import uvfits or measurement set and apply calibration
	if [[ $2 ]]
	then
		if [[ -e ${datadir}/${src}/${src}.uvfits && -d $2 ]]
		then
			ln -s ${datadir}/${src}/${src}.uvfits ./
			echo "vis='${src}.ms'" > casa_commands.py
			echo "importuvfits(fitsfile='${src}.uvfits',vis=vis)" >> casa_commands.py
			cat $toolsdir/scripts/auto_flag.py >> casa_commands.py
			echo "applycal(vis=vis,gaintable='${cal}')" >> casa_commands.py
			echo "exportuvfits(vis=vis,fitsfile='${src}_cal.uvfits',multisource=False)" >> casa_commands.py
			echo "rmtables(vis)" >> casa_commands.py
			casapy --nologger -c casa_commands.py
			rm -rf ${src}.ms.flagversions
		elif [[ -d ${datadir}/${src}/${src}.ms && -d $2 ]]
		then
			echo "vis='${src}.ms'" > casa_commands.py
			echo "split(vis='${datadir}/${src}/'+vis,outputvis=vis,datacolumn='data')" >> casa_commands.py
	# assuming ms was made by cotter so flagging unnecessary
			echo "applycal(vis=vis,gaintable='${cal}')" >> casa_commands.py
			echo "exportuvfits(vis=vis,fitsfile='${src}_cal.uvfits',multisource=False)" >> casa_commands.py
			echo "rmtables(vis)" >> casa_commands.py
			casapy --nologger -c casa_commands.py
			rm -rf ${src}.ms.flagversions
		else
			echo "Calibration solution not found!"
			exit 1
		fi
	else
		echo "Calibration not specified; linking directly."
		if [[ -e ${datadir}/${src}/${src}_cal.uvfits ]]
		then
			ln -s ${datadir}/${src}/${src}_cal.uvfits ./
		else
			echo "No calibrated uvfits file found! Exiting..."
			exit 1
		fi
	fi

# Remove any old files and import the new one; add a probably-incorrect estimate of T_sys
	rm -rf ${src}.uv
	fits op=uvin in=${src}_cal.uvfits out=${src}.uv
	puthd in=${src}.uv/systemp value=200.0
	puthd in=${src}.uv/jyperk value=750.0

# Optionally, delete the calibrated uvfits file
	rm ${src}_cal.uvfits

# flag first few seconds
	qvack vis=${src}.uv mode=frequency interval=0.1

# flag central chans (40kHz version)
# TODO: Update this to work on any fine-channel width
	uvflag flagval=flag vis=${src}.uv line=channel,24,17,1,32

# flag edge channels (40 kHz version)
	uvflag flagval=flag vis=${src}.uv line=channel,24,1,1,32
	uvflag flagval=flag vis=${src}.uv line=channel,24,2,1,32
	uvflag flagval=flag vis=${src}.uv line=channel,24,3,1,32
	uvflag flagval=flag vis=${src}.uv line=channel,24,32,1,32
	uvflag flagval=flag vis=${src}.uv line=channel,24,31,1,32
	uvflag flagval=flag vis=${src}.uv line=channel,24,30,1,32

# flag orbcomm
	centchan=`get_observation_info.py -g ${src} | head -3 | tail -1 | awk 'BEGIN {FS=","} {print $13}'`
	orbstart=`echo "( $centchan - 115 ) * 24 + 17" | bc -l`
	orbend=`echo "( $centchan - 115 ) * 24 + 49" | bc -l`
	if [[ $orbend -gt 0 ]]
	then
		uvflag flagval=flag vis=${src}.uv line=channel,32,$orbend
	fi

	if [[ $orbstart -gt 0 ]]
	then
		uvflag flagval=flag vis=${src}.uv line=channel,32,$orbstart
	fi

# Select imaging parameters
	select='uvrange(0.01,10)'

# Going for 40x40 degree images regardless of cellsize
# Clean to 3sigma (estimated)
	if [[ ${src} -gt 1030000000 ]] && [[ ${src} -le 1032653528 ]]
	then
		cell=300
		imsize=960
		threshold=1.0
		echo "Alpha array: using $imsize x $imsize $cell arcsecond pixels;"
	fi 
	if [[ ${src} -gt 1032653528 ]] && [[ ${src} -le 1034927848 ]]
	then
		cell=120
		imsize=2400
		threshold=0.8
		echo "Beta array: using $imsize x $imsize $cell arcsecond pixels"
	fi
	if [[ ${src} -gt 1034928064 ]] && [[ ${src} -le 1037011960 ]]
	then
    		cell=60
		imsize=4800
		threshold=0.120
		echo "Gamma array: using $imsize x $imsize $cell arcsecond pixels"
	fi
	if [[ ${src} -gt 1037011970 ]] && [[ ${src} -le 1037262456 ]]
	then
    		cell=30
                imsize=9600
		threshold=0.120
		echo "Delta array: using $imsize x $imsize $cell arcsecond pixels"
	fi
	if [[ ${src} -gt 1037262456 ]] && [[ ${src} -le 1038215664 ]]
	then
    		cell=30
                imsize=9600
		threshold=0.120
		echo "Epsilon array: using $imsize x $imsize $cell arcsecond pixels"
	fi
	if [[ ${src} -gt 1038215664 ]] && [[ ${src} -le 1039284016 ]]
	then
    		cell=60
		imsize=4800
		threshold=0.120
		echo "Zeta array: using $imsize x $imsize $cell arcsecond pixels"
	fi
	if [[ ${src} -gt 1039284016 ]] && [[ ${src} -le 1043000000 ]]
	then
    		cell=300
                imsize=960
		threshold=1.0
		echo "Eta array: using $imsize x $imsize $cell arcsecond pixels"
	fi
	if [[ ${src} -gt 1043000000 ]]
	then
		cell=30
		imsize=4800
		threshold=0.120
		echo "128T: using $imsize x $imsize $cell arcsecond pixels"
	fi

	for stokes in $stoke
	do
		rm -rf ${src}_${stokes}.map ${src}_${stokes}.beam ${src}_${stokes}.clean ${src}_${stokes}.restor
		invert vis=${src}.uv map=${src}_${stokes}.map beam=${src}_${stokes}.beam imsize=${imsize},${imsize} robust=0 options=double,mfs stokes=${stokes} select=${select} cell=${cell}
		clean map=${src}_${stokes}.map beam=${src}_${stokes}.beam out=${src}_${stokes}.clean niters=20000 speed=-1 cutoff=${threshold}
		restor model=${src}_${stokes}.clean beam=${src}_${stokes}.beam map=${src}_${stokes}.map out=${src}_${stokes}.restor
		fits op=xyout in=${src}_${stokes}.restor out=${src}_${stokes}.fits
		mv ${src}_${stokes}.fits ../results/
        	rm -rf ${src}_${stokes}.*
	done
        rm -rf ${src}.*

else
	echo "${src}.uvfits doesn't exist!"
fi

exit 0
