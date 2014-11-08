#!/bin/bash
# wrapper script to make UVFITS files from raw correlator .fits
# Randall Wayth. Sep 2012.
#

debug=1
nav_freq=4
nav_time=2
base=/data2/MWA

if [ $# -lt 1 ] ; then
  echo "usage: $0 obsid [ nav_freq nav_time [output_basedir] ]"
  echo "    Default freq av: $nav_freq"
  echo "    Default time av: $nav_time"
  echo "    Default output basedir: $base"
  exit 0
fi

obsid=$1
if [ $# -ge 3 ] ; then
  nav_freq=$2
  nav_time=$3
fi
if [ $# -eq 4 ] ; then
  base=$4
fi

# minimal sanity checks
if [ $nav_freq -lt 1 ] ; then
  echo "bad number of freqs to average: $nav_freq"
  exit 1
fi
if [ $nav_time -lt 1 ] ; then
  echo "bad number of times to average: $nav_time"
  exit 1
fi
if [ ! -d $base ] ; then
  echo "Output base dir $base does not exist"
  exit 1
fi

if (( "$obsid" < 1031241617 )) ; then
  echo "Obsid $obsid was in the dark ages..."
  exit 1
fi

# set output dir according to subarray
if (( "$obsid" > 1031241617 )) ; then basedir=${base}/alpha ; fi
if (( "$obsid" > 1033056017 )) ; then basedir=${base}/beta ; fi
if (( "$obsid" > 1035129617 )) ; then basedir=${base}/gamma ; fi
if (( "$obsid" > 1037030417 )) ; then basedir=${base}/delta ; fi
if (( "$obsid" > 1037203217 )) ; then basedir=${base}/epsilon ; fi
if (( "$obsid" > 1038240017 )) ; then basedir=${base}/zeta ; fi
if (( "$obsid" > 1039309072 )) ; then basedir=${base}/eta ; fi
if (( "$obsid" > 1048300000 )) ; then basedir=${base}/128T ; fi

if [ $debug -ne 0 ] ; then
  echo "Basedir: $basedir"
  echo "Nav freq: $nav_freq"
  echo "Nav time: $nav_time"
fi

mkdir -p $basedir/$obsid
cd $basedir/$obsid

if [ ! -f header.txt ] ; then
  make_metafiles.py -g $obsid --timeoffset=0
else
  echo "header.txt already present. Not overwriting files..."
fi

obs_freq=`cat header.txt | grep FREQCENT | tr -s " " | cut -f 2 -d" "`

cent_chan=`echo "scale=0; ( $obs_freq + 0.64 )/ 1.28" | bc -l`
if [ $debug -ne 0 ] ; then
  echo "Cent chan: $cent_chan"
fi

getFitsFiles.sh $obsid

c2uv.sh $obsid $nav_freq $cent_chan $nav_time

