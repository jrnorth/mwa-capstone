#! /bin/bash

BDC=/usr/global/MWA/VirtualEnvironments/MWA/bin/bash_delaycal.py
CASA=/usr/global/MWA/casa//casapy
CALS=/home/djacobs/src/CASA_Cals/

NTHREADS=30
FILES=$*
CASAPIDS=
for THREAD in `python -c "print ' '.join(map(str,range(1,${NTHREADS})))"`
do
    echo Launching thread $THREAD
    THREADFILES=`~/scripts/pull_args.py -t1:${NTHREADS} --taskid=${THREAD} $FILES`
    if [ "$THREADFILES" ] ;
    then
        echo $THREADFILES
        cal.sh ${THREADFILES}>cal_log_thread_${THREAD}.txt&
        CASAPIDS="${CASAPIDS} "$!
    else
        break
    fi
    echo Waiting a minute to let casa logs cycle
    sleep 61
done
echo Waiting on cal.sh PIDS $CASAPIDS
wait $CASAPIDS
