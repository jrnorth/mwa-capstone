#!/bin/bash

# submit a grab and cotter job to the PBS queue

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
  hostmem="70gb"
fi

rootdir=/scratch/$groupq
datadir=$rootdir/$user
codedir=$rootdir/code
queuedir=/home/$user/queue/

if [[ $1 ]] && [[ $2 ]]
then

 obsnum=$1
 proj=$2
 if [[ $3 ]]
 then
  timing="-a "$3
 else
# Currently, wait 9 hours after the observation, to give Cortex time to catch up
# Converting between UNIX time (1970 seconds) and GPS time (1980 and a bit, apparently)
# 315964800.0=10*24*60*60*365.7
  proctime=`expr $obsnum + 32400 + 315964800`
  nowtime=`date +%s`
  calctime=`date --date="@$proctime" +%d%H%M`
# If the deadline was in the past, don't put in a timing constraint
  if [[ $proctime -gt $nowtime ]]
  then
   timing="-a "$calctime
  fi
 fi

 if [[ ! -d $datadir/${proj} ]]
 then
  mkdir $datadir/${proj}
 fi

 if [[ ! -d $datadir/${proj}/${obsnum}/${obsnum}.ms ]]
 then

  cd $queuedir
  cat q_cot_data.template | sed "s;OBSNUM;${obsnum};g" | sed "s;PROJ;${proj};g" | sed "s;DATADIR;${datadir};g" | sed "s;GROUPQ;${groupq};g" | sed "s;STANDARDQ;${standardq};g" | sed "s;HOSTMEM;${hostmem};g" > cot_${obsnum:5:5}.sh

# Suppresses error message when checking if the files have downloaded
  ls $datadir/${proj}/${obsnum}/*gpubox*.fits 1>> /dev/null 2>> /dev/null

  if [[ $? == 0 ]]
  then
   numfiles=`ls $datadir/${proj}/${obsnum}/*gpubox*.fits | wc -l`
  fi

# NB: needs changing as gpuboxes get fixed
  if [[ $numfiles -lt 44 ]]
  then
   cat q_grab_data.template | sed "s;OBSNUM;${obsnum};g" | sed "s;PROJ;${proj};g"  | sed "s;DATADIR;${datadir};g" | sed "s;GROUPQ;${groupq};g" > grb_${obsnum:5:5}.sh
   existingjob=`qstat -u nhurleywalker | grep "grb" | tail -1 | awk '{print $1}'`
   if [[ "$existingjob" == *$computer* ]]
   then
# Other grab job doesn't necessarily have to succeed for it to be a good idea to submit the next one
     dependency="-W depend=afterany:$existingjob"
   fi
   jobnum=`qsub $timing $dependency grb_${obsnum:5:5}.sh`
   qsub -W depend=afterok:$jobnum cot_${obsnum:5:5}.sh
  else
   echo "All files downloaded already, going straight to cotter"
   qsub cot_${obsnum:5:5}.sh
  fi

 else
  echo "This measurement set already exists!"
  exit 1
 fi

else
 echo "Give me an obsnum and project, e.g. grab_cot.sh 1012345678 C001"
 echo "And optionally, a timestring to start the download, of the format ddhhmm, e.g."
 echo "grab_cot.sh 1012345678 C001 101345 will start the job on the 10th of this month, at 13:45."
 exit 1
fi

exit 0
