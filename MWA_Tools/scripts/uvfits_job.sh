#! /bin/bash
#convert gpubox files to uvfits using cotter
#$ -S /bin/bash
#$ -V

# Expected parameters to have been passed in (with -v option of qsub):
# production_dir
# master_log
# obs
# version
# subversion
# cotter_args
# scratch_space

echo JOBID ${JOB_ID}
cd $scratch_space
if [ $? -gt 0 ]; then
  echo Cannot find scratch space: $scratch_space >&2
  echo Quitting. >&2
  echo ${obs}: could not find scratch space. >> $master_log
  exit 1
fi
cotter_args="${cotter_args} -o ${obs}.uvfits -saveqs ${obs}.qs" # make output uvfits, save quality statistics

#get local host name
host=${HOSTNAME:0:6} # just the eor-xx part

mkdir $obs
cd $obs

# print some network diagnostics
iostat 5 5
uptime

# find the file locations for this observation
echo Getting gpubox file locations and copying over.
SECONDS=0 # start timer
temp=$(fetch_file_locs.py -o ${obs})
paths=
for path in $temp; do
    loc=${path:1:6} # machine it's on
    if [ "$loc" != "$host" ]; then
	# File is on another machine. get it.
	nfs_path=/nfs/mwa-${path:5}
	rsync -P $nfs_path ./
	path=./$(basename $nfs_path)
    fi
    paths+=($path)
done
echo Copying files took $SECONDS seconds.

change_db.py mit

echo Making metafits
SECONDS=0
make_metafits.py -g ${obs}
echo Metafits took $SECONDS seconds.
echo Running cotter
cotter -m ${obs}.metafits ${cotter_args} ${paths[@]} 
if [ $? -gt 0 ]; then
  echo ${obs}: cotter error. >> $master_log
  cd ..
  rm -r ./${obs}
  exit 1
fi

# if we've made it this far, the conversion was successful.
echo Tidying up
SECONDS=0
ls $production_dir > /dev/null # ping the directory to make sure the disk is mounted before moving things.
copy_metafitsheader.py -i ${obs}.uvfits -m ${obs}.metafits
mv ${obs}.uvfits ${production_dir}/${obs}.uvfits &&
mv ${obs}.metafits ${production_dir}/${obs}.metafits &&
mv ${obs}.qs ${production_dir}/${obs}.qs &&
cd .. &&
rm -r ${obs} && # clean up
# record the file location in the database. Update various other things.
write_uvfits_loc.py -o ${obs} -v ${version} -s ${subversion} -f ${production_dir}/${obs}.uvfits &&
populate_qc.py -v $obs &&
python add_data_paths.py $obs -u 1 > /dev/null


echo ${obs}: complete. >> $master_log
echo Tidying up took $SECONDS seconds
