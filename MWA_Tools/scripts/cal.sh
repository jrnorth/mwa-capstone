#! /bin/bash
#wrapper script for delaycal. input list of directories with uvfits files in them.
BDC=/usr/global/MWA/VirtualEnvironments/MWA/bin/bash_delaycal.py
CASA=/usr/global/MWA/casa//casapy
CALS=/home/djacobs/src/CASA_Cals/


FILES=$*
echo ${FILES}
for FILE in $FILES
do
        if [ -e ${FILE} ]
        then
            cd $FILE
            $CASA --nologger -c $BDC --caldir=/home/djacobs/src/CASA_Cals/ --src=all --nsrcs=1 --cat=bright_sources \
            --refant=2 --docal \
            --apply_cal --doimage --overwrite --useflagversion=MWAflag -C mwa_32T_pb  1*uvfits
            cd ..
        else
            echo $FILE does not exist. skipping
        fi
done

