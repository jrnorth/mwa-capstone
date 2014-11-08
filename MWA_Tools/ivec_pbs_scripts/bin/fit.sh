#!/bin/bash

# preliminary: run some fits on the data
# (will eventually get merged into calibrate.sh)

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

rootdir=/scratch/${groupq}
datadir=$rootdir/$user
codedir=$rootdir/code
queuedir=/home/$user/queue/


if [[ $1 ]] && [[ $2 ]]
then

 obsnum=$1
 proj=$2

 cd $queuedir

 if [[ ! -d  $datadir/${proj}/$obsnum/$obsnum.cal ]]
 then
   echo "No calibration table: checking for existing job"
   existingjob=`qstat -u nhurleywalker | grep cal_${obsnum:5:5} | awk '{print $1}'`
   if [[ "$existingjob" == *$computer* ]]
   then
    echo "I see the calibration is currently in the queue."
    dependency="-W depend=afterok:$existingjob"
   else
    echo "No dependency detected. You need to calibrate this data before you fit it."
    exit 1
   fi
 fi
 cat fit.template | sed "s;OBSNUM;${obsnum};g" | sed "s;PROJ;${proj};g" | sed "s;CODEDIR;${codedir};g" | sed "s;GROUPQ;${groupq};g"  | sed "s;STANDARDQ;${standardq};g" | sed "s;DATADIR;$datadir;g" > fit_${obsnum:5:5}.sh
 jobnum=`qsub $dependency fit_${obsnum:5:5}.sh`
 cat q_send_pngs.template | sed "s;OBSNUM;${obsnum};g" | sed "s;PROJ;${proj};g" | sed "s;DATADIR;$datadir;g" | sed "s;GROUPQ;${groupq};g"  > snp_${obsnum:5:5}.sh
 qsub -W depend=afterok:$jobnum snp_${obsnum:5:5}.sh

else
 echo "Give me an obsnum and project, e.g. calibrate.sh 1012345678 C001"
 exit 1
fi

exit 0
