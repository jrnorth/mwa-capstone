#! /bin/bash
# Wrapper for submitting jobs to Grid Engine to convert observations to uvfits
#
# Arguments = -v version -s subversion -p production_directory -m max_obs
# All following arguments are obsids to be converted.

usage()
{
cat <<EOF
usage: $0 options

This script finds observations and submits them to Grid Engine for uvfits conversion.

OPTIONS:
   -h     Show this message and quit.
   -v     uvfits version (See uvfits_version db table)
   -s     uvfits subversion
   -p     Production directory
   -m     (optional, default=200) Maximum observations to submit to Grid Engine
   -t     (optional, default=02:00:00) Time requirement per uvfits job.
EOF
}

version=
subversion=
production_dir=
max_obs=200 # Default for now
time_req=02:00:00 # Default
OPTIND=1 # used to shift arguments after getting options
while getopts “:hv:s:p:m:t:” OPTION
do
     case $OPTION in
         h)
             usage
             return 1
             ;;
         v)
             version=$OPTARG
             ;;
         s)
             subversion=$OPTARG
             ;;
         p)
             production_dir=$OPTARG
             ;;
         m)
      	     max_obs=$OPTARG
             ;;
	 t)
	     time_req=$OPTARG
	     ;;
         ?)
             usage
             exit
             ;;
     esac
done

echo time req = ${time_req}

shift $(($OPTIND - 1)) # The rest should be obsids.

if [[ -z $version ]] || [[ -z $subversion ]] || [[ -z $production_dir ]]
then
     usage
     exit 1
fi
#export variables that won't change between jobs
export version subversion production_dir

# Use the version number to set up other options
case "${version},${subversion}" in
0,0)
	cotter_args="-timeavg 4 -freqavg 2 -flagedges 2 -usepcentre -initflag 2 -noflagautos"
	;;
1,0)
	cotter_args="-timeavg 4 -freqavg 2 -flagedges 2"
	;;
2,0)
      	cotter_args="-timeavg 4 -freqavg 2 -flagedges 2 -usepcentre -initflag 2 -noflagautos"
	;;
2,1)
	cotter_args="-timeavg 4 -flagedges 2 -usepcentre -initflag 2 -noflagautos"
	;;
2,2)
	cotter_args="-timeavg 4 -freqavg 2 -flagedges 2 -usepcentre -initflag 2 -noflagautos"
	;;
2,3)
	cotter_args="-timeavg 1 -freqavg 2 -flagedges 2 -usepcentre -initflag 2 -noflagautos"
	;;
3,0)
	cotter_args="-timeavg 4 -freqavg 2 -flagedges 2 -usepcentre -initflag 2 -noflagautos"
	;;
3,1)
	cotter_args="-timeavg 4 -freqavg 1 -edgewidth 80 -usepcentre -initflag 0 -noflagautos"
	;;
3,2)
	cotter_args="-timeavg 1 -freqavg 2 -edgewidth 80 -usepcentre -initflag 0 -noflagautos"
	;;
3,3)
	# used to test compressed fits
	cotter_args="-timeavg 4 -freqavg 1 -edgewidth 80 -usepcentre -initflag 0 -noflagautos"
	;;
3,4)
	# re-running 3,1 with newer cotter
	cotter_args="-timeavg 4 -freqavg 1 -edgewidth 80 -usepcentre -initflag 0 -noflagautos"
	;;
4,0)
	# Going back to old settings for industrial run
	cotter_args="-timeres 2 -freqres 80 -edgewidth 80 -usepcentre -initflag 2 -noflagautos"
	;;
4,1)
	# Same as 4,0 but will run on compressed gpubox files
	cotter_args="-timeres 2 -freqres 80 -edgewidth 80 -usepcentre -initflag 2 -noflagautos"
	;;
*)
	echo Could not find version,subversion specified. Please create settings.
	cotter_args="-timeavg 4 -freqavg 2 -usepcentre"
esac
cotter_mem=30 # Now in GB!
nslots=10
cotter_args="$cotter_args -absmem $cotter_mem -j $nslots"
export cotter_args # cotter_args is ammended in each job, but the root is the same
# Note that cotter output is specified later inside of observation loop

export master_log=${production_dir}/`date +%F`.log
echo Logging will be put in $master_log
echo accCotter arguments = $cotter_args >> $master_log

configs_path=$(dirname $(dirname $(python -c 'import mwapy; print mwapy.__file__')))/configs
node_file=${configs_path}/MIT_nodes.txt

nodes=
local_dirs=

while read -r -a line
do
    nodes+=$line[0]
    local_dirs+=$line[1]
done < $node_file

unset all_obs
for obs in "$@"; do
    # Check that we have all the gpubox files at mit
    nfile_mit=$(fetch_file_locs.py -o ${obs} -n)
    if [ $nfile_mit -eq 0 ]; then
	echo obsid $obs has no data. Skipping.
	continue
    fi
    nfile_tot=$(get_nfiles.py -o ${obs})
    if [ "$nfile_mit" -eq "$nfile_tot" ]; then
	# Check that it hasn't been run yet.
	if [ "$(read_uvfits_loc.py -o $obs -v $version -s $subversion)" = "" ]; then
	    all_obs+=($obs)
	    if [ ${#all_obs[@]} -ge $max_obs ]; then
		break
	    fi
	fi
    fi
done

echo ${#all_obs[@]} observations to be converted.

for obs in ${all_obs[@]}; do
    # Get the preferred host
    echo $obs
    preferred_host=$(fetch_file_locs.py -o $obs -p)
    # Some machines don't have scratch space. hard code a solution.
    if [ $preferred_host == eor-01 ] || [ $preferred_host == eor-02 ] || [ $preferred_host == eor-04 ] || [ $preferred_host == eor-12 ] || [ $preferred_host == eor-13 ]; then
	echo Preferred host, $preferred_host, does not have scratch space.
	preferred_host=eor-14
	echo Using $preferred_host instead.
    else
	echo Preferred host = $preferred_host
    fi

    ((GEmem = cotter_mem / $nslots))

    GEmem=${GEmem}G
    # Submit GE job
    local_log=${production_dir}/${obs}.log
    local_err=${production_dir}/${obs}.err
    scratch_space=/${preferred_host}/d1/uvfits_scratch
    script_path=$(which uvfits_job.sh)
    qsub -P uvfits -l h_vmem=${GEmem},h=${preferred_host},h_stack=512k,h_rt=${time_req} -V -v obs=$obs,scratch_space=$scratch_space -o $local_log -e $local_err -pe chost $nslots $script_path

done
