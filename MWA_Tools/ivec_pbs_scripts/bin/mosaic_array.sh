#!/bin/bash

# Will generate beams, regrid the images, and then mosaic them

module load python/2.6.9 numpy/1.6.2 scipy

# user localisation
user=`whoami`

# host localisation
host=`hostname`
if [[ "${host:0:4}" == "epic" ]]
then
  computer="epic"
  groupq="astronomy818"
  standardq="routequeue"
  hostmem="20gb"
else
  computer="fornax"
  groupq="partner676"
  standardq="workq"
  hostmem="80gb"
fi

rootdir=/scratch/${groupq}
datadir=$rootdir/$user
codedir=$rootdir/code
queuedir=/home/$user/queue/

# Regridding options --- see the bottom of this script for a full description
# Survey Dec 18.6 - first pass
#regrid_commands="project=ZEA desc=350,10001,-0.625E-02,20000,-40.0,2801,0.625E-02,5600 axes=1,2 tol=0"
# Survey Dec -40 - first pass
#regrid_commands="project=ZEA desc=350,10001,-0.625E-02,20000,-40.0,2801,0.625E-02,5600 axes=1,2 tol=0"
#A3266
#regrid_commands="project=ZEA desc=67.799583,501,-0.625E-02,1000,-61.406389,501,0.625E-02,1000 axes=1,2 tol=0"
# NGC1534
#regrid_commands="project=ZEA desc=62.06666655,2001,-0.625E-02,4000,-62.76194443,2001,0.625E-02,4000 axes=1,2 tol=0"
# Test of two different Dec strips
regrid_commands="project=ZEA desc=30.0,2001,-0.625E-02,4000,-20.00,2001,0.625E-02,4000 axes=1,2 tol=0"

if [[ $1 ]] && [[ $2 ]]
then

 filelist=$1
 proj=$2

 cd $datadir/$proj

 if [[ -e $filelist ]]
 then
    filelength=`cat $filelist | wc -l`
    if [[ $filelength -lt 2 ]]
    then
        echo "$filelength has fewer than two images! Exiting..."
        exit 1
    fi
    identifier=`echo $filelist | awk 'BEGIN {FS="/"} {print $NF}' | awk 'BEGIN {FS="."} {print $1}'`

# Set up destination for beams, regridded files etc
    if [[ ! -d mosaics ]] ; then mkdir mosaics ; fi
    if [[ ! -d mosaics/$identifier ]] ; then mkdir mosaics/$identifier ; fi

    if [[ -e ${identifier}_beams.txt ]] ; then rm ${identifier}_beams.txt ; fi
    # Find out which beams need to be created
    for filewpath in `cat $filelist`
    do
        file=`echo $filewpath | awk 'BEGIN {FS="/"} {print $NF}'`
        obsnum=${file:0:10}
# Good way to skip multiple polarisations of the same file
        if [[ -e ${identifier}_temp.txt ]] && grep -q $obsnum ${identifier}_temp.txt
        then
            echo "Already checked ${obsnum}, moving on."
        else
# Try to get the delays from the metafits files so as not to spam the database
            cd `dirname $filewpath`
            if [[ -e ${obsnum}.metafits ]]
            then
                echo "Found ${obsnum}.metafits."
            else
                echo "Couldn't find ${obsnum}.metafits: creating a file..."
                make_metafits.py -g ${obsnum}
                if [[ ! -e ${obsnum}.metafits ]]
                then
                    echo "Couldn't create metafits file -- something must be very wrong!"
                    exit 1
                fi
            fi
            delays=`pyhead.py -p DELAYS -i ${obsnum}.metafits | awk '{print $3}'`
            channel=`pyhead.py -p CHANNELS -i  ${obsnum}.metafits  | awk '{print $3}' | awk 'BEGIN {FS=","} {print $13}'`
            cd `dirname $filelist`
            echo $filewpath" "$delays" "$channel >> ${identifier}_temp.txt
        fi
    done
    cd `dirname $filelist`
    sort -u -k2,3 ${identifier}_temp.txt > ${identifier}_beams.txt
    rm ${identifier}_temp.txt

    numbeams=`wc -l ${identifier}_beams.txt | awk '{print $1}'`

    cd $queuedir

    if [[ $numbeams -gt 1 ]]
    then
         cat beam_array.template | sed "s;FILELIST;${identifier}_beams.txt;g" | sed "s/FILELENGTH/${numbeams}/g" | sed "s;PROJ;${proj};g" | sed "s;HOSTMEM;${hostmem};g" | sed "s;GROUPQ;${groupq};g"  | sed "s;STANDARDQ;${standardq};g" | sed "s;DATADIR;$datadir;g" > bear_$identifier.sh
    else
         cat beam_single.template | sed "s;FILELIST;${identifier}_beams.txt;g" | sed "s;PROJ;${proj};g" | sed "s;HOSTMEM;${hostmem};g" | sed "s;GROUPQ;${groupq};g"  | sed "s;STANDARDQ;${standardq};g" | sed "s;DATADIR;$datadir;g" > bear_$identifier.sh
    fi
    jobnum=`qsub bear_$identifier.sh`

    cat regrid_array.template | sed "s;FILELIST;${filelist};g" | sed "s/FILELENGTH/${filelength}/g" | sed "s;PROJ;${proj};g" | sed "s;HOSTMEM;${hostmem};g" |  sed "s;CODEDIR;${codedir};g" | sed "s;GROUPQ;${groupq};g"  | sed "s;STANDARDQ;${standardq};g" | sed "s;DATADIR;$datadir;g" | sed "s;REGRID_COMMANDS;${regrid_commands};g" > rgd_$identifier.sh
    jobnum=`qsub -W depend=afterok:$jobnum rgd_$identifier.sh`
    # Then submit the job which knits them all together

    cat mosaic.template | sed "s;FILELIST;${filelist};g" | sed "s/FILELENGTH/${filelength}/g" | sed "s;PROJ;${proj};g" | sed "s;HOSTMEM;${hostmem};g" |  sed "s;CODEDIR;${codedir};g" | sed "s;GROUPQ;${groupq};g"  | sed "s;STANDARDQ;${standardq};g" | sed "s;DATADIR;$datadir;g" | sed "s;REGRID_COMMANDS;${regrid_commands};g" > mos_$identifier.sh
   qsub -W depend=afterok:$jobnum mos_$identifier.sh

 else
   echo "$filelist is invalid; please specify a real list of images."
   echo "You can use the full path, or put it in the project directory."
   exit 1
 fi
