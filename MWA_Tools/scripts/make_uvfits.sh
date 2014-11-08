#!/bin/bash
# wrapper script to make UVFITS files from raw correlator .fits
# updated for full array
# Randall Wayth. Sep 2012, March 2013.
#

debug=1
nav_freq=1
nav_time=4
gpubox_id=13
base=/media/data/MWA
rts_output=0
autoflag=0

if [ $# -lt 2 ] ; then
  echo "usage: $0 -O obsid [-f nav_freq] [-t nav_time] [-g gpubox_id(1..24)] [-b output_basedir] [-F] [-R]" 1>&2
  echo "    Default freq av: $nav_freq" 1>&2
  echo "    Default time av: $nav_time" 1>&2
  echo "    Default gpubox: $gpubox_id" 1>&2
  echo "    Default output basedir: $base" 1>&2
  echo "    -F: enable flagging. Default: $autoflag" 1>&2
  echo "    -R: specify RTS option for phase centre" 1>&2
  exit 0
fi

while getopts ":O:t:f:g:b:RF" opt; do
  case $opt in
    t)
        nav_time=$OPTARG
        ;;
    f)
        nav_freq=$OPTARG
        ;;
    g)
        gpubox_id=$OPTARG
        ;;
    b)
        base=$OPTARG
        ;;
    R)
        rts_output=1
        ;;
    F)
        autoflag=1
        ;;
    O)
        obsid=$OPTARG
        ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
  esac
done

# minimal sanity checks
if [ $nav_freq -lt 1 ] ; then
  echo "bad number of freqs to average: $nav_freq" 1>&2
  exit 1
fi
if [ $nav_time -lt 1 ] ; then
  echo "bad number of times to average: $nav_time" 1>&2
  exit 1
fi
if [ ! -d $base ] ; then
  echo "Output base dir $base does not exist" 1>&2
  exit 1
fi
if [ $gpubox_id -lt 1 ] ; then
  echo "bad coarse chan $gpubox_id" 1>&2
  exit 1
fi
if [ -z "$obsid" ] ; then
  echo "please set an obsid" 1>&2
  exit 1
fi

if [[ "$obsid" -lt 1031241617 ]] ; then
  echo "Obsid $obsid was in the dark ages..." 1>&2
  exit 1
fi

# set output dir according to subarray
if [[ "$obsid" -lt  1048300000 ]] ; then
  echo "This was prior to 128T. Perhaps you want make_uvfits_commish.sh?" 1>&2
  exit 1
fi

if [[ "$obsid" -gt 1048300000 ]] ; then basedir=${base} ; fi

if [ $debug -ne 0 ] ; then
  echo "Basedir: $basedir"
  echo "Nav freq: $nav_freq"
  echo "Nav time: $nav_time"
  echo "Coarse chan: $gpubox_id"
fi

mkdir -p $basedir/$obsid
cd $basedir/$obsid

getFitsFiles.sh $obsid $gpubox_id
rts_opt=""
if [ "$rts_output" -gt 0 ] ; then rts_opt=" -R" ; fi
if [ ! -f header.txt ] ; then
  make_metafiles_128T.sh $obsid $gpubox_id $nav_time $rts_opt
else
  echo "header.txt already present. Not overwriting files..."
fi

nice c2uv_128T.sh -O $obsid -f $nav_freq -g $gpubox_id -t $nav_time "$rts_opt"


