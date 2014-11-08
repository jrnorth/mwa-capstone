#!/bin/bash

# Calibrate some new data

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

 if [[ ! $3 ]]
 then
  echo "No obsid specified for calibration: applying self-calibration"
  calnum=${obsnum}
 else
  calnum=$3
 fi

# Check if the calibration table exists
 if [[ ! -d  $datadir/${proj}/$calnum/$calnum.cal ]]
 then
# Check if the calibration is in the queue
  existingjob=`qstat -u nhurleywalker | grep cal_${calnum:5:5} | awk '{print $1}'`
  if [[ "$existingjob" == *$computer* ]]
  then
   echo "I see you're still creating the calibration table."
   dependency1="depend=afterok:$existingjob"
  fi
 fi 

# Check if the observation measurement set exists
 if [[ ! -d  $datadir/${proj}/$obsnum/$obsnum.ms ]]
 then
# Check if the observation measurement set is in the queue
  existingjob=`qstat -u nhurleywalker | grep cot_${obsnum:5:5} | awk '{print $1}'`
  if [[ "$existingjob" == *$computer* ]]
  then
   echo "I see you're still creating the observation measurement set."
   dependency2="depend=afterok:$existingjob"
  fi
 fi
 
# Combine the dependencies into an expression
 if [[ $dependency1 ]]
 then
   dependency="-W "$dependency1
   if [[ $dependency2 ]]
   then
     dependency="-W "$dependency1","$dependency2
   fi
 else
   if [[ $dependency2 ]]
   then
     dependency="-W "$dependency2
   fi
 fi

 cd $queuedir

 cat applycal.template | sed "s;OBSNUM;${obsnum};g" | sed "s;PROJ;${proj};g" | sed "s;CALNUM;${calnum};g" | sed "s;DATADIR;${datadir};g" | sed "s;STANDARDQ;${standardq};g" | sed "s;GROUPQ;${groupq};g" > aply_${obsnum:5:5}.sh
 qsub $dependency aply_${obsnum:5:5}.sh

else
 echo "Give me an obsnum and project, and optionally, another obsnum from which to calibrate."
 echo "e.g. cal.sh 1012345678 C001 1012387654"
 exit 1
fi

exit 0
