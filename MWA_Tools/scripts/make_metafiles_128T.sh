#!/bin/bash
# Script to make corr2uvfits meta files for 128T single/multi channel data.
# Randall Wayth. 2012, 2013, 2014...

debug=1

if [ $# -lt 3 ] ; then
  echo "Usage: $0 <obsid> <gpubox IDs, comma sep, or 'all'> <n_avg_time> [-R]" 1>&2
  exit 0
fi

obsid=$1
gpubox_indices=$2
nav_time=$3
for_rts=0               # flag to change the phase centre to zenith for RTS if necessary
corr_int_time=0.5       # seconds. Newer correlator files have this in the header of the fits files.
freqres=40              # kHz. This will be read from DB and/or O-file later
n_inp=256

if [ "$4" = "-R" ] ; then
  echo "Setting output for RTS: phase centre at zenith"
fi

# simple sanity check:
if [ $obsid -lt 1048300000 ] ; then
  echo "Obsid $obsid was in the dark ages... exiting." 1>&2
  exit 1
fi
# split out the desired gpubox indices into an array
gpubox_ind=()   # empty array of gpubox indices
if [ "$gpubox_indices" == "all" ] ; then
    # we want all 24 gpu boxes
    for i in {1..24} ; do gpubox_ind+=("$i") ; done
else
    # extract comma-separated list into an array
    IFS=',' read -ra gpubox_ind <<< "$gpubox_indices"
fi

if [ "$gpubox_ind" -lt 1 ] ; then
  echo "gpubox index must be between 1 and 24" 1>&2
  exit 1
fi

# check if psql environment variable(s) are set
: ${PGDATABASE:?"Need to set DB connect environment vars"}

if [ "${debug:-0}" -gt 0 ] ; then echo "Making corr2uvfits files for obsid: $1" ; fi

# big query to get the instrument config and antenna info:
q="select ri.receiver_id, ri.active, sct.tilename, orc.slot_power, pc.correlator_index as corr_ind,  cpm.corr_product_index as corr_prod_ind, to_char((ci.eleclength - ri.fibre_length/cv2.velocity_factor),'09999D999') as elec_length, sct.tile_pos_east as east, sct.tile_pos_north as north, sct.tile_alt as height, tf.tile_id as flag, orc.observing_status as status \
from receiver_info ri \
left outer join obsc_recv_cmds orc ON (orc.rx_id=ri.receiver_id and orc.starttime=$obsid), \
pfb_correlator_mapping pc, pfb_receiver_connection pr, \
tile_connection tc, siteconfig_tilecorrproductmapping cpm, cable_velocity_factor cv2, cable_flavor cf, cable_info ci, siteconfig_tile sct \
left outer join tile_flags tf ON (tf.tile_id = sct.tilenumber and tf.starttime<$obsid and tf.stoptime > $obsid) \
where ri.begintime < $obsid and ri.endtime > $obsid \
and pc.pfb_id=pr.pfb_id and pc.pfb_slot=pr.pfb_slot \
and pr.rx_id=ri.receiver_id \
and pr.begintime<$obsid and pr.endtime>$obsid and pc.begintime<$obsid and pc.endtime>$obsid \
and tc.receiver_id=ri.receiver_id and tc.begintime<$obsid and tc.endtime>$obsid \
and cpm.rx_slot = tc.receiver_slot \
and ci.flavor=cf.flavor and ci.name=tc.cable_name \
and ci.begintime<$obsid and ci.endtime>$obsid \
and sct.tilenumber=tc.tile \
and cv2.type='fiber' \
and cf.begintime<$obsid and cf.endtime>$obsid \
order by corr_ind, corr_prod_ind \
; "

tmpfile=`mktemp /tmp/arrayconfig.XXXXXX`
if [ "${debug:-0}"  -gt 0 ] ; then  echo "Temp file: $tmpfile" ; fi

# execute the query for the instrument config
if [ "${debug:-0}"  -gt 0 ] ; then echo "Querying array config..." ; fi
psql -t -c "$q" >> $tmpfile
if [ $? -ne 0 ] ; then
  echo "Problem executing query:\n$q" 1>&2
  exit
fi

# generate the instr_config and antenna_locations files from the result of the query
if [ "${debug:-0}"  -gt 0 ] ; then echo "Making antenna_locations and instr_config files..." ; fi
q2c.py $tmpfile

# get the info about the observation (the 'settings')
cmd="select ms.starttime,stoptime,obsname,mode,ra_phase_center,dec_phase_center, projectid, \
dataquality, number, azimuth, elevation, ra, dec, frequencies, int_time, freq_res, extract(epoch from timestamp_gps($obsid)) \
from mwa_setting ms, rf_stream rf \
where ms.starttime = rf.starttime and ms.starttime = $obsid;"

if [ "${debug:-0}"  -gt 0 ] ; then echo "Querying settings" ; fi
tmp_settings=`mktemp /tmp/settings.XXXXXX`
psql -A -t -c "$cmd" | sed '/^$/d' > $tmp_settings # run query and trim trailing blank line
# check how many rows we got back- sanity check. Should be 1.
nlines=`wc -l $tmp_settings | sed 's/^ *//' | cut -f 1 -d " "`
# this will be OK for very rare obs with multiply rf_streams (e.g. AAVS0.5)
if [ "$nlines" -lt 1 ] ; then
  echo "Bad result for mwa_setting query for $obsid. Result from the DB is (in $tmp_settings):" 1>&2
  cat $tmp_settings 1>&2
  exit 1
fi

# split the resulting line by '|' separator
IFS='|' read -ra settings < "$tmp_settings"
# extract columns
start=${settings[0]}
stop=${settings[1]}
fieldname=${settings[2]}
mode=${settings[3]}
ra_ph=${settings[4]}
dec_ph=${settings[5]}
projid=${settings[6]}
dataquality=${settings[7]}
az=${settings[9]}
el=${settings[10]}
ra=${settings[11]}
dec=${settings[12]}
freqs=${settings[13]:1:$((${#settings[13]}-2))}
corr_int_time=${settings[14]}
freqres=${settings[15]}
ts=${settings[16]}          # this is the obsid converted to Unix time as a guess for the start time

if [ "${debug:-0}"  -gt 0 ] ; then
    echo "=== Settings ==="
    echo "Start/stop GPS time: $start, $stop"
    echo "Fieldname: $fieldname"
    echo "Coarse chans: $freqs"
    echo "======"
fi

# extract number of fine channels per coarse chan
nchan=`echo $freqres | awk ' { print 1280/$1 }'`
if [ "$nchan" -lt 8 -o "$nchan" -gt 128 ] ; then
    echo "Bad derived number of channels from freqres: $freqres. nchan: $nchan" 1>&2
    exit 1
fi
if [ "${debug:-0}"  -gt 0 ] ; then echo "Derived $nchan fine chans per coarse chan" ; fi

# extract coarse chan indexes from obs metadata
IFS=',' read -ra freqarr <<< "$freqs"
# sanity check
if [ ${#freqarr[@]} -ne 24 ] ; then
  echo "There are not 24 coarse chans defined for this obs. Got: $freqs" 1>&2
  exit 1
fi

# reverse the order of coarse chans after 128 so that GPU box index-1 selects
# the corresponding coarse channel
r_ind=24
for ind in {0..23} ; do 
  if [ ${freqarr[$ind]} -gt 128 ] ; then
    r_ind=$ind
    break
  fi
done
if [ $r_ind -lt 23 ] ; then
  for (( i=0 ; i<(24-$r_ind)/2 ; i++ )) ; do
    temp=${freqarr[$((23-i))]}
    freqarr[$((23-i))]=${freqarr[$((r_ind + i))]}
    freqarr[$((r_ind + i))]=$temp
  done
fi
if [ "${debug:-0}"  -gt 0 ] ; then
    echo "Coarse channel IDs in gpubox order: ${freqarr[@]}"
fi

# extract number of channels, time and integration time from a gpubox file.
# specifying an array without an index just gives you the first item
prefix=""
if [ $gpubox_ind -lt 10 ] ; then
    prefix="0"
fi
read -ra gpubox_files <<< `ls ${obsid}_*gpubox${prefix}${gpubox_ind}*.fits`
if [ ${#gpubox_files[@]} -lt 1 ] ; then
    echo "Could not find a gpubox file. Cannot verify time/freq info from O-files." 1>&2
else
    if [ "${debug:-0}" -gt 0 ] ; then
      echo "Extracting time, nchans etc from ${gpubox_files[0]}" 
    fi

    # get the time etc from the first file primary header
    tmphdr=`mktemp /tmp/hdr.XXXXXX`
    printFitsHdr.py ${gpubox_files[0]} > $tmphdr
    old_ts=$ts
    ts=`grep "TIME    = " $tmphdr | head -1 | tr -s " " | cut -f 3 -d " "`
    tm=`grep "MILLITIM= " $tmphdr | head -1 | tr -s " " | cut -f 2 -d " "`

    if [ $old_ts -ne $ts ] ; then
        echo "Overriding obsid start time $old_ts with $ts from O-file header"
    fi

    # get the integration time from the header, if there.
    grep "INTTIME" $tmphdr > /dev/null # returns 0 if it finds anything, 1 otherwise
    if [ $? -eq 0 ] ; then
      file_int_time=`grep "INTTIME " $tmphdr | head -1 | tr -s " " | cut -f 3 -d " "`
      if [ "${debug:-0}" -gt 0 ] ; then
        echo "The O-file reports itself as having integration time of $file_int_time seconds"
      fi 
      if [ "$file_int_time" != "$corr_int_time" ] ; then
        echo "WARNING: database int time: $corr_int_time is different to O-file: $file_int_time. Using file."  1>&2
        corr_int_time = file_int_time
      fi
    fi
    # slightly nasty hack to find the number of channels in the data from the 1st extension header
    # redirect stderr from dd to suppress unwanted status messages for blocks transferred
    dd bs=2880 skip=1 count=1 if=${gpubox_files[0]} 2> /dev/null | printFitsHdr.py - > $tmphdr
    old_nchan=$nchan
    # try extracting it as a compressed file
    nchan=`grep "ZNAXIS2 = " $tmphdr | head -1 | tr -s " " | cut -f 3 -d " "`
    if [ ! -n "$nchan" ] ; then
        # try extracting it as an uncompressed file
        nchan=`grep "NAXIS2  = " $tmphdr | head -1 | tr -s " " | cut -f 3 -d " "`
    fi

    if [ ! -n "$nchan" -a $old_nchan -ne $nchan ] ; then
        echo "Overriding nchan $old_nchan with $nchan from O-file header" 1>&2
    fi

    rm $tmphdr # tidy up 
fi

# check if there was a phase centre set. If not, point at the zenith
if [ "$ra_ph" = "" ] ; then
  for_rts=1
  echo "WARNING: There was no phase centre defined for this obs. Setting phase centre to zenith" 1>&2
fi

if [ -z "$ts" ] ; then
  echo "could not find the time from FITS header" 1>&2
  exit 1
fi
if [ -z "$nchan" ] ; then
  echo "could not find number of channels in data from FITS header" 1>&2
  exit 1
fi

# get the approximate length of the scan from DB data:
scan_time=$((stop - start))     # this is the number of seconds M&C thinks the scan went for
n_scans=` echo $scan_time $corr_int_time $nav_time | awk '{ print $1/$2/$3}'`
# adjust integration time of the visibilities
int_time=` echo $corr_int_time $nav_time | awk '{ print $1*$2}'`
if [ "${debug:-0}" -gt 0 ] ; then
  echo "Start time of data: `date -u --date="@${ts}" "+%Y-%m-%d %H:%M:%S"`"
fi 

# round the time up if necessary
if [ "$nav_time" -gt 1 ] ; then
  ts=$((ts+ int_time/2))
fi

newdate=`date -u --date="@${ts}" "+%Y%m%d"`
newtime=`date -u --date="@${ts}" "+%H%M%S"`

if [ "${debug:-0}" -gt 0 ] ; then
  echo "Adjusted start time of data after averaging: `date -u --date="@${ts}" "+%Y-%m-%d %H:%M:%S"`"
fi

# find the low and high coarse chan indices of the assumed set of contiguous coarse chans
# start by building a sub-array of the coarse chan ids corresponding to the gpubox IDs
# note gpubox IDs start at 1...
cc_ind=()
for i in ${gpubox_ind[@]} ; do cc_ind+=("${freqarr[$(($i-1))]}") ; done
if [ "${debug:-0}" -gt 0 ] ; then echo "Coarse chan indexes for desired gpu boxes: ${cc_ind[@]}" ; fi

isodd=$((${#cc_ind[@]} % 2))        # odd number of gpu boxes or even?

# choose the central channel of the subset for the identifier
central_ind=$((${#gpubox_ind[@]} / 2))

# find the freq corresponding to the central coarse chan and set central freq depending on number of fine chans
central=${freqarr[$((central_ind))]}
if [ "${debug:-0}" -gt 0 ] ; then
  echo "Selected central coarse chan $central"
fi

if [ "$isodd" -ne 0 ] ; then
    cent_freq=`echo $central $nchan | awk '{ print ($1 * 1.28 + 128*0.005/$2) }'`
    if [ "${debug:-0}" -gt 0 ] ; then echo "Odd number of channels. Central freq: $cent_freq" ; fi
else
    cent_freq=`echo $central $nchan | awk '{ print (($1-0.5) * 1.28 + 128*0.005/$2) }'`
    if [ "${debug:-0}" -gt 0 ] ; then echo "Even number of channels. Central freq: $cent_freq" ; fi
fi

bandwidth=`echo ${#cc_ind[@]} | awk '{ print ($1 * 1.28 ) }'`
ra_hrs=`echo $ra_ph | awk '{ print $1/15.0 }' `

# generate the header file:
hdrfile="header.txt"
echo "# header file for corr2uvfits" > "$hdrfile"
echo "# lines beginning with '#' and blank lines are ignored" >> "$hdrfile"
echo "FIELDNAME $fieldname" >> "$hdrfile"
echo "N_SCANS   $n_scans   # number of scans (time instants) in correlation products" >> $hdrfile
echo "N_INPUTS  $n_inp   # number of inputs into the correlation products" >> $hdrfile
echo "N_CHANS   $(($nchan * ${#cc_ind[@]}))  # number of channels in spectrum" >> $hdrfile
echo "CORRTYPE  B     # correlation type to use. 'C'(cross), 'B'(both), or 'A'(auto)" >> $hdrfile
echo "INT_TIME  $int_time   # integration time of a visibility in seconds" >> $hdrfile
echo "FREQCENT  $cent_freq # observing center freq in MHz" >> $hdrfile
echo "BANDWIDTH $bandwidth  # total bandwidth in MHz" >> $hdrfile
echo "DATE      $newdate  # YYYYMMDD in UT" >> $hdrfile
echo "TIME      $newtime    # HHMMSS in UT" >> $hdrfile
if [ "${for_rts:-0}" -ne 0 ] ; then
    # output for RTS with phase centre at zenith
    echo "HA_HRS    0.0   # HA of the phase centre (hours)" >> $hdrfile
    echo "DEC_DEGS  -26.7033   # the DEC of the desired phase centre (degs)" >> $hdrfile
else
    # output with specified phase centre
    echo "RA_HRS    $ra_hrs   # RA of the phase centre (hours)" >> $hdrfile
    echo "DEC_DEGS  $dec_ph   # the DEC of the desired phase centre (degs)" >> $hdrfile
fi
echo "TELESOPE MWA  # translates to the TELESCOP item in UVFITS header" >> $hdrfile
echo "INSTRUMENT 128T   # translates to the INSTRUME item in UVFITS header" >> $hdrfile

# all done. Tidy up
rm $tmpfile
rm $tmp_settings

