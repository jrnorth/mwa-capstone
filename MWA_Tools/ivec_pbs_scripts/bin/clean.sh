#!/bin/bash

# Run some 'typical' cleans

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

# Clean options
stokes="I"
uvrange="0.00~3.0klambda"
weighting="briggs"
antoption=""
robust="-2.0"

if [[ $1 ]] && [[ $2 ]]
then

 obsnum=$1
 proj=$2

 cd $queuedir

# Could add a loop here to go through various imaging parameters

 cat clean.template | sed "s;OBSNUM;${obsnum};g" | sed "s;PROJ;${proj};g" | sed "s;HOSTMEM;${hostmem};g" |  sed "s;CODEDIR;${codedir};g" | sed "s;GROUPQ;${groupq};g"  | sed "s;STANDARDQ;${standardq};g" | sed "s;DATADIR;$datadir;g" | sed "s;UVRANGE;${uvrange};g" | sed "s;STOKES;${stokes};g" | sed "s;WEIGHTING;${weighting};g" | sed "s/ANTOPTION/${antoption}/g" | sed "s;NAME;;g" | sed "s;ROBUST;${robust};g" > cln_${obsnum:5:5}.sh
 qsub cln_${obsnum:5:5}.sh

else
 echo "Give me an obsnum, e.g. cln.sh 1012345678"
 exit 1
fi

exit 0
