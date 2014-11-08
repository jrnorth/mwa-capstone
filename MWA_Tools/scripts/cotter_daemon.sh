#! /bin/bash
# Daemon for finding gpubox files as they come in and running cotter on them.
# usage:
# cotter_daemon.sh <task_number> <cotter_daemon_config.cfg>
# TODO:
# Read in config file
#workon MWA
echo "HELLO. I Am CHOMPY"
echo "Would you like to play a game?"
. /nfs/blank/h4215/djacobs/src/CanopyEnvs/MWA/bin/activate 
export PGPASSWORD='ngas$ro'
daemon_task_id=$1
#load and test the variables
. $2  # load the configuration file variables
if [ -e $scratch ]
then
echo scratch: $scratch
else
echo scratch: $scratch not found
break
fi

if [ -e $production_dir ]
then
echo production_dir: $production_dir
else
echo production_dir: $production_dir not found
break
fi

if [ -e $global_dir ]
then
echo global_dir: $global_dir
else
echo global_dir: $global_dir not found
break
fi

# Loop
hostname=`hostname`
host=`python -c "print '${hostname}'.split('.')[0]"`

daemon_log=${global_dir}/cotter_daemon_log_${host}_$1.log

echo "starting daemon $1 with config = $2" >> $daemon_log
echo `date` >> $daemon_log
NOPROCESS=-
FINISHED=-
success_loop=0
n_mismatch=0
n_lockfiles=0
n_missing_flags=0
n_failed_cotters=0
while true; do
    #clear some variables for the start of the loop
    genflags=0 
    # Check that NOPROCESS isnt too big
    (( n=${#NOPROCESS}/11 )) # 10 digit obses + spacer
    if [ "$n" -gt "$n_baddies" ]; then
	    # uh-oh
	    echo "Too many skips. Sending email"
	    subject="CHOMPY is stalled"
	    email_file=${scratch}"/emailmsg.txt"
	    echo "CHOMPY stalled with ${n} skipped obses" > $email_file
    	echo "number of mismatches    = ${n_mismatch}" >> $email_file
    	echo "number of lockfiles     = ${n_lockfiles}" >> $email_file
    	echo "number of missing flags = ${n_missing_flags}" >> $email_file
    	echo "Offending observations:" >> $email_file
    	echo "$NOPROCESS" >> $email_file
    	mail -s "$subject" "$email" < $email_file
    	NOPROCESS=- # reset the grey list
    	n_mismatch=0
	    n_lockfiles=0
	    n_missing_flags=0    fi
    # TODO (maybe):
    # Check that ngas is not targeting this node [This is fine for now -dcj]
    

    # TODO:
    echo querying database
    echo skipping $NOPROCESS
    echo finished: $FINISHED

    #get the blacklist BLACKLIST TODO
    #BLACKLIST=`psql <connect to Nicholes DB and get the blacklist>` TODO
    BLACKLIST=-
    # Get oldest ngas observation on this node which has all files
    obs=`psql -h ngas -d ngas -U ngas_ro -c "select substring(b.file_id, 1,10) as obs_id from ngas_disks a, ngas_files b
    where a.disk_id = b.disk_id and host_id like '%${host}%' and not b.file_id similar to '%(a|${NOPROCESS}|${BLACKLIST}|${FINISHED})%' order by ingestion_date desc limit 1" -A -t`  #
    #check that we're not working on this file
    echo using obsid ${obs} 
    


    #check that all files are available
    nfiles_mandc=`get_nfiles.py -a -o ${obs}`
    nfiles_ngas=`fetch_file_locs.py -a -o ${obs} | wc -w`
    #TODO check that they are equal
    echo found ${nfiles_mandc} files in MandC
    echo found ${nfiles_ngas} files in NGAS
    if [ ${nfiles_mandc} -eq ${nfiles_ngas} ]
    then
        echo files exist and match between mandc
    else
        echo error finding all the files 
        echo MandC files: ${nfiles_mandc}
        echo NGAS files: ${nfiles_ngas}
	    NOPROCESS=${obs}'|'$NOPROCESS
	    (( n_mismatch++ )) #accumulate error count for later email
        continue
    fi

    # Check that others are not working on this obsid
    if [ -f ${global_dir}/${obs}.lockfile ];
    then
        echo exiting on lockfile ${global_dir}/${obs}.lockfile
        NOPROCESS=${obs}'|'$NOPROCESS
	    (( n_lockfiles++ ))  #accumulate lockfile count for later email
        continue
    else
        #claim priority with a lockfile
        lockfile=${global_dir}/${obs}.lockfile
        touch ${lockfile}
    fi

    echo getting files
    #check that this obs hasn't been processed yet
    FILE=`read_uvfits_loc.py -v ${version} -s ${subversion} -o ${obs}`
    if [ -n "${FILE}" ]; 
    then 
        echo ${FILE} found;
        FINISHED=${obs}'|'$FINISHED
	    rm $lockfile
        continue ; 
    fi
    #find the files
    paths=`fetch_file_locs.py -o ${obs}`  #paths to fits correlator files
    newpaths=
    for gpufile in $paths
    do
        newpaths='/nfs/'"${gpufile} ${newpaths}"
    done
    paths=$newpaths
    echo "checking for flag file"
    flagfile=`fetch_file_locs.py -o ${obs} -f` #path to the flag file
    if [ -n "$flagfile" ];
    then
        echo ${flagfile} found 
    else
        echo "Flag file not found"
        if [  $allow_flagging -eq 1 ]
        then
            echo "generating my own flags"
            genflags=1
        else
            echo "not allowed to flag on my own, skipping..."
	        rm $lockfile
	        NOPROCESS=${obs}'|'$NOPROCESS
	        (( n_missing_flags++ ))
            continue
        fi
    fi
    cd ${scratch}  #move to the scratch directory   
    mkdir ${obs}
    cd ${obs} #get into position

    #unzip the flags
    if [ -n "${flagfile}" ]
    then
        echo unzipping flags 
        unzip $flagfile 
        #flag format ${obs}_%%.mwaf
    fi

    obslog=${production_dir}/cotter_${obs}.log
    echo using $obslog

    #get ready to COTTER!
    echo This is Cotter Daemon >> $obslog
    echo `date` >> $obslog
    echo $paths >> $obslog

    cotter_args="${cotter_args} -o ${obs}.uvfits -saveqs ${obs}.qs"
    echo "getting metadata for ${obs}"
    make_metafits.py -g ${obs}
    # add outfile and statistics file
    # Run cotter, etc => log to output directory
    #  don't forget flag file
    if [ ${genflags} -eq 1 ]
    then
        echo "running cotter in flaggin mode" >>$obslog
        cotter -m ${obs}.metafits ${cotter_args} ${paths[@]} &>> $obslog
    else
        echo "running cotter using Randall flags" >>$obslog
        cotter -m ${obs}.metafits ${cotter_args} ${paths[@]} -flagfiles ${obs}_%%.mwaf &>> $obslog  
    fi

    if [ $? -gt 0 ]; then
	    echo ${obs}: cotter error. >> $obslog
	    cd ..
	    rm -r ./${obs}
	    continue
    fi
    
    # Tidy up
    echo Tidying up >> $obslog
    SECONDS=0
    ls $production_dir > /dev/null # ping the directory to make sure the disk is mounted before moving
    copy_metafitsheader.py -i ${obs}.uvfits -m ${obs}.metafits >> $obslog
    mv ${obs}.uvfits ${production_dir}/${obs}.uvfits &&
    mv ${obs}.metafits ${production_dir}/${obs}.metafits &&
    mv ${obs}.qs ${production_dir}/${obs}.qs &&
    cd .. &&
    rm -r ${obs} && # clean up
    # Update uvfits database
    write_uvfits_loc.py -o ${obs} -v ${version} -s ${subversion} -f ${production_dir}/${obs}.uvfits &&
    populate_qc.py -v $obs 
    #echo ${obs}: complete. >> $master_log ||
    #echo ${obs}: tidying error. >> $master_log
    echo Tidying up took $SECONDS seconds >> $obslog

    # Delete lockfile
    rm ${lockfile} 
    FINISHED=${obs}'|'$FINISHED
    ((success_loop++))
    if [ "${success_loop}" -gt "${n_success}" ]; then
	    NOPROCESS=- # revisit some baddies
	    success_loop=0
    fi

    # Wait a little while - this will probably end up in an "else" block.
    sleep $sleep_cadence
done
