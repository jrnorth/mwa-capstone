#!/bin/bash
# script to convert a bunch of correlator output files to a UVFITS file.
# uses corr2uvifts and pipe splat average and a bunch of named pipes to stream
# the data, avoiding unnecessary intermediate files
# Randall Wayth, Sep 2012, May 2013

# set defaults
nav_freq=1
gpubox_index=0    # this is the gpubox index from 1..24. 0 means all files.
nav_time=4
autoflag=0
ngpubox=24
nchan=$(( ngpubox * 32))
debug=1

if [ $# -lt 4 ] ; then
    echo "Usage: $0 <options>" 1>&2
    echo "  -O obsid        No default, required." 1>&2
    echo "  -f nav_freq     Default: $nav_freq" 1>&2
    echo "  -g gpubox_id    coarse chan gpu box index 1..24. Default: all" 1>&2
    echo "  -t nav_time     Default: $nav_time" 1>&2
    echo "  -R      enable RTS HA locking" 1>&2
    echo "  -F      enable autoflagger" 1>&2
    exit 0
fi

while getopts ":O:t:f:g:RF" opt; do
  case $opt in
    t)
        nav_time=$OPTARG
        ;;
    f)
        nav_freq=$OPTARG
        ;;
    g)
        gpubox_index=$OPTARG
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

prefix=""
if [ "$gpubox_index" -lt 10 ] ; then prefix="0" ; fi
hdrfile="header_${obsid}_all.txt"
antfile="antenna_locations_${prefix}${gpubox_index}.txt"
instfile="instr_config_$header_${prefix}${gpubox_index}.txt"

# check for metafiles
if [ ! -f "$hdrfile" ] ; then
    echo "no header file. Was looking for $hdrfile" 1>&2
    exit 0
fi

# prepend a "0" to the coarse chan for 1-9 to match gpubox name
cc_match=$gpubox_index
if [[ $gpubox_index -eq 0 ]] ; then
  # just count the first gpubox files in the case we want all files
  cc_match="01"
fi
if [[ $gpubox_index -gt 0 && $gpubox_index -lt 10 ]] ; then
  tmp=$(($gpubox_index*1))   # force int result with no leading zeros, just in case
  cc_match="0$tmp"
fi

# how many files to process from each gpubox?
nfiles=`ls *gpubox${cc_match}*.fits | wc -l`
if [ $debug -gt 0 ] ; then echo "there are $nfiles files to process" ; fi
if [ $nfiles -eq 0 ] ; then exit 1 ; fi

# make pipes
rm -f pipe_${obsid}*

# loop over files
# This code works for gpubox files that all start at the same time. For the old bug
# where they don't, some extra fiddling will be necessary.
for (( i=0 ; i< $nfiles ; i++ )) ; do
    mkfifo pipe_${obsid}_${i}.LACSPC
    mkfifo pipe_${obsid}_${i}.LCCSPC
    # assemble the string with the names of all the files
    tstring="$i"
    if [ "$i" -lt 10 ] ; then tstring="0$i" ; fi
    argstr=""
    for ((b=1; b<=$ngpubox; b++)) ; do
      bstring="$b"
      if [ $b -lt 10 ] ; then bstring="0$b" ; fi
      argstr="$argstr -v `ls *_gpubox${bstring}_${tstring}.fits`"
    done
    cmd="build_lfiles -m 1 -o pipe_${obsid}_${i} $argstr"
    if [ $debug -gt 0 ] ; then echo "cmd is: $cmd" ; fi
    ($cmd ; echo "Finished $f1" ) &
done

sleep 1

mkfifo pipe_${obsid}_cat.LACSPC
mkfifo pipe_${obsid}_cat.LCCSPC
mkfifo pipe_${obsid}_av.LACSPC
mkfifo pipe_${obsid}_av.LCCSPC

# cat the files into a time/freq averaging process
cat pipe_${obsid}_?.LACSPC > pipe_${obsid}_cat.LACSPC &
cat pipe_${obsid}_?.LCCSPC > pipe_${obsid}_cat.LCCSPC &

#wc -c pipe_${obsid}_cat.LACSPC &
#wc -c pipe_${obsid}_cat.LCCSPC 
#exit 0

pipe_splat_average.py --noadjustgains --auto  -f $nav_freq -t $nav_time -o pipe_${obsid}_av.LACSPC --channels=$nchan -i 256 < pipe_${obsid}_cat.LACSPC &
pipe_splat_average.py --noadjustgains --cross -f $nav_freq -t $nav_time -o pipe_${obsid}_av.LCCSPC --channels=$nchan -i 256 < pipe_${obsid}_cat.LCCSPC &

#wc -c pipe_${obsid}_av.LACSPC &
#wc -c pipe_${obsid}_av.LCCSPC 
#exit 0

echo "running corr2uvfits"
corr2uvfits -a pipe_${obsid}_av.LACSPC -c pipe_${obsid}_av.LCCSPC -o ${obsid}.uvfits -H "$hdrfile"

#rm -f pipe_${obsid}*

