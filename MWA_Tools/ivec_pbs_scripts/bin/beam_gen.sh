#!/bin/bash

# Generate primary beams

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
#stokes="I"
#uvrange="0.00~3.0klambda"
#weighting="uniform"
#antoption=""

if [[ $1 ]] && [[ $2 ]]
then

# obsnum=$1
 filename=$1
# Bit of an assumption here
 obsnum=`echo $filename | awk 'BEGIN {FS="/"} {print substr($NF,1,10)}'`
 proj=$2

 cd $queuedir

# cat beam.template | sed "s;OBSNUM;${obsnum};g" | sed "s;PROJ;${proj};g" | sed "s;HOSTMEM;${hostmem};g" |  sed "s;CODEDIR;${codedir};g" | sed "s;GROUPQ;${groupq};g"  | sed "s;STANDARDQ;${standardq};g" | sed "s;DATADIR;$datadir;g" | sed "s;UVRANGE;${uvrange};g" | sed "s;STOKES;${stokes};g" | sed "s;WEIGHTING;${weighting};g" | sed "s/ANTOPTION/${antoption}/g" | sed "s;NAME;;g" > beam_${obsnum:5:5}.sh
 cat beam.template | sed "s;OBSNUM;${obsnum};g" | sed "s;PROJ;${proj};g" | sed "s;HOSTMEM;${hostmem};g" |  sed "s;CODEDIR;${codedir};g" | sed "s;GROUPQ;${groupq};g"  | sed "s;STANDARDQ;${standardq};g" | sed "s;DATADIR;${datadir};g" | sed "s;FILENAME;${filename};"  > beam_${obsnum:5:5}.sh

 qsub beam_${obsnum:5:5}.sh

else
 echo "Give me a filename and a project code, e.g. beam_gen.sh /scratch/partner676/user/data/G0008/1012345678/1012345678.fits G0008"
 exit 1
fi

exit 0
