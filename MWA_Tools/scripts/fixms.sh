#!/bin/bash

PROGRAM=`basename $0`
MS=$1
MWATOOLS=$2

if [ $# -ne 2 ]; then
    echo "Usage:" $PROGRAM "<your/ms> <your/MWA_Tools/scripts/directory>"
    echo "This script replaces the ANTENNA table of your measurement set that is imported from a cotter uvfits file."
    echo "It gets the ANTENNA table from MWA_Tools/scripts."
    exit
fi

echo "Copy correct ANTENNA table to" ${MS}
cp ${MWATOOLS}/ms_antenna.tar.gz .
tar -xzf ms_antenna.tar.gz
rm -r ${MS}/ANTENNA
mv ANTENNA ${MS}
rm ms_antenna.tar.gz