#!/bin/bash

# send calibration solutions to Enterprise and das5

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

 cd $queuedir

 cat q_send_data.template | sed "s;OBSNUM;${obsnum};g" | sed "s;PROJ;${proj};g" | sed "s;DATADIR;${datadir};g" > snd_${obsnum:5:5}.sh

 qsub snd_${obsnum:5:5}.sh

else
 echo "Give me an obsnum, e.g. send_cal.sh 1012345678"
 exit 1
fi

exit 0