else
 echo "Give me a list of image files and a project ID, e.g. regrid_array.sh /scratch/astronomy123/user/project/last_night.txt G0001 ."
 echo "And optionally, some distinctive tag for the output, like mk1."
 exit 1
fi

exit 0

# Expecting a series of fits images of any stokes parameters, with file names like:
# Creates a big mosaic based on the projection you specify following the rules below:

#          projection   RA(deg)_0  pixel_x0  pixel_size(deg) size_x(pixels)
#                      Dec(deg)_0  pixel_y0  pixel_size(deg) size_y(pixels)
#                       axes=x,y    tolerance=intolerant ?:) you have to set it.

# Some examples:
# Cylindrical projection doesn't have pixels of equal area
#	regrid in=$root.im out=$root.regrid.im project=CYP desc=45,4001,-1.6667E-02,8000,-47.5,2401,-1.6667E-02,4800 axes=1,2 tol=0
# Healpix requires a template image?
#	regrid in=$root.im out=$root.regrid.im tin=512.im axes=1,2 tol=0 project=HPX
# A small patch around Vela
#	regrid in=$root.im out=$root.regrid.im project=AIT desc=128.5,513,-1.6667E-02,1024,-45.5,513,-1.6667E-02,1024 axes=1,2 tol=0
# Zeta C120 regrid_commands="project=ZEA desc=75,5201,-1.6667E-02,10400,-6,2501,-1.6667E-02,4800 axes=1,2 tol=0"
# Dec -47.5 drift scan regrid_commands="project=ZEA desc=75,4001,-1.6667E-02,8000,-47.5,2401,-1.6667E-02,4800 axes=1,2 tol=0"
# Gamma C101 regrid_commands="project=ZEA desc=48.75,3750,-1.6667E-02,7500,-26.7,3750,1.6667E-02,7500 axes=1,2 tol=0"
# LMC regrid_commands="project=ZEA desc=75,1600,-1.6667E-02,4000,-60,2500,1.6667E-02,4000 axes=1,2 tol=0"
# A3667 regrid_commands="project=SIN desc=303.14033,201,-1.6667E-02,400,-56.840639,201,1.6667E-02,400 axes=1,2 tol=0"
# Dec -47.5 drift scan
	#regrid_commands="project=ZEA desc=40,4001,-1.6667E-02,8000,-47.5,3401,1.6667E-02,4800 axes=1,2 tol=0"
# A small patch around Fornax
#	regrid_commands="project=SIN desc=50.673,513,-0.8333E-02,1024,-37.2093,513,0.8333E-02,1024 axes=1,2 tol=0"
# Dec -26 drift scan
#	regrid_commands="project=ZEA desc=40,5001,-1.6667E-02,10000,-26.7,2401,1.6667E-02,4800 axes=1,2 tol=0"
# AIT MASSIVE MOSAIC
#	regrid_commands="project=ZEA desc=40,6001,-1.6667E-02,12000,-37.5,3501,1.6667E-02,6000 axes=1,2 tol=0"
	# C102 GC drift
#	regrid_commands="project=ZEA desc=230.0,5001,-.8333E-02,10000,-26.7,2401,1.6667E-02,4800 axes=1,2 tol=0"
# Galactic Centre
#	regrid_commands="project=SIN desc=266.0,2401,-.8333E-02,4800,-26.7,2401,1.6667E-02,4800 axes=1,2 tol=0"
# W44
#	regrid_commands="project=SIN desc=285.0,2401,-.8333E-02,4800,1.5,2401,0.8333E-02,4800 axes=1,2 tol=0"
# Dec -26 drift scan -- fine mesh
#	regrid_commands="project=ZEA desc=40,10001,-0.83333333E-02,20000,-26.7,4801,0.83333333E-02,9600 axes=1,2 tol=0"

# see 'man regrid' for details on how to change these options
