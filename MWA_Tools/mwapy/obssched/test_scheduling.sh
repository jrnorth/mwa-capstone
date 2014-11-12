#!/bin/sh

# test_scheduling.sh
# a suite of test observations
# Usage: give it a "1" as an argument for every test you want to run, and a "0" for those you don't.  E.g.:
#
# plock-122[obssched]% ./test_scheduling.sh 0 1 0 0 0 1 1
#
# will run the 2nd, 6th, and 7th.
#
# It does:
#
# 1) Single observation of EOR2
# 2) Single observation of the Sun
# 3) Tracking the Sun for several hours
# 4) Tiling around the Sun
# 5) Observing a ORBCOMM satellite at a few different positions
# 6) Observing at the zenith (defined by Az,El)
# 7) Observing at the zenith (defined by hex code - not sure that the code here is right, but it's easily changed)



single_observation="./single_observation.py"
tile_body="./tile_body.py"
ephemeris_file="./orbcomm_tle_20080820.txt"

do_test_1=0
do_test_2=0
do_test_3=0
do_test_4=0
do_test_5=0
do_test_6=0
do_test_7=0

if [ $# -gt 0 ]; then do_test_1=$1; fi
if [ $# -gt 1 ]; then do_test_2=$2; fi
if [ $# -gt 2 ]; then do_test_3=$3; fi
if [ $# -gt 3 ]; then do_test_4=$4; fi
if [ $# -gt 4 ]; then do_test_5=$5; fi
if [ $# -gt 5 ]; then do_test_6=$6; fi
if [ $# -gt 6 ]; then do_test_7=$7; fi

# Date of observation
date="2004-10-07"

# for first observation: a static source
time1="01:00:00"
target1="EOR2"
length1="4m"
tile1="1-3 4x 5y 8-10"
frequencies1="0"

# for second observation: a moving source at a single time
time2="01:10:00"
target2="Sun"
length2="4m"
tile2="8T"
frequencies2="0"

# for third observation: a moving source, tracking
time3="01:20:00"
target3="Sun"
length3="3h"
tile3="8T"
frequencies3="0"

# for fourth observation: a moving source, tracking
time4="04:30:00"
target4="Sun"
length4="240"
tile4="8T"
frequencies4="0"
innerradius=5
outerradius=10
tilesize=5

# for fifth observation: a moving source, just going to a few positions
time5="05:30:00"
target5="ORBCOMM FM31"
length5="240"
tile5="8T"
frequencies5="0"
move_time=64;

# for sixth observation: a zenith
time6="06:00:00"
az6=0
el6=89
length6="32"
tile6="8T"
frequencies6="0"

# for seventh observation: a zenith
time7="06:01:00"
hex7="20202020202020202020202020202020"
length7="32"
tile7="8T"
frequencies7="0"

##################################################
# First Observation: EOR2
##################################################
if [ $do_test_1 == 1 ]; then
    # This is the format that single_observation.py wants
    datetime="${date},${time1}"
    
    command="${single_observation} --starttime=${datetime} --stoptime=++${length1} --source=${target1}"
    command="${command} --rfstream=0 --obsname=EOR2 --logtype=monitor --frequency=${frequencies1}"
    command="${command}  --ut --verbose --clear"

    echo "******************************Test 1******************************"
    echo "Running:"
    echo "${command} --comment=tests --tile=\"${tile1}\""
    $command --comment=tests --tile="${tile1}"
    echo ""
    echo ""
fi


##################################################
# Second Observation: the Sun
##################################################
if [ $do_test_2 == 1 ]; then
    # This is the format that single_observation.py wants
    datetime="${date},${time2}"
    
    command="${single_observation} --starttime=${datetime} --stoptime=++${length2} --source=${target2}"
    command="${command} --rfstream=0 --obsname=Sun --logtype=monitor --frequency=${frequencies2}"
    command="${command} --ut --verbose --force"
    
    echo "******************************Test 2******************************"
    echo "Running:"
    echo "${command} --tile=\"${tile2}\" --comment=\"more tests\""
    $command --tile="${tile2}" --comment="more tests"
    echo ""
    echo ""
fi

##################################################
# Third Observation: tracking the Sun
##################################################
if [ $do_test_3 == 1 ]; then
    # This is the format that single_observation.py wants
    datetime="${date},${time3}"
    
    command="${single_observation} --starttime=${datetime} --stoptime=++${length3} --source=${target3}"
    command="${command} --rfstream=0 --obsname=Sun_track --logtype=monitor --frequency=${frequencies3}"
    command="${command} --ut --verbose --force"
    
    echo "******************************Test 3******************************"
    echo "Running:"
    echo "${command} --tile=\"${tile3}\" --comment=\"and some more tests\""
    $command --tile="${tile3}" --comment="and some more tests"
    echo ""
    echo ""
fi
    
##################################################
# Fourth Observation: tile around the Sun
##################################################
if [ $do_test_4 == 1 ]; then
    # This is the format that single_observation.py wants
    datetime="${date},${time4}"
    
    command="${tile_body} -n ${target4} -t ${datetime} -i ${innerradius} -o ${outerradius} -s ${tilesize}"
    #command="${command} | grep -v \"#\" | awk '{printf \"%s_%s\n\",\$3,\$4}'"
    command="${command}"
    echo "******************************Test 4******************************"
    echo "Running:"
    echo "${command}"
    echo "But extracting the RA,Dec"
    RADec_values=`$command | grep -v \# | awk '{printf "%s_%s\n",$4,$5}'`
    GPStime=`$command | grep GPStime | perl -pe 's/.*?=//;s/\[.*//'`
    for RADec_value in $RADec_values; do
	RA=`echo $RADec_value | awk -F "_" '{print $1}'`
	Dec=`echo $RADec_value | awk -F "_" '{print $2}'`
	echo "This position has RA=${RA}, Dec=${Dec}"

	command="${single_observation} --starttime=${GPStime} --stoptime=++${length4} --ra=${RA} --dec=${Dec}"
	command="${command} --rfstream=0 --obsname=Sun_tile --logtype=monitor --frequency=${frequencies4}"
	command="${command} --ut --verbose --force"
	echo "Running:"
	echo "${command} --tile=\"${tile4}\" --comment=\"still more tests\""
	$command --tile="${tile4}" --comment="still more tests"

	GPStime=$((${GPStime} + ${length4}))
    done
    echo ""
    echo ""
fi

##################################################
# Fifth Observation: ORBCOMM
##################################################
if [ $do_test_5 == 1 ]; then
    # This is the format that single_observation.py wants
    datetime="${date},${time5}"
    
    command="${single_observation} --starttime=${datetime} --stoptime=++${length5}"
    command="${command} --rfstream=0 --obsname=orbcomm --logtype=monitor --frequency=${frequencies5}"
    command="${command} --ut --force --verbose"
    command="${command} --tlefile=${ephemeris_file} --dt=64 --move=240"
    
    echo "******************************Test 5******************************"
    echo "Running:"
    echo "${command} --source=\"${target5}\" --tile=\"${tile5}\" --comment=\"even more tests\""
    $command --source="${target5}"  --tile="${tile5}" --comment="even more tests"
    echo ""
    echo ""
fi
 

##################################################
# Sixth Observation: zenith
##################################################
if [ $do_test_6 == 1 ]; then
    # This is the format that single_observation.py wants
    datetime="${date},${time6}"
    
    command="${single_observation} --starttime=${datetime} --stoptime=++${length6} --az=${az6} --el=${el6}"
    command="${command} --rfstream=0 --obsname=zenith --logtype=monitor --frequency=${frequencies6}"
    command="${command}  --ut --verbose --force"

    echo "******************************Test 6******************************"
    echo "Running:"
    echo "${command} --comment=\"azel tests\" --tile=\"${tile6}\""
    $command --comment="azel tests" --tile="${tile6}"
    echo ""
    echo ""
fi

##################################################
# Sixth Observation: hex zenith
##################################################
if [ $do_test_7 == 1 ]; then
    # This is the format that single_observation.py wants
    datetime="${date},${time7}"
    
    command="${single_observation} --starttime=${datetime} --stoptime=++${length7} --hex=${hex7}"
    command="${command} --rfstream=0 --obsname=zenith --logtype=monitor --frequency=${frequencies7}"
    command="${command}  --ut --verbose --force"

    echo "******************************Test 7******************************"
    echo "Running:"
    echo "${command} --comment=\"hex tests\" --tile=\"${tile7}\""
    $command --comment="hex tests" --tile="${tile7}"
    echo ""
    echo ""
fi
