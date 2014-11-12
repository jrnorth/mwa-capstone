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

if [[ $1 ]] && [[ $2 ]]
then

 obsnum=$1
 proj=$2

 cd $queuedir

 uvlow="0.00 0.02 0.04"
 uvhigh="0.6 2"

#weightings="uniform"
weightings="natural briggs superuniform radial"

antoptions="!Tile111;!Tile118;!Tile108;!Tile107;!Tile165;!Tile164;!Tile163;!Tile152;!Tile151;!Tile142;!Tile141;!Tile133;!Tile132;!Tile131;!Tile121;!Tile128;!Tile101;!Tile105"

n=1

for weighting in $weightings
do
  for uvl in $uvlow
  do
    for uvh in $uvhigh
    do
       antoption=''
       uvrange=$uvl"~"$uvh"klambda"
       cat clean.template | sed "s;OBSNUM;${obsnum};g" | sed "s;PROJ;${proj};g" | sed "s;HOSTMEM;${hostmem};g" |  sed "s;CODEDIR;${codedir};g" | sed "s;GROUPQ;${groupq};g"  | sed "s;STANDARDQ;${standardq};g" | sed "s;DATADIR;$datadir;g" | sed "s;UVRANGE;${uvrange};g" | sed "s;STOKES;${stokes};g" | sed "s;WEIGHTING;${weighting};g" | sed "s/ANTOPTION/${antoption}/g" | sed "s;NAME;;g" > cln_${obsnum:5:5}_${n}.sh
       if [[ ! $jobnum ]]
       then
           jobnum=`qsub -W depend=afterok:3484931 cln_${obsnum:5:5}_${n}.sh`
       else
           jobnum=`qsub -W depend=afterok:$jobnum cln_${obsnum:5:5}_${n}.sh`
       fi
       ((n+=1))
    done
  done 
  uvrange="0.00~2klambda"
  for antoption in $antoptions
  do
      cat clean.template | sed "s;OBSNUM;${obsnum};g" | sed "s;PROJ;${proj};g" | sed "s;HOSTMEM;${hostmem};g" |  sed "s;CODEDIR;${codedir};g" | sed "s;GROUPQ;${groupq};g"  | sed "s;STANDARDQ;${standardq};g" | sed "s;DATADIR;$datadir;g" | sed "s;UVRANGE;${uvrange};g" | sed "s;STOKES;${stokes};g" | sed "s;WEIGHTING;${weighting};g" | sed "s/ANTOPTION/${antoption}/g" | sed "s;NAME;_112T;g" > cln_${obsnum:5:5}_${n}.sh
     jobnum=`qsub -W depend=afterok:$jobnum cln_${obsnum:5:5}_${n}.sh`
     ((n+=1))
  done
done

else
 echo "Give me an obsnum, e.g. clean_fast.sh 1012345678"
 exit 1
fi

exit 0
